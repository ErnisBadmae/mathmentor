import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from app.application.use_cases import LearningService
from app.domain.enums import (
    AiPolicy,
    AttemptKind,
    AttemptMode,
    EvidenceStatus,
    MissionStatus,
    Subject,
)
from app.domain.multiple_choice import CISIA_PREFIX, choice_answer
from app.infrastructure.models import (
    AttemptORM,
    ErrorEventORM,
    EvidenceORM,
    MissionORM,
    ReviewItemORM,
)
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts.seed import DEMO_STUDENT_ID


class NoLLM:
    async def review_attempt(self, *args):
        raise AssertionError("CISIA must not call an LLM")

    async def assess(self, *args):
        raise AssertionError("CISIA must not call an LLM judge")


def setup_practice(session):
    service = LearningService(SqlAlchemyUnitOfWork(session), NoLLM(), judge=NoLLM())
    task = service.add_task(
        {
            "subject": Subject.MATH_PROFILE,
            "statement": "Источник: CISIA, вопрос 1, стр. 3.",
            "expected_answer": "E",
            "source": "cisia_sample",
            "source_ref": CISIA_PREFIX + "1",
        }
    )
    service.approve_task(task.id)
    mission = service.create_mission(
        {
            "student_id": DEMO_STUDENT_ID,
            "subject": Subject.MATH_PROFILE,
            "task_id": task.id,
            "title": "CISIA 1/20",
            "instructions": "Пришли A–E",
            "status": MissionStatus.ACTIVE,
            "ai_policy": AiPolicy.ATTEMPT_FIRST,
            "threshold_percent": 100,
            "source_ref": CISIA_PREFIX + "1",
            "due_date": date.today(),
        }
    )
    return service, task, mission


@pytest.mark.parametrize("text", ["A or E", "44", "А", "не знаю", "", "F"])
def test_ambiguous_choice_is_not_guessed(text):
    with pytest.raises(ValueError):
        choice_answer(text)


@pytest.mark.parametrize("answer,passed", [("e", True), ("Ответ: E", True), ("A", False)])
def test_official_key_records_once_without_ege_progression(seeded_session, answer, passed):
    service, task, mission = setup_practice(seeded_session)
    reviews_before = seeded_session.scalar(select(func.count()).select_from(ReviewItemORM))
    errors_before = seeded_session.scalar(select(func.count()).select_from(ErrorEventORM))
    submit = {
        "mission_id": mission["id"],
        "kind": AttemptKind.TEXT,
        "mode": AttemptMode.UNKNOWN,
        "answer_text": answer,
        "tasks_total": 10,
        "tasks_correct": 10,
    }
    result = asyncio.run(service.submit_attempt(submit))
    assert result["status"] == (EvidenceStatus.PASSED if passed else EvidenceStatus.FAILED)
    assert result["tasks_total"] == 1
    assert result["tasks_correct"] == int(passed)
    assert seeded_session.get(MissionORM, mission["id"]).status == MissionStatus.DONE
    evidence = seeded_session.get(EvidenceORM, result["evidence_id"])
    assert evidence.model_id == "official-answer-key"
    assert evidence.rubric_version == "cisia-sample-2021-mcq-v1"
    assert evidence.topic_id is None
    assert seeded_session.scalar(select(func.count()).select_from(ReviewItemORM)) == reviews_before
    assert seeded_session.scalar(select(func.count()).select_from(ErrorEventORM)) == errors_before
    assert task.id not in {
        item.id for item in service._uow.tasks.list_gradable(Subject.MATH_PROFILE)
    }
    assert not service.list_cisia_drill(DEMO_STUDENT_ID)
    with pytest.raises(ValueError, match="уже завершён"):
        asyncio.run(service.submit_attempt(submit))


def test_invalid_choice_keeps_question_open_without_failed_evidence(seeded_session):
    service, task, mission = setup_practice(seeded_session)
    before = seeded_session.scalar(select(func.count()).select_from(AttemptORM))
    with pytest.raises(ValueError, match="латинскую"):
        asyncio.run(
            service.submit_attempt(
                {
                    "mission_id": mission["id"],
                    "kind": AttemptKind.TEXT,
                    "mode": AttemptMode.UNKNOWN,
                    "answer_text": "A or E",
                }
            )
        )
    assert seeded_session.scalar(select(func.count()).select_from(AttemptORM)) == before
    assert seeded_session.get(MissionORM, mission["id"]).status == MissionStatus.ACTIVE
    payload = service.list_cisia_drill(DEMO_STUDENT_ID)[0]
    assert payload["cisia_number"] == 1
    assert "expected_answer" not in payload
    assert mission["id"] not in {p["id"] for p in service.list_daily_drill(DEMO_STUDENT_ID)}


def test_bot_sends_original_image_with_source_and_without_key(seeded_session):
    from app.adapters.telegram import bot

    service, task, mission = setup_practice(seeded_session)
    message = AsyncMock()
    message.chat.id = 12345
    bot._cisia_active.add(12345)
    bot._presented.pop(12345, None)
    try:
        with patch.object(bot, "SessionLocal"), patch.object(bot, "_service", return_value=service):
            asyncio.run(bot._send_next(message))
        message.answer_photo.assert_awaited_once()
        call = message.answer_photo.call_args
        assert "Источник: CISIA" in call.kwargs["caption"]
        assert "expected_answer" not in call.kwargs["caption"]
        assert bot._awaiting[12345] == mission["id"]
    finally:
        bot._cisia_active.discard(12345)
        bot._awaiting.pop(12345, None)
        bot._presented.pop(12345, None)
