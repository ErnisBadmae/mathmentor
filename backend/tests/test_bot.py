"""Telegram-адаптер: авторизация (шов №5) и happy-path дрилла через in-process сервис.

Хендлеры гоняются с фейковыми message/settings; ``bot.SessionLocal`` подменяется на тестовую
in-memory фабрику, так что бот работает на тех же сидовых данных, без сети и aiogram.
"""

import asyncio
import logging
from datetime import date
from uuid import uuid4

from app.adapters.telegram import bot
from app.application.use_cases import LearningService, RuleBasedReviewer
from app.domain.enums import AiPolicy, MissionStatus, Subject
from app.infrastructure import telegram_send
from app.infrastructure.models import TopicORM
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
    local_timezone = "Europe/Moscow"
    authorized_chat_ids = ["111"]

    def llm_connection(self) -> None:
        return None


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
        id=uuid4(), subject=Subject.MATH_PROFILE, title="Р‘РѕС‚ РёРЅС‚РµСЂРІР°Р»", spec_year=2026, task_number=None
    )
    session.add(topic)
    session.commit()
    source_ref = "https://example.org/bot/interval"
    task = svc.add_task(
        {
            "subject": Subject.MATH_PROFILE,
            "statement": "Р РµС€РёС‚Рµ РЅРµСЂР°РІРµРЅСЃС‚РІРѕ: 1 < x < 9.",
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
            "title": "Р”СЂРёР»Р»: Р‘РѕС‚ РёРЅС‚РµСЂРІР°Р»",
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
        "progress",
        "help",
        "cancel",
    ]


def test_today_does_not_build_an_empty_queue(session_factory, monkeypatch):
    _patch_bot(monkeypatch, session_factory)

    message = FakeMessage(111)
    asyncio.run(bot._on_today(message))

    assert any("открытых заданий нет" in reply.lower() for reply in message.replies)
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
