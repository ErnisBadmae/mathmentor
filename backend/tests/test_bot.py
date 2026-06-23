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

    async def answer(self, text: str) -> None:
        self.replies.append(text)


class FakeSettings:
    telegram_student_chat_id = "111"
    local_timezone = "Europe/Moscow"

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


def _patch_bot(monkeypatch, session_factory) -> None:
    bot._presented.clear()
    bot._awaiting.clear()
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

    start = FakeMessage(111)
    asyncio.run(bot._on_start(start))
    assert any("2+2" in reply for reply in start.replies)  # условие задачи пришло
    assert all("4" != reply.strip() for reply in start.replies)  # ответ-ключ не утёк

    answer = FakeMessage(111, text="4")
    asyncio.run(bot._on_answer(answer))
    assert any("Верно" in reply for reply in answer.replies)
