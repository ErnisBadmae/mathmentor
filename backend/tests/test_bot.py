"""Telegram-адаптер: авторизация (шов №5) и happy-path дрилла через in-process сервис.

Хендлеры гоняются с фейковыми message/settings; ``bot.SessionLocal`` подменяется на тестовую
in-memory фабрику, так что бот работает на тех же сидовых данных, без сети и aiogram.
"""

import asyncio
from datetime import date
from uuid import uuid4

from app.adapters.telegram import bot
from app.application.use_cases import LearningService, RuleBasedReviewer
from app.domain.enums import AiPolicy, MissionStatus, Subject
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

    async def answer(self, text: str, **kwargs: object) -> None:
        self.replies.append(text)
        self.reply_markups.append(kwargs.get("reply_markup"))

    async def edit_text(self, text: str, **kwargs: object) -> None:
        self.replies.append(text)
        self.reply_markups.append(kwargs.get("reply_markup"))


class FakeCallback:
    def __init__(self, chat_id: int, data: str) -> None:
        self.message = FakeMessage(chat_id)
        self.data = data
        self.answers: list[str] = []

    async def answer(self, text: str = "", show_alert: bool = False) -> None:
        self.answers.append(text)


class FakeBot:
    def __init__(self) -> None:
        self.commands = []

    async def set_my_commands(self, commands) -> None:
        self.commands = commands


class FakeSettings:
    telegram_student_chat_id = "111"
    telegram_extra_chat_ids = ""
    local_timezone = "Europe/Moscow"
    authorized_chat_ids = ["111"]

    def llm_connection(self) -> None:
        return None


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
