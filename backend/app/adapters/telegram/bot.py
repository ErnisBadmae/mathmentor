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
import os
from typing import Any
from uuid import UUID

from app.application.use_cases import LearningService, RuleBasedReviewer
from app.config import get_settings
from app.domain.enums import AttemptKind, AttemptMode
from app.infrastructure.db import SessionLocal
from app.infrastructure.llm import OpenAICompatibleReviewer
from app.infrastructure.repositories import SqlAlchemyUnitOfWork

# One student in the family pilot (the all-zero UUID the frontend/seed/MCP use).
PILOT_STUDENT_ID = UUID("00000000-0000-0000-0000-000000000000")

# Cache only (DB is the source of truth via list_daily_drill): which drill missions were
# already shown this run, and which one each chat is currently answering. Survivable across
# restarts — on restart we simply re-present whatever is still open.
_presented: dict[int, set[UUID]] = {}
_awaiting: dict[int, UUID] = {}


def _service(session: Any) -> LearningService:
    settings = get_settings()
    connection = settings.llm_connection()
    reviewer = OpenAICompatibleReviewer(connection) if connection else RuleBasedReviewer()
    return LearningService(SqlAlchemyUnitOfWork(session), reviewer, settings.local_timezone)


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


def _is_student_chat(message: Any) -> bool:
    configured = get_settings().telegram_student_chat_id
    return not configured or str(message.chat.id) == str(configured)


def _task_text(payload: dict[str, object]) -> str:
    parts: list[str] = [str(payload["title"])]
    if payload.get("statement"):
        parts.append(str(payload["statement"]))
    if payload.get("instructions"):
        parts.append(str(payload["instructions"]))
    parts.append("Напиши свой ответ одним сообщением.")
    return "\n\n".join(parts)


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


async def _send_next(message: Any) -> None:
    chat_id = message.chat.id
    with SessionLocal() as session:
        drills = _service(session).list_daily_drill(PILOT_STUDENT_ID)
    presented = _presented.setdefault(chat_id, set())
    nxt = next((d for d in drills if d["id"] not in presented), None)
    if nxt is None:
        _awaiting.pop(chat_id, None)
        await message.answer("На сегодня задачи закончились 🎉")
        return
    mission_id = nxt["id"]
    assert isinstance(mission_id, UUID)
    presented.add(mission_id)
    _awaiting[chat_id] = mission_id
    await message.answer(_task_text(nxt))


async def _on_start(message: Any) -> None:
    if not _is_student_chat(message):
        return
    _presented.pop(message.chat.id, None)
    await message.answer("Погнали! Решаем задачи по одной.")
    await _send_next(message)


async def _on_answer(message: Any) -> None:
    if not _is_student_chat(message):
        return
    chat_id = message.chat.id
    mission_id = _awaiting.get(chat_id)
    if mission_id is None:
        await _send_next(message)
        return
    with SessionLocal() as session:
        result = await _service(session).submit_attempt(
            {
                "mission_id": mission_id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.UNKNOWN,
                "answer_text": message.text or "",
            }
        )
    _awaiting.pop(chat_id, None)
    await message.answer(_verdict_text(result))
    await _send_next(message)


def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit("Set telegram_bot_token to run the Telegram bot")
    try:
        from aiogram import Bot, Dispatcher, F
        from aiogram.client.session.aiohttp import AiohttpSession
        from aiogram.filters import CommandStart
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
    dp.message.register(_on_answer, F.text)
    bot = Bot(token=settings.telegram_bot_token, session=session)
    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()
