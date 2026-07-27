"""Telegram-адаптер: авторизация (шов №5) и happy-path дрилла через in-process сервис.

Хендлеры гоняются с фейковыми message/settings; ``bot.SessionLocal`` подменяется на тестовую
in-memory фабрику, так что бот работает на тех же сидовых данных, без сети и aiogram.
"""

import asyncio
import logging
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.adapters.telegram import bot
from app.application.use_cases import LearningService, RuleBasedReviewer
from app.domain.enums import AiPolicy, MissionStatus, Subject
from app.infrastructure import telegram_send
from app.infrastructure.models import MissionORM, StudyLogEntryORM, TaskORM, TopicORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts import seed as seed_module

STUDENT = seed_module.DEMO_STUDENT_ID


class FakeChat:
    def __init__(self, chat_id: int) -> None:
        self.id = chat_id


class FakeMessage:
    def __init__(self, chat_id: int, text: str | None = None) -> None:
        self.chat = FakeChat(chat_id)
        self.text = text
        self.replies: list[str] = []
        self.reply_markups: list[object | None] = []
        self.photos: list[object] = []
        self.photo_captions: list[str | None] = []

    async def answer(self, text: str, **kwargs: object) -> None:
        self.replies.append(text)
        self.reply_markups.append(kwargs.get("reply_markup"))

    async def edit_text(self, text: str, **kwargs: object) -> None:
        self.replies.append(text)
        self.reply_markups.append(kwargs.get("reply_markup"))

    async def edit_reply_markup(self, reply_markup: object | None = None, **kwargs: object) -> None:
        self.reply_markups.append(reply_markup)

    async def answer_photo(self, photo: object, **kwargs: object) -> None:
        self.photos.append(photo)
        self.photo_captions.append(kwargs.get("caption"))


class FakeCallback:
    def __init__(self, chat_id: int, data: str) -> None:
        self.message = FakeMessage(chat_id)
        self.data = data
        self.answers: list[str] = []
        self.show_alerts: list[bool] = []

    async def answer(self, text: str = "", show_alert: bool = False) -> None:
        self.answers.append(text)
        self.show_alerts.append(show_alert)


class FakeBot:
    def __init__(self) -> None:
        self.commands = []
        self.sent: list[str] = []
        self.sent_chat_ids: list[int] = []

    async def set_my_commands(self, commands) -> None:
        self.commands = commands

    async def send_message(self, chat_id: int, text: str, **kwargs: object) -> None:
        self.sent.append(text)
        self.sent_chat_ids.append(chat_id)


class FakeSettings:
    telegram_student_chat_id = "111"
    telegram_extra_chat_ids = ""
    telegram_parent_chat_id = ""
    public_frontend_base_url = "https://mentor.example.test"
    local_timezone = "Europe/Moscow"
    authorized_chat_ids = ["111"]
    daily_drill_size = 5
    telegram_push_time = "16:00"
    telegram_reminder_repeat_hours = 2.0
    telegram_reminder_cutoff_time = "21:00"
    telegram_slice_reminder_days = 4
    telegram_parent_summary_time = "21:00"

    def llm_connection(self) -> None:
        return None


class PrivateFrontendSettings(FakeSettings):
    public_frontend_base_url = "http://192.168.1.60:8088"


def test_polling_failure_monitor_counts_recent_aiogram_failures():
    now = [1_000.0]
    monitor = bot.PollingFailureMonitor(
        now=lambda: now[0],
        window_seconds=60,
        threshold=2,
    )
    record = logging.LogRecord(
        "aiogram.dispatcher",
        logging.ERROR,
        "",
        1,
        "Failed to fetch updates - ProxyConnectionError",
        (),
        None,
    )

    monitor.emit(record)
    assert monitor.failure_count() == 1
    assert not monitor.should_restart()

    monitor.emit(record)
    assert monitor.failure_count() == 2
    assert monitor.should_restart()

    now[0] += 61
    assert monitor.failure_count() == 0
    assert not monitor.should_restart()


def _make_drill(session) -> None:
    svc = LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer())
    topic = TopicORM(
        id=uuid4(), subject=Subject.MATH_PROFILE, title="Бот тема", spec_year=2026, task_number=None
    )
    session.add(topic)
    session.commit()
    url = "https://example.org/bot/1"
    task = svc.add_task(
        {
            "subject": Subject.MATH_PROFILE,
            "statement": "Сколько будет 2+2?",
            "expected_answer": "4",
            "source": "official",
            "source_url": url,
            "source_ref": url,
            "topic_id": topic.id,
        }
    )
    svc.approve_task(task.id)
    svc.create_mission(
        {
            "student_id": STUDENT,
            "subject": Subject.MATH_PROFILE,
            "title": "Дрилл: Бот тема",
            "instructions": "",
            "status": MissionStatus.ACTIVE,
            "ai_policy": AiPolicy.ATTEMPT_FIRST,
            "threshold_percent": 80.0,
            "topic_id": topic.id,
            "task_id": task.id,
            "due_date": date.today(),
            "source_ref": "daily:manual",
        }
    )


def _make_interval_drill(session) -> None:
    svc = LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer())
    topic = TopicORM(
        id=uuid4(),
        subject=Subject.MATH_PROFILE,
        title="Бот интервал",
        spec_year=2026,
        task_number=None,
    )
    session.add(topic)
    session.commit()
    source_ref = "https://example.org/bot/interval"
    task = svc.add_task(
        {
            "subject": Subject.MATH_PROFILE,
            "statement": "Решите неравенство: 1 < x < 9.",
            "expected_answer": "(1; 9)",
            "source": "official",
            "source_url": source_ref,
            "source_ref": source_ref,
            "topic_id": topic.id,
        }
    )
    svc.approve_task(task.id)
    svc.create_mission(
        {
            "student_id": STUDENT,
            "subject": Subject.MATH_PROFILE,
            "title": "Дрилл: Бот интервал",
            "instructions": "",
            "status": MissionStatus.ACTIVE,
            "ai_policy": AiPolicy.ATTEMPT_FIRST,
            "threshold_percent": 80.0,
            "topic_id": topic.id,
            "task_id": task.id,
            "due_date": date.today(),
            "source_ref": "daily:manual:interval",
        }
    )


def _make_slice_topic(session) -> TopicORM:
    svc = LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer())
    topic = TopicORM(
        id=uuid4(), subject=Subject.MATH_PROFILE, title="Срез тема", spec_year=2026,
        task_number=None, phase="june_diagnostics", program_order=901,
    )
    session.add(topic)
    session.commit()
    for i in range(2):  # обе задачи с одним ключом "5" — ответ детерминирован независимо от порядка
        url = f"https://example.org/slice-bot/{i}"
        task = svc.add_task(
            {
                "subject": Subject.MATH_PROFILE,
                "statement": f"срез задача {i}",
                "expected_answer": "5",
                "source": "official",
                "source_url": url,
                "source_ref": url,
                "topic_id": topic.id,
            }
        )
        svc.approve_task(task.id)
    return topic


def _patch_bot(monkeypatch, session_factory) -> None:
    bot._presented.clear()
    bot._awaiting.clear()
    bot._srez.clear()
    monkeypatch.setattr(bot, "SessionLocal", session_factory)
    monkeypatch.setattr(bot, "get_settings", lambda: FakeSettings())


def test_unauthorized_chat_gets_its_id_and_no_drill(seeded_session, session_factory, monkeypatch):
    _make_drill(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    message = FakeMessage(999, text=None)  # не совпадает с настроенным 111
    asyncio.run(bot._on_start(message))

    assert any("chat_id: 999" in reply for reply in message.replies)
    assert all("Дрилл" not in reply for reply in message.replies)  # задача не выдана


def test_authorized_drill_flow_sends_task_and_grades(seeded_session, session_factory, monkeypatch):
    _make_drill(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    today = FakeMessage(111)
    asyncio.run(bot._on_today(today))
    assert any("2+2" in reply for reply in today.replies)  # условие задачи пришло
    assert all("4" != reply.strip() for reply in today.replies)  # ответ-ключ не утёк

    answer = FakeMessage(111, text="4")
    asyncio.run(bot._on_answer(answer))
    assert any("Верно" in reply for reply in answer.replies)


def test_task_text_includes_visual_concept_link(monkeypatch):
    monkeypatch.setattr(bot, "get_settings", lambda: FakeSettings())
    topic_id = uuid4()

    text = bot._task_text(
        {
            "title": "Векторы",
            "instructions": "Реши самостоятельно.",
            "statement": "Найдите координаты суммы векторов.",
            "topic_id": topic_id,
            "visual_ready": True,
        }
    )

    assert f"https://mentor.example.test/theory/{topic_id}" in text
    assert "expected_answer" not in text


def test_task_text_hides_private_visual_link(monkeypatch):
    monkeypatch.setattr(bot, "get_settings", lambda: PrivateFrontendSettings())
    topic_id = uuid4()

    text = bot._task_text(
        {
            "title": "Векторы",
            "instructions": "Реши и отправь ответ числом.",
            "statement": "Найдите скалярное произведение.",
            "topic_id": topic_id,
            "visual_ready": True,
        }
    )

    assert "192.168.1.60" not in text
    assert "Визуализация есть на сайте" in text
    assert "кратко распиши ход решения" not in text


def test_srez_task_includes_visual_concept_link(monkeypatch):
    monkeypatch.setattr(bot, "get_settings", lambda: FakeSettings())
    topic_id = uuid4()
    bot._srez[111] = {
        "subject": Subject.MATH_PROFILE,
        "items": [
            {
                "task_id": uuid4(),
                "topic_id": topic_id,
                "statement": "Найдите координаты суммы векторов.",
                "visual_ready": True,
            }
        ],
        "idx": 0,
        "judged": [],
    }
    message = FakeMessage(111)

    try:
        asyncio.run(bot._send_srez_task(message, 111))
    finally:
        bot._srez.clear()

    assert f"https://mentor.example.test/theory/{topic_id}" in message.replies[-1]


def test_interval_drill_answer_sends_visual_photo(seeded_session, session_factory, monkeypatch):
    _make_interval_drill(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    today = FakeMessage(111)
    asyncio.run(bot._on_today(today))
    assert any("1 < x < 9" in reply for reply in today.replies)

    answer = FakeMessage(111, text="(2; 7)")
    asyncio.run(bot._on_answer(answer))

    assert len(answer.photos) == 1
    assert answer.photo_captions == ["\U0001f4ca Синее — решение, оранжевое — твой ответ"]


def test_start_shows_menu_without_starting_drill(
    seeded_session, session_factory, monkeypatch
):
    _make_drill(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    message = FakeMessage(111)
    asyncio.run(bot._on_start(message))

    assert any("помогу" in reply.lower() for reply in message.replies)
    assert all("2+2" not in reply for reply in message.replies)
    assert message.reply_markups[-1] is not None


def test_idle_text_does_not_start_drill(seeded_session, session_factory, monkeypatch):
    _make_drill(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    message = FakeMessage(111, text="привет")
    asyncio.run(bot._on_answer(message))

    assert any("нет активного задания" in reply.lower() for reply in message.replies)
    assert all("2+2" not in reply for reply in message.replies)


def test_progress_uses_dashboard_truth(seeded_session, session_factory, monkeypatch):
    _patch_bot(monkeypatch, session_factory)

    message = FakeMessage(111)
    asyncio.run(bot._on_progress(message))

    assert any("65 из 85" in reply for reply in message.replies)
    assert any("50 из 85" in reply for reply in message.replies)
    assert any("Код без подсказок: 40%" in reply for reply in message.replies)


class _FakeSender:
    """Заглушка send_telegram_message: собирает, что и куда ушло бы в Telegram."""

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.sent_chat_ids: list[int] = []

    def __call__(self, settings, chat_id: int, text: str) -> None:
        self.sent.append(text)
        self.sent_chat_ids.append(chat_id)


def _patch_delivery(monkeypatch, session_factory) -> _FakeSender:
    monkeypatch.setattr(telegram_send, "SessionLocal", session_factory)
    sender = _FakeSender()
    monkeypatch.setattr(telegram_send, "send_telegram_message", sender)
    return sender


def test_mentor_notes_delivered_once(seeded_session, session_factory, monkeypatch):
    # агент опубликовал заметку → доставляется ученику ровно один раз (идемпотентно)
    LearningService(SqlAlchemyUnitOfWork(seeded_session), RuleBasedReviewer()).publish_feedback(
        {"student_id": STUDENT, "body": "Молодец, дробные неравенства теперь идут!"}
    )
    sender = _patch_delivery(monkeypatch, session_factory)

    assert telegram_send.deliver_pending_notes(FakeSettings(), STUDENT) == 1
    assert any("дробные неравенства" in text for text in sender.sent)
    assert any("От наставника" in text for text in sender.sent)

    sender.sent.clear()
    assert telegram_send.deliver_pending_notes(FakeSettings(), STUDENT) == 0  # повтор не дублирует
    assert sender.sent == []


def test_parent_pinged_on_delivery(seeded_session, session_factory, monkeypatch):
    # при доставке заметки ученику родитель-контролёр получает пинг (видит, что и когда ушло)
    LearningService(SqlAlchemyUnitOfWork(seeded_session), RuleBasedReviewer()).publish_feedback(
        {"student_id": STUDENT, "body": "Срез по вероятности: 1/3, разбираем тему."}
    )
    sender = _patch_delivery(monkeypatch, session_factory)
    monkeypatch.setattr(FakeSettings, "telegram_parent_chat_id", "222")

    telegram_send.deliver_pending_notes(FakeSettings(), STUDENT)
    assert 111 in sender.sent_chat_ids  # ученик получил заметку
    assert 222 in sender.sent_chat_ids  # родитель получил пинг
    assert any("доставлена ученику" in text for text in sender.sent)


def test_long_mentor_note_is_split_under_telegram_limit(
    seeded_session, session_factory, monkeypatch
):
    # заметка длиннее лимита Telegram (4096) режется на части, доставка не срывается
    LearningService(SqlAlchemyUnitOfWork(seeded_session), RuleBasedReviewer()).publish_feedback(
        {"student_id": STUDENT, "body": "А" * 9000}
    )
    sender = _patch_delivery(monkeypatch, session_factory)

    telegram_send.deliver_pending_notes(FakeSettings(), STUDENT)
    assert len(sender.sent) == 3  # 9000 + префикс → 4096 + 4096 + остаток
    assert all(len(text) <= 4096 for text in sender.sent)


def test_registers_native_telegram_commands():
    fake = FakeBot()

    asyncio.run(bot._register_commands(fake))

    assert [command.command for command in fake.commands] == [
        "start",
        "today",
        "slice",
        "ready",
        "topics",
        "progress",
        "help",
        "cancel",
        "skip",
    ]


def test_today_does_not_build_an_empty_queue(session_factory, monkeypatch):
    _patch_bot(monkeypatch, session_factory)

    message = FakeMessage(111)
    asyncio.run(bot._on_today(message))

    assert any("всё сделано" in reply.lower() for reply in message.replies)
    with session_factory() as session:
        assert LearningService(
            SqlAlchemyUnitOfWork(session), RuleBasedReviewer()
        ).list_daily_drill(STUDENT) == []


def test_menu_today_and_cancel_share_drill_state(
    seeded_session, session_factory, monkeypatch
):
    _make_drill(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    callback = FakeCallback(111, "menu:today")
    asyncio.run(bot._on_menu(callback))
    assert any("2+2" in reply for reply in callback.message.replies)
    assert callback.answers == [""]
    assert 111 in bot._awaiting

    cancel = FakeMessage(111, text="/cancel")
    asyncio.run(bot._on_cancel(cancel))
    assert 111 not in bot._awaiting
    assert any("остановлен" in reply.lower() for reply in cancel.replies)


def test_skip_in_slice_excludes_task_from_count(seeded_session, session_factory, monkeypatch):
    topic = _make_slice_topic(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    asyncio.run(bot._on_slice(FakeMessage(111, text="/slice")))
    pick = FakeCallback(111, f"slice:topic:{topic.id}")
    asyncio.run(bot._on_slice_topic(pick))

    skip = FakeMessage(111, text="/skip")
    asyncio.run(bot._on_skip(skip))
    assert any("Пропущено" in reply for reply in skip.replies)
    assert any("Задача 2/2" in reply for reply in skip.replies)

    ans = FakeMessage(111, text="5")
    asyncio.run(bot._on_answer(ans))
    # 1 пропущена (не входит ни в total, ни в correct), 1 отвечена верно -> 1/1
    assert any("Срез готов: 1/1" in reply and "зачёт" in reply for reply in ans.replies)
    assert 111 not in bot._srez


def test_skip_daily_drill_defers_mission_and_shows_next(
    seeded_session, session_factory, monkeypatch
):
    _make_drill(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    start = FakeMessage(111, text="/today")
    asyncio.run(bot._on_today(start))
    assert 111 in bot._awaiting
    mission_id = bot._awaiting[111]

    skip = FakeMessage(111, text="/skip")
    asyncio.run(bot._on_skip(skip))

    assert any("Пропущено" in reply for reply in skip.replies)
    assert any("всё сделано" in reply.lower() for reply in skip.replies)  # больше дрилла нет
    assert 111 not in bot._awaiting
    with session_factory() as session:
        mission = session.get(MissionORM, mission_id)
        assert mission.status == MissionStatus.ACTIVE  # осталась открытой, не провалена


def test_skip_without_active_task_is_a_noop(session_factory, monkeypatch):
    _patch_bot(monkeypatch, session_factory)

    skip = FakeMessage(111, text="/skip")
    asyncio.run(bot._on_skip(skip))

    assert any("нет активной задачи" in reply.lower() for reply in skip.replies)


def test_today_task_message_has_skip_button(seeded_session, session_factory, monkeypatch):
    _make_drill(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    message = FakeMessage(111, text="/today")
    asyncio.run(bot._on_today(message))

    mission_id = bot._awaiting[111]
    markup = message.reply_markups[-1]
    assert markup is not None
    button = markup.inline_keyboard[0][0]
    assert button.text == "⏭ Пропустить"
    assert button.callback_data == f"today:skip:{mission_id}"


def test_today_skip_button_defers_and_shows_next(seeded_session, session_factory, monkeypatch):
    _make_drill(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    start = FakeMessage(111, text="/today")
    asyncio.run(bot._on_today(start))
    mission_id = bot._awaiting[111]

    callback = FakeCallback(111, f"today:skip:{mission_id}")
    asyncio.run(bot._on_today_skip(callback))

    assert callback.answers == [""]
    assert any("Пропущено" in reply for reply in callback.message.replies)
    assert any("всё сделано" in reply.lower() for reply in callback.message.replies)
    assert 111 not in bot._awaiting
    with session_factory() as session:
        mission = session.get(MissionORM, mission_id)
        assert mission.status == MissionStatus.ACTIVE  # осталась открытой, не провалена


def test_today_skip_button_stale_mission_is_noop(seeded_session, session_factory, monkeypatch):
    _make_drill(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    start = FakeMessage(111, text="/today")
    asyncio.run(bot._on_today(start))
    mission_id = bot._awaiting[111]

    # тап по клавиатуре старого сообщения после того, как /cancel уже сбросил ожидание
    asyncio.run(bot._on_cancel(FakeMessage(111, text="/cancel")))
    callback = FakeCallback(111, f"today:skip:{mission_id}")
    asyncio.run(bot._on_today_skip(callback))

    assert callback.show_alerts == [True]
    assert callback.message.replies == []


def test_unauthorized_menu_callback_is_rejected(session_factory, monkeypatch):
    _patch_bot(monkeypatch, session_factory)

    callback = FakeCallback(999, "menu:today")
    asyncio.run(bot._on_menu(callback))

    assert callback.show_alerts == [True]
    assert callback.message.replies == []


def test_slice_flow_subject_topic_then_grade(seeded_session, session_factory, monkeypatch):
    topic = _make_slice_topic(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    start = FakeMessage(111, text="/slice")
    asyncio.run(bot._on_slice(start))
    assert any("предмет" in reply.lower() for reply in start.replies)

    subj = FakeCallback(111, "slice:subj:math_profile")
    asyncio.run(bot._on_slice_subject(subj))
    assert any("тему" in reply.lower() for reply in subj.message.replies)

    pick = FakeCallback(111, f"slice:topic:{topic.id}")
    asyncio.run(bot._on_slice_topic(pick))
    assert any("Задача 1/2" in reply for reply in pick.message.replies)
    assert all("5" != reply.strip() for reply in pick.message.replies)  # ключ не утёк

    ans1 = FakeMessage(111, text="5")
    asyncio.run(bot._on_answer(ans1))
    assert any("Задача 2/2" in reply for reply in ans1.replies)

    ans2 = FakeMessage(111, text="5")
    asyncio.run(bot._on_answer(ans2))
    assert any("Срез готов: 2/2" in reply and "зачёт" in reply for reply in ans2.replies)
    assert 111 not in bot._srez  # сессия закрыта


def test_cancel_clears_active_slice(seeded_session, session_factory, monkeypatch):
    topic = _make_slice_topic(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    asyncio.run(bot._on_slice(FakeMessage(111, text="/slice")))
    pick = FakeCallback(111, f"slice:topic:{topic.id}")
    asyncio.run(bot._on_slice_topic(pick))
    assert 111 in bot._srez

    cancel = FakeMessage(111, text="/cancel")
    asyncio.run(bot._on_cancel(cancel))

    assert 111 not in bot._srez
    assert 111 not in bot._awaiting
    assert cancel.reply_markups[-1] is not None


def test_unauthorized_slice_callback_is_rejected(session_factory, monkeypatch):
    _patch_bot(monkeypatch, session_factory)

    callback = FakeCallback(999, "slice:subj:math_profile")
    asyncio.run(bot._on_slice_subject(callback))

    assert callback.show_alerts == [True]
    assert callback.message.replies == []


def test_help_shows_home_keyboard(session_factory, monkeypatch):
    _patch_bot(monkeypatch, session_factory)

    message = FakeMessage(111, text="/help")
    asyncio.run(bot._on_help(message))

    assert message.replies
    assert message.reply_markups[-1] is not None


def _make_ready_topic(session, title: str = "Бот ready тема") -> TopicORM:
    """Открытая тема июньской фазы с одобренной задачей — кандидат для /ready."""
    svc = LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer())
    topic = TopicORM(
        id=uuid4(),
        subject=Subject.MATH_PROFILE,
        title=title,
        spec_year=2026,
        task_number=None,
        phase="june_diagnostics",
        program_order=950,
    )
    session.add(topic)
    session.commit()
    url = f"https://example.org/bot/ready/{topic.id}"
    task = svc.add_task(
        {
            "subject": Subject.MATH_PROFILE,
            "statement": "Сколько будет 3+3?",
            "expected_answer": "6",
            "source": "official",
            "source_url": url,
            "source_ref": url,
            "topic_id": topic.id,
        }
    )
    svc.approve_task(task.id)
    return topic


def test_ready_lists_candidates_with_keyboard(seeded_session, session_factory, monkeypatch):
    _make_ready_topic(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    message = FakeMessage(111, text="/ready")
    asyncio.run(bot._on_ready(message))

    assert any("Отметь темы" in reply for reply in message.replies)
    markup = message.reply_markups[-1]
    assert markup is not None
    button_texts = [btn.text for row in markup.inline_keyboard for btn in row]
    assert any("Бот ready тема" in text for text in button_texts)
    assert any(text == "Готово" for text in button_texts)
    # part-2/manual-path темы не предлагаются
    assert all("Стереометрия" not in text for text in button_texts)


def test_ready_toggle_marks_topic_and_updates_keyboard(
    seeded_session, session_factory, monkeypatch
):
    topic = _make_ready_topic(seeded_session)
    _patch_bot(monkeypatch, session_factory)
    svc = LearningService(SqlAlchemyUnitOfWork(seeded_session), RuleBasedReviewer())

    callback = FakeCallback(111, f"ready:t:{topic.id}")
    asyncio.run(bot._on_ready_toggle(callback))

    assert callback.answers and "Отмечено" in callback.answers[-1]
    seeded_session.expire_all()
    rows = svc.list_theory_ready_candidates(STUDENT)
    assert next(r for r in rows if r["topic_id"] == topic.id)["theory_ready"] is True
    # клавиатура перерисована с галочкой
    markup = callback.message.reply_markups[-1]
    assert any(
        btn.text.startswith("✅") and "Бот ready тема" in btn.text
        for row in markup.inline_keyboard
        for btn in row
    )


def test_ready_callbacks_unauthorized_rejected(session_factory, monkeypatch):
    _patch_bot(monkeypatch, session_factory)

    toggle = FakeCallback(999, f"ready:t:{uuid4()}")
    asyncio.run(bot._on_ready_toggle(toggle))
    done = FakeCallback(999, "ready:done")
    asyncio.run(bot._on_ready_done(done))

    assert toggle.show_alerts == [True]
    assert done.show_alerts == [True]
    assert toggle.message.replies == []
    assert done.message.replies == []


def test_topics_lists_candidates_with_keyboard(seeded_session, session_factory, monkeypatch):
    _make_ready_topic(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    message = FakeMessage(111, text="/topics")
    asyncio.run(bot._on_topics(message))

    assert any("Выбери тему" in reply for reply in message.replies)
    markup = message.reply_markups[-1]
    assert markup is not None
    button_texts = [btn.text for row in markup.inline_keyboard for btn in row]
    assert any("Бот ready тема" in text for text in button_texts)
    # part-2/manual-path темы не предлагаются
    assert all("Стереометрия" not in text for text in button_texts)


def test_topics_pick_adds_mission_and_confirms(seeded_session, session_factory, monkeypatch):
    topic = _make_ready_topic(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    callback = FakeCallback(111, f"topics:pick:{topic.id}")
    asyncio.run(bot._on_topics_pick(callback))

    assert callback.answers[-1] == "Добавлено ✅"
    assert any("добавила в «Сегодня»" in reply for reply in callback.message.replies)
    with session_factory() as session:
        mission = session.scalar(
            select(MissionORM).where(MissionORM.source_ref == f"daily:self:{topic.id}")
        )
        assert mission is not None
        assert mission.status == MissionStatus.ACTIVE


def test_topics_pick_shortage_shows_alert_without_creating_mission(
    seeded_session, session_factory, monkeypatch
):
    topic = _make_ready_topic(seeded_session)
    with session_factory() as session:
        # единственная задача темы уже назначена другой миссией — свежей не осталось
        task = session.scalar(select(TaskORM).where(TaskORM.topic_id == topic.id))
        session.add(
            MissionORM(
                id=uuid4(),
                student_id=STUDENT,
                subject=Subject.MATH_PROFILE,
                topic_id=topic.id,
                task_id=task.id,
                title="прошлая",
                instructions="",
                status=MissionStatus.DONE,
                ai_policy=AiPolicy.ATTEMPT_FIRST,
                threshold_percent=80.0,
            )
        )
        session.commit()
    _patch_bot(monkeypatch, session_factory)

    callback = FakeCallback(111, f"topics:pick:{topic.id}")
    asyncio.run(bot._on_topics_pick(callback))

    assert callback.show_alerts == [True]
    assert "нет свежих задач" in callback.answers[-1]
    with session_factory() as session:
        assert (
            session.scalar(
                select(MissionORM).where(MissionORM.source_ref == f"daily:self:{topic.id}")
            )
            is None
        )


def test_topics_callbacks_unauthorized_rejected(session_factory, monkeypatch):
    _patch_bot(monkeypatch, session_factory)

    pick = FakeCallback(999, f"topics:pick:{uuid4()}")
    asyncio.run(bot._on_topics_pick(pick))

    assert pick.show_alerts == [True]
    assert pick.message.replies == []

    more = FakeCallback(999, f"topics:more:{uuid4()}")
    asyncio.run(bot._on_topics_more(more))
    assert more.show_alerts == [True]
    assert more.message.replies == []


def _make_two_task_ready_topic(session) -> TopicORM:
    """Тема части 1 с ДВУМЯ approved-задачами — чтобы после ответа осталась свежая для «ещё»."""
    svc = LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer())
    topic = TopicORM(
        id=uuid4(),
        subject=Subject.MATH_PROFILE,
        title="Бот ещё тема",
        spec_year=2026,
        task_number=None,
        phase="june_diagnostics",
        program_order=951,
    )
    session.add(topic)
    session.commit()
    for i in range(2):
        url = f"https://example.org/bot/more/{topic.id}/{i}"
        task = svc.add_task(
            {
                "subject": Subject.MATH_PROFILE,
                "statement": f"Сколько будет {i}+{i}?",
                "expected_answer": str(i + i),
                "source": "official",
                "source_url": url,
                "source_ref": url,
                "topic_id": topic.id,
            }
        )
        svc.approve_task(task.id)
    return topic


def test_answer_verdict_has_more_button(seeded_session, session_factory, monkeypatch):
    topic = _make_two_task_ready_topic(seeded_session)
    _patch_bot(monkeypatch, session_factory)
    # открыть задачу по теме и ответить
    svc = LearningService(SqlAlchemyUnitOfWork(seeded_session), RuleBasedReviewer())
    result = svc.self_add_topic_mission(STUDENT, topic.id)
    mission_id = result["mission"]["id"]
    bot._awaiting[111] = mission_id

    ans = FakeMessage(111, text="0")
    asyncio.run(bot._on_answer(ans))

    # к сообщению-вердикту прикреплена кнопка «Ещё по этой теме» с topic_id
    verdict_markup = ans.reply_markups[0]
    assert verdict_markup is not None
    btn = verdict_markup.inline_keyboard[0][0]
    assert btn.text == "🔁 Ещё по этой теме"
    assert btn.callback_data == f"topics:more:{topic.id}"


def test_topics_more_serves_fresh_same_topic_task(seeded_session, session_factory, monkeypatch):
    topic = _make_two_task_ready_topic(seeded_session)
    _patch_bot(monkeypatch, session_factory)

    callback = FakeCallback(111, f"topics:more:{topic.id}")
    asyncio.run(bot._on_topics_more(callback))

    assert callback.answers[-1] == "Лови ещё ✅"
    assert callback.message.replies  # прислана новая задача
    assert 111 in bot._awaiting  # ожидание ответа выставлено
    with session_factory() as session:
        mission = session.scalar(
            select(MissionORM)
            .where(MissionORM.source_ref == f"daily:self:{topic.id}")
            .where(MissionORM.status == MissionStatus.ACTIVE)
        )
        assert mission is not None


def test_topics_more_shortage_shows_alert(seeded_session, session_factory, monkeypatch):
    topic = _make_ready_topic(seeded_session, "Бот ещё пусто")  # одна задача
    with session_factory() as session:
        task = session.scalar(select(TaskORM).where(TaskORM.topic_id == topic.id))
        session.add(
            MissionORM(
                id=uuid4(),
                student_id=STUDENT,
                subject=Subject.MATH_PROFILE,
                topic_id=topic.id,
                task_id=task.id,
                title="прошлая",
                instructions="",
                status=MissionStatus.DONE,
                ai_policy=AiPolicy.ATTEMPT_FIRST,
                threshold_percent=80.0,
            )
        )
        session.commit()
    _patch_bot(monkeypatch, session_factory)

    callback = FakeCallback(111, f"topics:more:{topic.id}")
    asyncio.run(bot._on_topics_more(callback))

    assert callback.show_alerts == [True]
    assert "кончились" in callback.answers[-1]


def test_run_daily_push_sends_encouraging_text_and_slice_reminder(
    seeded_session, session_factory, monkeypatch
):
    topic = _make_ready_topic(seeded_session, "Бот push тема")
    svc = LearningService(SqlAlchemyUnitOfWork(seeded_session), RuleBasedReviewer())
    svc.set_topic_theory_ready(topic.id, True)
    seeded_session.add(
        StudyLogEntryORM(
            id=uuid4(),
            student_id=STUDENT,
            subject=Subject.MATH_PROFILE,
            occurred_on=date.today() - timedelta(days=10),
            topic_title="старый срез",
            tasks_total=5,
            tasks_correct=5,
            percent_correct=100.0,
        )
    )
    seeded_session.commit()
    _patch_bot(monkeypatch, session_factory)
    # deliver_pending_notes уходит в отдельный поток (asyncio.to_thread) — там sqlite
    # ":memory:" уже другая, пустая БД; доставку заметок здесь не проверяем, глушим.
    monkeypatch.setattr(bot, "deliver_pending_notes", lambda *a, **k: 0)
    fake_bot = FakeBot()

    asyncio.run(bot._run_daily_push(fake_bot, 111))

    assert any("вперёд" in text.lower() for text in fake_bot.sent)
    assert any("срез" in text.lower() and "/slice" in text for text in fake_bot.sent)


def test_run_daily_push_skips_slice_reminder_when_recent(
    seeded_session, session_factory, monkeypatch
):
    topic = _make_ready_topic(seeded_session, "Бот push свежая тема")
    svc = LearningService(SqlAlchemyUnitOfWork(seeded_session), RuleBasedReviewer())
    svc.set_topic_theory_ready(topic.id, True)
    seeded_session.add(
        StudyLogEntryORM(
            id=uuid4(),
            student_id=STUDENT,
            subject=Subject.MATH_PROFILE,
            occurred_on=date.today(),
            topic_title="свежий срез",
            tasks_total=5,
            tasks_correct=5,
            percent_correct=100.0,
        )
    )
    seeded_session.commit()
    _patch_bot(monkeypatch, session_factory)
    # deliver_pending_notes уходит в отдельный поток (asyncio.to_thread) — там sqlite
    # ":memory:" уже другая, пустая БД; доставку заметок здесь не проверяем, глушим.
    monkeypatch.setattr(bot, "deliver_pending_notes", lambda *a, **k: 0)
    fake_bot = FakeBot()

    asyncio.run(bot._run_daily_push(fake_bot, 111))

    assert any("вперёд" in text.lower() for text in fake_bot.sent)
    assert not any("/slice" in text for text in fake_bot.sent)


def test_parent_summary_text_covers_states(monkeypatch):
    monkeypatch.setattr(bot, "get_settings", lambda: FakeSettings())
    started = bot._parent_summary_text(
        "Ульяна", {"attempted_today": True, "drill_open": 1, "days_since_slice": 1}
    )
    assert "занималась" in started

    not_started = bot._parent_summary_text(
        "Ульяна", {"attempted_today": False, "drill_open": 2, "days_since_slice": None}
    )
    assert "ещё не приступала" in not_started
    assert "Срезов пока не было" in not_started

    nothing_today = bot._parent_summary_text(
        "Ульяна", {"attempted_today": False, "drill_open": 0, "days_since_slice": 1}
    )
    assert "заданий" in nothing_today and "не было" in nothing_today
