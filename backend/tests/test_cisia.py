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
from app.domain.multiple_choice import CISIA_PREFIX, choice_answer, cisia_number, cisia_section
from app.infrastructure.models import (
    AttemptORM,
    ErrorEventORM,
    EvidenceORM,
    MissionORM,
    ReviewItemORM,
    TaskORM,
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


@pytest.mark.parametrize(
    "number,section",
    [(1, "math"), (20, "math"), (21, "logic"), (30, "logic"), (31, None), (50, None)],
)
def test_cisia_sections_stop_before_science(number, section):
    assert cisia_section(CISIA_PREFIX + str(number)) == section


def test_import_logic_preserves_attempts_and_math_timer(
    seeded_session, session_factory, monkeypatch
):
    import json
    from pathlib import Path

    from scripts import import_cisia

    svc, task, original = setup_practice(seeded_session)
    result = asyncio.run(
        svc.submit_attempt(
            {
                "mission_id": original["id"],
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.UNKNOWN,
                "answer_text": "E",
            }
        )
    )
    monkeypatch.setattr(import_cisia, "SessionLocal", session_factory)
    monkeypatch.setattr("sys.argv", ["import_cisia", "--apply"])
    import_cisia.main()
    import_cisia.main()
    seeded_session.expire_all()
    tasks = seeded_session.scalars(select(TaskORM).where(TaskORM.source == "cisia_sample")).all()
    assert len(tasks) == 30
    missions = seeded_session.scalars(
        select(MissionORM).where(MissionORM.source_ref.like(CISIA_PREFIX + "%"))
    ).all()
    assert len(missions) == 30
    assert seeded_session.get(MissionORM, original["id"]).status == MissionStatus.DONE
    assert seeded_session.get(EvidenceORM, result["evidence_id"]).status == EvidenceStatus.PASSED
    queue = svc.list_cisia_drill(DEMO_STUDENT_ID)
    logic = [q for q in queue if q["cisia_number"] > 20]
    assert svc.list_cisia_drill(DEMO_STUDENT_ID, section="logic") == logic
    assert all(
        q["cisia_number"] <= 20 for q in svc.list_cisia_drill(DEMO_STUDENT_ID, section="math")
    )
    assert [q["cisia_number"] for q in logic] == list(range(21, 31))
    assert all("Логика" in q["title"] and "Логика" in q["statement"] for q in logic)
    assert all("expected_answer" not in q for q in logic)
    bundle = json.loads((Path(__file__).parents[1] / "data/cisia/logic.json").read_text())
    assert [q["expected_answer"] for q in bundle["questions"]] == list("CAADCDCCCD")
    by_number = {cisia_number(t.source_ref): t for t in tasks}
    assert all(
        by_number[q["number"]].expected_answer == q["expected_answer"] for q in bundle["questions"]
    )
    logic_result = asyncio.run(
        svc.submit_attempt(
            {
                "mission_id": logic[0]["id"],
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.UNKNOWN,
                "answer_text": "C",
            }
        )
    )
    assert logic_result["status"] == EvidenceStatus.PASSED  # BoomReviewer not called
    from app.adapters.telegram import bot

    message = AsyncMock()
    message.chat.id = 12346
    bot._cisia_active.add(12346)
    bot._cisia_sections[12346] = "logic"
    try:
        with patch.object(bot, "SessionLocal"), patch.object(bot, "_service", return_value=svc):
            asyncio.run(bot._send_next(message))
        assert "Логика" in message.answer_photo.call_args.kwargs["caption"]
        assert message.answer_photo.call_args.args[0].path.name == "q22.png"
    finally:
        bot._cisia_active.discard(12346)
        bot._cisia_sections.pop(12346, None)
        bot._awaiting.pop(12346, None)
        bot._presented.pop(12346, None)
    # Put logic first in any mixed pool: timed maths must still select only mathematics.
    monkeypatch.setattr(
        "app.application.use_cases.random.shuffle",
        lambda pool: pool.sort(key=lambda t: cisia_number(t["source_ref"]), reverse=True),
    )
    block = svc.start_timed_block(DEMO_STUDENT_ID)
    assert all(q["number"] <= 20 for q in block["tasks"])
