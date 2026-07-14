"""Telegram delivery adapter: part-1 drill in chat for the single pilot student.

Like the MCP server, this is an adapter *inside* the backend — it calls ``LearningService``
directly through ``SessionLocal`` (no self-HTTP, no API token). The bot sends one task
statement, takes the child's short answer, submits it, and relays the verdict. Answer keys
never leave the backend (the mission payload carries no expected answer); the verdict is
graded server-side by exact match for ``daily:`` drill missions.

Run from ``backend/`` with the ``[bot]`` extra installed:

    python -m app.adapters.telegram.bot
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlparse
from uuid import UUID
from zoneinfo import ZoneInfo

from app.application.use_cases import (
    SLICE_SUBJECT_LABEL,
    ExactOnlyJudge,
    LearningService,
    RuleBasedReviewer,
)
from app.config import get_settings
from app.domain.enums import AttemptKind, AttemptMode, Subject
from app.infrastructure.db import SessionLocal
from app.infrastructure.llm import LlmShortAnswerJudge, OpenAICompatibleReviewer
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from app.infrastructure.telegram_send import deliver_pending_notes

# One student in the family pilot (the all-zero UUID the frontend/seed/MCP use).
PILOT_STUDENT_ID = UUID("00000000-0000-0000-0000-000000000000")
SLICE_SIZE = 5  # сколько задач в срезе по теме (фактически ≤ банка темы)
BOT_COMMANDS = (
    ("start", "Главное меню"),
    ("today", "Задания на сегодня"),
    ("slice", "Срез по теме"),
    ("ready", "Отметить: теорию изучила"),
    ("progress", "Мой прогресс"),
    ("help", "Как пользоваться ботом"),
    ("cancel", "Остановить текущий режим"),
    ("skip", "Пропустить текущую задачу"),
)

logger = logging.getLogger(__name__)
POLLING_FAILURE_MARKERS = (
    "Failed to fetch updates",
    "TelegramNetworkError",
    "ProxyConnectionError",
)
POLLING_FAILURE_WINDOW_SECONDS = 5 * 60
POLLING_FAILURE_THRESHOLD = 6
POLLING_WATCHDOG_INTERVAL_SECONDS = 30
POLLING_RESTART_EXIT_CODE = 75


class PollingFailureMonitor(logging.Handler):
    """Tracks repeated aiogram polling failures so Docker can restart the bot."""

    def __init__(
        self,
        now: Callable[[], float] | None = None,
        window_seconds: int = POLLING_FAILURE_WINDOW_SECONDS,
        threshold: int = POLLING_FAILURE_THRESHOLD,
    ) -> None:
        super().__init__(level=logging.NOTSET)
        self._now = now or time.monotonic
        self.window_seconds = window_seconds
        self.threshold = threshold
        self._failures: deque[float] = deque()

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if any(marker in message for marker in POLLING_FAILURE_MARKERS):
            self.record_failure()

    def record_failure(self) -> None:
        self._failures.append(self._now())
        self._prune()

    def failure_count(self) -> int:
        self._prune()
        return len(self._failures)

    def should_restart(self) -> bool:
        return self.failure_count() >= self.threshold

    def _prune(self) -> None:
        cutoff = self._now() - self.window_seconds
        while self._failures and self._failures[0] < cutoff:
            self._failures.popleft()


def _install_polling_failure_monitor() -> PollingFailureMonitor:
    root = logging.getLogger()
    for handler in root.handlers:
        if isinstance(handler, PollingFailureMonitor):
            return handler
    monitor = PollingFailureMonitor()
    root.addHandler(monitor)
    return monitor


async def _polling_failure_watchdog(
    monitor: PollingFailureMonitor,
    exit_fn: Callable[[int], object] = os._exit,
) -> None:
    while True:
        await asyncio.sleep(POLLING_WATCHDOG_INTERVAL_SECONDS)
        if monitor.should_restart():
            logger.error(
                "Telegram polling failed %s times in %s seconds; exiting for Docker restart",
                monitor.failure_count(),
                monitor.window_seconds,
            )
            exit_fn(POLLING_RESTART_EXIT_CODE)
            return

# Cache only (DB is the source of truth via list_daily_drill): which drill missions were
# already shown this run, and which one each chat is currently answering. Survivable across
# restarts — on restart we simply re-present whatever is still open.
_presented: dict[int, set[UUID]] = {}
_awaiting: dict[int, UUID] = {}
# Активная сессия среза на чат: {subject, items, idx, judged}. Срез приоритетнее дрилла.
_srez: dict[int, dict[str, Any]] = {}


def _service(session: Any) -> LearningService:
    settings = get_settings()
    connection = settings.llm_connection()
    reviewer = OpenAICompatibleReviewer(connection) if connection else RuleBasedReviewer()
    # В TG (ученический тренажёр) ответы оценивает ИИ-судья по верифицированному эталону.
    judge = LlmShortAnswerJudge(connection) if connection else ExactOnlyJudge()
    return LearningService(
        SqlAlchemyUnitOfWork(session), reviewer, settings.local_timezone, judge=judge
    )


def build_parent_digest(student_id: str = str(PILOT_STUDENT_ID)) -> str:
    with SessionLocal() as session:
        data = _service(session).get_dashboard(UUID(student_id))
    tracks = ", ".join(
        f"{track['subject']}: {track['current_score']}/{track['target_score']}"
        for track in data.get("tracks", [])
    )
    return (
        "EGE Mentor digest\n"
        f"Tracks: {tracks or 'no tracks yet'}\n"
        f"Clean sheet: {data.get('clean_sheet_ratio', 0):.0%}\n"
        f"Due reviews: {data.get('due_reviews', 0)}"
    )


def _is_authorized(chat_id: int) -> bool:
    """chat_id обязателен (шов №5): авторизованы ученик + доп. тестовые chat_id."""
    return str(chat_id) in get_settings().authorized_chat_ids


async def _ensure_authorized(message: Any) -> bool:
    """Для message-хендлеров: неавторизованному отвечаем его chat_id (для онбординга — родитель
    впишет в TELEGRAM_STUDENT_CHAT_ID), но задачи не выдаём."""
    if _is_authorized(message.chat.id):
        return True
    await message.answer(
        f"Этот чат не авторизован. Ваш chat_id: {message.chat.id}.\n"
        "Передайте его родителю — он добавит вас в настройки бота."
    )
    return False


def _task_text(payload: dict[str, object]) -> str:
    parts: list[str] = [str(payload["title"])]
    if payload.get("statement"):
        parts.append(str(payload["statement"]))
    if payload.get("instructions"):
        parts.append(str(payload["instructions"]))
    if payload.get("visual_ready") and payload.get("topic_id"):
        parts.append(_topic_theory_line(payload["topic_id"]))
    if not payload.get("instructions"):
        parts.append("Реши, кратко распиши ход решения и в конце укажи ответ.")
    return "\n\n".join(parts)


def _topic_theory_url(topic_id: object) -> str:
    base = get_settings().public_frontend_base_url.rstrip("/")
    return f"{base}/theory/{topic_id}"


def _is_public_frontend_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        return False
    try:
        parsed_ip = ip_address(host)
    except ValueError:
        return True
    return not (parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_link_local)


def _topic_theory_line(topic_id: object) -> str:
    base_url = get_settings().public_frontend_base_url
    if _is_public_frontend_url(base_url):
        return f"Визуализация темы: {_topic_theory_url(topic_id)}"
    return "Визуализация есть на сайте: «Программа» → эта тема."


def _verdict_text(result: dict[str, object]) -> str:
    status = result["status"]
    status_value = getattr(status, "value", status)
    head = {"passed": "✅ Верно!", "failed": "❌ Неверно."}.get(str(status_value), "📝 Принято.")
    lines = [head]
    if result.get("feedback"):
        lines.append(str(result["feedback"]))
    if result.get("next_action"):
        lines.append(str(result["next_action"]))
    return "\n".join(lines)


def _home_keyboard() -> Any:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 Сегодня", callback_data="menu:today")],
            [InlineKeyboardButton(text="🧪 Срез по теме", callback_data="menu:slice")],
            [InlineKeyboardButton(text="📖 Готова к новым темам", callback_data="menu:ready")],
            [InlineKeyboardButton(text="📊 Прогресс", callback_data="menu:progress")],
        ]
    )


async def _show_home(message: Any, text: str = "Выбери, что хочешь сделать:") -> None:
    await message.answer(text, reply_markup=_home_keyboard())


def _progress_text(data: dict[str, object], phase: dict[str, object] | None = None) -> str:
    lines = ["📊 Твой прогресс"]
    for track in data.get("tracks", []):
        subject = track["subject"]
        label = SLICE_SUBJECT_LABEL.get(subject, getattr(subject, "value", str(subject)))
        current = float(track["current_score"])
        target = float(track["target_score"])
        lines.append(f"{label}: {current:g} из {target:g}")
    if phase is not None:
        cov = phase["coverage"]
        # in_progress включает under_review — вычитаем, чтобы корзины не пересекались.
        in_work = cov["in_progress"] - cov["under_review"]
        start, end = phase.get("start_date"), phase.get("end_date")
        dates = ""
        if hasattr(start, "strftime") and hasattr(end, "strftime"):
            dates = f" ({start.strftime('%d.%m')} – {end.strftime('%d.%m')})"
        lines.append("")
        lines.append(f"📚 Фаза «{phase['label']}»{dates}")
        lines.append(
            f"Закрыто {cov['confirmed']} из {cov['total']} · "
            f"в работе {in_work} · на повторении {cov['under_review']}"
        )
        upcoming = [
            str(topic["topic_title"])
            for topic in phase.get("topics", [])
            if getattr(topic["state"], "value", topic["state"]) == "open"
        ][:3]
        if upcoming:
            lines.append("Дальше: " + ", ".join(upcoming))
    lines.append(f"Повторы на сегодня: {data.get('due_reviews', 0)}")
    lines.append(f"Код без подсказок: {float(data.get('clean_sheet_ratio', 0)):.0%}")
    lines.append("")
    lines.append("Тема засчитана не когда «понял на 100%», а когда решил верно и прошёл повтор.")
    return "\n".join(lines)


async def _send_next(message: Any) -> None:
    chat_id = message.chat.id
    with SessionLocal() as session:
        drills = _service(session).list_daily_drill(PILOT_STUDENT_ID)
    presented = _presented.setdefault(chat_id, set())
    nxt = next((d for d in drills if d["id"] not in presented), None)
    if nxt is None:
        _awaiting.pop(chat_id, None)
        await _show_home(message, "На сегодня всё сделано ✅ Новая порция — завтра утром.")
        return
    mission_id = nxt["id"]
    assert isinstance(mission_id, UUID)
    presented.add(mission_id)
    _awaiting[chat_id] = mission_id
    await message.answer(_task_text(nxt))


async def _on_start(message: Any) -> None:
    if not await _ensure_authorized(message):
        return
    await _show_home(
        message,
        "Привет! Я помогу пройти задания на сегодня, сделать срез по теме "
        "и посмотреть прогресс.\n\nСначала реши сам, затем пришли ход решения и ответ.",
    )


async def _on_today(message: Any) -> None:
    if not await _ensure_authorized(message):
        return
    chat_id = message.chat.id
    if chat_id in _srez:
        await message.answer("Сейчас идёт срез. Заверши его или используй /cancel.")
        return
    _presented.pop(chat_id, None)
    _awaiting.pop(chat_id, None)
    await _send_next(message)


async def _on_progress(message: Any) -> None:
    if not await _ensure_authorized(message):
        return
    with SessionLocal() as session:
        service = _service(session)
        data = service.get_dashboard(PILOT_STUDENT_ID)
        phases = service.list_program_progress(PILOT_STUDENT_ID)
    current_phase = next((p for p in phases if p["is_current"]), None)
    await message.answer(_progress_text(data, current_phase), reply_markup=_home_keyboard())


async def _on_help(message: Any) -> None:
    if not await _ensure_authorized(message):
        return
    await _show_home(
        message,
        "Как пользоваться ботом:\n"
        "• Сегодня — подготовленные задания и повторы.\n"
        "• Срез по теме — 5 задач с результатом в конце.\n"
        "• Готова к новым темам (/ready) — отметь, по каким темам изучила теорию: "
        "новые задачи буду брать из твоего списка.\n"
        "• Прогресс — текущие баллы и повторы.\n\n"
        "Ответ присылай текстом: кратко распиши решение и в конце укажи ответ. "
        "/skip пропустит одну задачу, если пока не готова (не считается ошибкой). "
        "/cancel остановит текущий режим.",
    )


READY_PROMPT = (
    "Отметь темы, по которым уже изучила теорию и готова решать. ✅ — в работу, "
    "повторное нажатие снимает отметку. Пока есть хотя бы одна отметка, новые темы "
    "в «Сегодня» беру только из твоего списка."
)


def _ready_keyboard(rows: list[dict[str, Any]]) -> Any:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = [
        [
            InlineKeyboardButton(
                text=("✅ " if row["theory_ready"] else "▫️ ") + str(row["title"]),
                callback_data=f"ready:t:{row['topic_id']}",
            )
        ]
        for row in rows
    ]
    keyboard.append([InlineKeyboardButton(text="Готово", callback_data="ready:done")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def _on_ready(message: Any) -> None:
    if not await _ensure_authorized(message):
        return
    with SessionLocal() as session:
        rows = _service(session).list_theory_ready_candidates(PILOT_STUDENT_ID)
    if not rows:
        await _show_home(message, "Открытых тем для отметки сейчас нет — всё уже в работе. 👍")
        return
    await message.answer(READY_PROMPT, reply_markup=_ready_keyboard(rows))


async def _on_ready_toggle(callback: Any) -> None:
    if not _is_authorized(callback.message.chat.id):
        await callback.answer("Не авторизовано", show_alert=True)
        return
    topic_id = UUID(callback.data.split(":", 2)[2])
    with SessionLocal() as session:
        service = _service(session)
        rows = service.list_theory_ready_candidates(PILOT_STUDENT_ID)
        current = next((r for r in rows if r["topic_id"] == topic_id), None)
        if current is None:
            await callback.answer("Эта тема уже недоступна", show_alert=True)
            return
        updated = service.set_topic_theory_ready(topic_id, not current["theory_ready"])
        rows = service.list_theory_ready_candidates(PILOT_STUDENT_ID)
    await callback.answer("Отмечено ✅" if updated["theory_ready"] else "Отметка снята")
    await callback.message.edit_reply_markup(reply_markup=_ready_keyboard(rows))


async def _on_ready_done(callback: Any) -> None:
    if not _is_authorized(callback.message.chat.id):
        await callback.answer("Не авторизовано", show_alert=True)
        return
    await callback.answer()
    with SessionLocal() as session:
        rows = _service(session).list_theory_ready_candidates(PILOT_STUDENT_ID)
    marked = [row for row in rows if row["theory_ready"]]
    if marked:
        text = (
            f"Отмечено тем: {len(marked)}. Новые задачи в «Сегодня» теперь только из "
            "твоего списка. Отметки можно менять в любой момент через /ready."
        )
    else:
        text = "Отметок нет — новые темы буду выдавать по плану фазы."
    await callback.message.edit_text(text)
    await _show_home(callback.message)


async def _on_send(message: Any) -> None:
    """Родительская команда: /send <текст> — опубликовать заметку и сразу доставить ученику.
    Доступна только из чата родителя-контролёра (telegram_parent_chat_id)."""
    settings = get_settings()
    parent_chat = settings.telegram_parent_chat_id.strip()
    if not parent_chat or str(message.chat.id) != parent_chat:
        return  # чужим командам не отвечаем
    text = (message.text or "").partition(" ")[2].strip()
    if not text:
        await message.answer("Использование: /send текст — заметка уйдёт ученику в Telegram.")
        return
    with SessionLocal() as session:
        _service(session).publish_feedback(
            {"student_id": PILOT_STUDENT_ID, "body": text, "source_ref": "parent:telegram"}
        )
    delivered = await asyncio.to_thread(deliver_pending_notes, settings, PILOT_STUDENT_ID)
    await message.answer(f"Отправлено ученику ✅ (доставлено заметок: {delivered})")


async def _on_menu(callback: Any) -> None:
    if not _is_authorized(callback.message.chat.id):
        await callback.answer("Не авторизовано", show_alert=True)
        return
    await callback.answer()
    action = callback.data.split(":", 1)[1]
    handlers = {
        "today": _on_today,
        "slice": _on_slice,
        "progress": _on_progress,
        "ready": _on_ready,
    }
    await handlers[action](callback.message)


async def _on_answer(message: Any) -> None:
    if not await _ensure_authorized(message):
        return
    chat_id = message.chat.id
    if chat_id in _srez:  # срез приоритетнее дрилла, пока активен
        await _handle_srez_answer(message, chat_id)
        return
    mission_id = _awaiting.get(chat_id)
    if mission_id is None:
        await _show_home(message, "Сейчас нет активного задания. Выбери действие:")
        return
    with SessionLocal() as session:
        service = _service(session)
        result = await service.submit_attempt(
            {
                "mission_id": mission_id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.UNKNOWN,
                "answer_text": message.text or "",
            }
        )
        # Post-attempt разбор: если ответ задачи — интервал, показываем
        # числовую прямую (правильное решение + ответ ученика).
        visual = service.drill_solution_visual(mission_id, message.text or None)
    _awaiting.pop(chat_id, None)
    await message.answer(_verdict_text(result))
    if visual is not None:
        from aiogram.types import BufferedInputFile

        await message.answer_photo(
            BufferedInputFile(visual.png, filename="solution.png"),
            caption=f"\U0001f4ca {visual.caption}",
        )
    await _send_next(message)


# ---- срез по теме (ученический тренажёр) -------------------------------------


def _subject_keyboard(subjects: list[Subject]) -> Any:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [
            InlineKeyboardButton(
                text=SLICE_SUBJECT_LABEL.get(subject, subject.value),
                callback_data=f"slice:subj:{subject.value}",
            )
        ]
        for subject in subjects
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _topic_keyboard(topics: list[dict[str, object]]) -> Any:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [
            InlineKeyboardButton(
                text=f"{str(topic['title'])[:55]} ({topic['tasks_in_bank']})",
                callback_data=f"slice:topic:{topic['topic_id']}",
            )
        ]
        for topic in topics
    ]
    rows.append([InlineKeyboardButton(text="← К предметам", callback_data="slice:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _on_slice(message: Any) -> None:
    if not await _ensure_authorized(message):
        return
    chat_id = message.chat.id
    if chat_id in _srez:
        await message.answer("Срез уже идёт. Заверши его или используй /cancel.")
        return
    if chat_id in _awaiting:
        await message.answer("Сейчас идёт задание дня. Заверши его или используй /cancel.")
        return
    with SessionLocal() as session:
        topics = _service(session).list_slice_topics(PILOT_STUDENT_ID)
    if not topics:
        await message.answer("В банке пока нет задач для среза.")
        return
    subjects: list[Subject] = []
    for topic in topics:
        subject = topic["subject"]
        if subject not in subjects:
            subjects.append(subject)
    await message.answer("Срез по теме. Выбери предмет:", reply_markup=_subject_keyboard(subjects))


async def _on_slice_subject(callback: Any) -> None:
    if not _is_authorized(callback.message.chat.id):
        await callback.answer("Не авторизовано", show_alert=True)
        return
    await callback.answer()  # закрыть спиннер
    subject_value = callback.data.split(":")[2]
    with SessionLocal() as session:
        topics = [
            t
            for t in _service(session).list_slice_topics(PILOT_STUDENT_ID)
            if t["subject"].value == subject_value
        ]
    if not topics:
        await callback.message.answer("По предмету нет тем с задачами.")
        return
    await callback.message.edit_text("Выбери тему:", reply_markup=_topic_keyboard(topics))


async def _on_slice_back(callback: Any) -> None:
    if not _is_authorized(callback.message.chat.id):
        await callback.answer("Не авторизовано", show_alert=True)
        return
    await callback.answer()
    with SessionLocal() as session:
        topics = _service(session).list_slice_topics(PILOT_STUDENT_ID)
    subjects = list(dict.fromkeys(topic["subject"] for topic in topics))
    await callback.message.edit_text(
        "Срез по теме. Выбери предмет:", reply_markup=_subject_keyboard(subjects)
    )


async def _on_slice_topic(callback: Any) -> None:
    if not _is_authorized(callback.message.chat.id):
        await callback.answer("Не авторизовано", show_alert=True)
        return
    await callback.answer()
    topic_id = UUID(callback.data.split(":")[2])
    chat_id = callback.message.chat.id
    with SessionLocal() as session:
        svc = _service(session)
        topic = next(
            (t for t in svc.list_slice_topics(PILOT_STUDENT_ID) if t["topic_id"] == topic_id), None
        )
        if topic is None:
            await callback.message.answer("Тема недоступна.")
            return
        items = svc.draw_slice(topic["subject"], SLICE_SIZE, topic_id)
    if not items:
        await callback.message.answer("По теме нет задач.")
        return
    _awaiting.pop(chat_id, None)  # срез приоритетнее дрилла
    _srez[chat_id] = {"subject": topic["subject"], "items": items, "idx": 0, "judged": []}
    await callback.message.edit_text(f"Срез по теме: {topic['title']}")
    await callback.message.answer(
        f"Срез: {topic['title']} — {len(items)} задач(и). "
        "/skip — пропустить задачу, /cancel — отмена всего среза."
    )
    await _send_srez_task(callback.message, chat_id)


async def _send_srez_task(message: Any, chat_id: int) -> None:
    session = _srez.get(chat_id)
    if session is None:
        return
    idx = session["idx"]
    items = session["items"]
    task = items[idx]
    visual_line = (
        f"\n\n{_topic_theory_line(task['topic_id'])}"
        if task.get("visual_ready") and task.get("topic_id")
        else ""
    )
    await message.answer(
        f"Задача {idx + 1}/{len(items)}:\n\n{task['statement']}\n\n"
        f"Реши, кратко распиши ход и в конце укажи ответ.{visual_line}"
    )


async def _handle_srez_answer(message: Any, chat_id: int) -> None:
    session = _srez[chat_id]
    task = session["items"][session["idx"]]
    with SessionLocal() as db:
        judged = await _service(db).judge_task_answer(task["task_id"], message.text or "")
    session["judged"].append(judged)
    head = "✅ Верно!" if judged["correct"] else "❌ Неверно."
    feedback = str(judged.get("feedback") or "")
    await message.answer(f"{head}\n{feedback}".strip())
    await _advance_srez(message, chat_id)


async def _advance_srez(message: Any, chat_id: int) -> None:
    """Следующая задача среза или, если задачи кончились, финальный подсчёт.

    Пропущенная задача просто не попадает в ``judged``, поэтому не входит ни в
    ``tasks_total``, ни в ``tasks_correct`` — пропуск не засчитывается ошибкой."""
    session = _srez[chat_id]
    session["idx"] += 1
    if session["idx"] < len(session["items"]):
        await _send_srez_task(message, chat_id)
        return
    with SessionLocal() as db:
        result = _service(db).record_slice(PILOT_STUDENT_ID, session["subject"], session["judged"])
    _srez.pop(chat_id, None)
    verdict = "зачёт ✅" if result["passed"] else "недобор"
    await message.answer(
        f"Срез готов: {result['tasks_correct']}/{result['tasks_total']} "
        f"({result['percent']}%) — {verdict}.",
        reply_markup=_home_keyboard(),
    )


async def _on_cancel(message: Any) -> None:
    if not await _ensure_authorized(message):
        return
    chat_id = message.chat.id
    active = _srez.pop(chat_id, None) is not None or chat_id in _awaiting
    _awaiting.pop(chat_id, None)
    _presented.pop(chat_id, None)
    await _show_home(message, "Текущий режим остановлен." if active else "Нет активного режима.")


async def _on_skip(message: Any) -> None:
    """Пропустить одну текущую задачу (не готова к ней), не завершая весь режим.

    В срезе — пропущенная задача не попадает в подсчёт (не зачёт и не ошибка).
    В дрилле дня — задание остаётся открытым и вернётся позже (сегодня или завтра)."""
    if not await _ensure_authorized(message):
        return
    chat_id = message.chat.id
    if chat_id in _srez:
        await message.answer("Пропущено — не считается ни зачётом, ни ошибкой.")
        await _advance_srez(message, chat_id)
        return
    if chat_id in _awaiting:
        _awaiting.pop(chat_id, None)
        await message.answer("Пропущено, вернёшься к этой задаче позже.")
        await _send_next(message)
        return
    await message.answer("Сейчас нет активной задачи для пропуска.")


async def _on_unknown_command(message: Any) -> None:
    if not await _ensure_authorized(message):
        return
    await _show_home(message, "Не знаю такую команду. Выбери действие:")


async def _on_unsupported(message: Any) -> None:
    if not await _ensure_authorized(message):
        return
    if message.chat.id in _srez or message.chat.id in _awaiting:
        await message.answer("Пока я принимаю решение только текстом.")
        return
    await _show_home(message, "Выбери действие, затем пришли решение текстом:")


def _seconds_until(hhmm: str, tz_name: str) -> float:
    """Секунд до ближайшего HH:MM в локальной таймзоне (следующий день, если уже прошло)."""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    try:
        hour, minute = (int(part) for part in hhmm.split(":"))
    except ValueError:
        hour, minute = 16, 0
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def _morning_push(bot: Any) -> None:
    """Ежедневный супервайзер пуша: будит в telegram_push_time. Сбой одной итерации логируем и
    продолжаем — иначе одна ошибка Telegram/DB остановила бы все будущие пуши до рестарта."""
    settings = get_settings()
    chat_id = int(settings.telegram_student_chat_id)
    while True:
        await asyncio.sleep(_seconds_until(settings.telegram_push_time, settings.local_timezone))
        try:
            await _run_daily_push(bot, chat_id)
        except Exception:
            logger.exception("Morning push iteration failed; will retry next cycle")


async def _run_daily_push(bot: Any, chat_id: int) -> None:
    """Одна итерация: собрать день, позвать решать, сообщить о дефиците, доставить заметки."""
    with SessionLocal() as session:
        result = _service(session).build_daily_queue(
            PILOT_STUDENT_ID, get_settings().daily_drill_size
        )
    _presented.pop(chat_id, None)
    _awaiting.pop(chat_id, None)
    filled = result.get("filled") or []
    if filled:
        await bot.send_message(
            chat_id, f"Задачи на сегодня готовы ({len(filled)}).", reply_markup=_home_keyboard()
        )
    else:
        await bot.send_message(
            chat_id, "Новых задач на сегодня нет.", reply_markup=_home_keyboard()
        )
    shortage = result.get("shortage") or []
    if shortage:
        titles = ", ".join(str(item["title"]) for item in shortage)
        logger.warning("Telegram daily queue shortage: %s", titles)
    # Доставка заметок — общая синхронная функция (см. telegram_send). В async-контексте
    # выносим её в поток, чтобы не блокировать поллинг на время сетевых отправок.
    await asyncio.to_thread(deliver_pending_notes, get_settings(), PILOT_STUDENT_ID)


async def _register_commands(bot: Any) -> None:
    from aiogram.types import BotCommand

    commands = [
        BotCommand(command=command, description=description)
        for command, description in BOT_COMMANDS
    ]
    await bot.set_my_commands(commands)


async def _run(dp: Any, bot: Any) -> None:
    await _register_commands(bot)
    monitor = _install_polling_failure_monitor()
    asyncio.create_task(_polling_failure_watchdog(monitor))
    if get_settings().telegram_student_chat_id:
        asyncio.create_task(_morning_push(bot))  # пуш только когда известен chat_id
    await dp.start_polling(bot)


def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit("Set telegram_bot_token to run the Telegram bot")
    try:
        from aiogram import Bot, Dispatcher, F
        from aiogram.client.session.aiohttp import AiohttpSession
        from aiogram.filters import Command, CommandStart
    except ImportError as exc:
        raise SystemExit("Install backend with the [bot] extra to run the Telegram bot") from exc
    # Telegram бывает доступен только через прокси (напр. в RU). Берём из настройки или env.
    proxy = (
        settings.telegram_proxy_url
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
    )
    session = AiohttpSession(proxy=proxy) if proxy else None
    dp = Dispatcher()
    dp.message.register(_on_start, CommandStart())
    dp.message.register(_on_today, Command("today"))
    dp.message.register(_on_slice, Command("slice"))
    dp.message.register(_on_ready, Command("ready"))
    dp.message.register(_on_progress, Command("progress"))
    dp.message.register(_on_help, Command("help"))
    dp.message.register(_on_cancel, Command("cancel"))
    dp.message.register(_on_skip, Command("skip"))
    dp.message.register(_on_send, Command("send"))  # родитель: /send <текст> ученику
    dp.message.register(_on_unknown_command, F.text.startswith("/"))
    dp.message.register(_on_answer, F.text)
    dp.message.register(_on_unsupported)
    dp.callback_query.register(_on_menu, F.data.startswith("menu:"))
    dp.callback_query.register(_on_slice_subject, F.data.startswith("slice:subj:"))
    dp.callback_query.register(_on_slice_topic, F.data.startswith("slice:topic:"))
    dp.callback_query.register(_on_slice_back, F.data == "slice:back")
    dp.callback_query.register(_on_ready_toggle, F.data.startswith("ready:t:"))
    dp.callback_query.register(_on_ready_done, F.data == "ready:done")
    bot = Bot(token=settings.telegram_bot_token, session=session)
    asyncio.run(_run(dp, bot))


if __name__ == "__main__":
    main()
