import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from app.application.use_cases import LearningService
from app.domain.enums import Subject
from app.domain.multiple_choice import grade_block
from app.infrastructure.models import (
    EvidenceORM,
    MissionORM,
    ReviewItemORM,
    ScoreEventORM,
    TimedBlockORM,
)
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts.seed import DEMO_STUDENT_ID as STUDENT


class NoLLM:
    async def review_attempt(self, *args):
        raise AssertionError("Timed practice must not call LLM")


@pytest.fixture
def svc(seeded_session):
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), NoLLM())
    data = json.loads((Path(__file__).parents[1] / "data/cisia/math.json").read_text())
    for q in data["questions"]:
        task = service.add_task(
            {
                "subject": Subject.MATH_PROFILE,
                "source": "cisia_sample",
                "source_ref": q["source_ref"],
                "statement": f"CISIA №{q['number']}",
                "expected_answer": q["expected_answer"],
            }
        )
        service.approve_task(task.id)
    return service


def test_grade_counts_skips_and_refuses_foreign_answers():
    assert grade_block({"q1": "a"}, {"q1": "A", "q2": "B"}) == (1, 2)
    with pytest.raises(ValueError):
        grade_block({"foreign": "A"}, {"q1": "A"})


def test_start_resume_no_keys_and_deadline_does_not_move(svc, seeded_session):
    first = svc.start_timed_block(STUDENT)
    assert len(first["tasks"]) == 5
    assert not first["finished"]
    assert "correct" not in first
    assert all("correct_answer" not in task for task in first["tasks"])
    fresh_service = LearningService(SqlAlchemyUnitOfWork(seeded_session), NoLLM())
    recovered = fresh_service.start_timed_block(STUDENT)
    assert recovered["id"] == first["id"]
    assert recovered["deadline_at"] == first["deadline_at"]
    assert seeded_session.scalar(select(func.count()).select_from(TimedBlockORM)) == 1


def test_change_finish_and_repeat_preserve_ege_truth(svc, seeded_session):
    models = [EvidenceORM, MissionORM, ReviewItemORM, ScoreEventORM]
    before = [seeded_session.scalar(select(func.count()).select_from(m)) for m in models]
    missions = [(m.id, m.status) for m in seeded_session.scalars(select(MissionORM))]
    block = svc.start_timed_block(STUDENT)
    row = seeded_session.get(TimedBlockORM, block["id"])
    expected = row.answer_key[row.task_ids[0]]
    svc.answer_timed_block(STUDENT, row.id, 0, "A")
    changed = svc.answer_timed_block(STUDENT, row.id, 0, expected)
    assert changed["tasks"][0]["answer"] == expected
    result = svc.finish_timed_block(STUDENT, row.id)
    assert result["correct"] == 1 and result["skipped"] == 4
    assert result["finish_reason"] == "submitted"
    finished_at = row.finished_at
    repeated = svc.finish_timed_block(STUDENT, row.id)
    assert repeated["correct"] == 1 and not repeated["newly_finished"]
    late = svc.answer_timed_block(STUDENT, row.id, 0, "B")
    assert late["tasks"][0]["answer"] == expected
    assert row.finished_at == finished_at
    assert before == [seeded_session.scalar(select(func.count()).select_from(m)) for m in models]
    assert missions == [(m.id, m.status) for m in seeded_session.scalars(select(MissionORM))]


def test_at_deadline_rejects_answer_and_caps_duration(svc, seeded_session, monkeypatch):
    block = svc.start_timed_block(STUDENT)
    row = seeded_session.get(TimedBlockORM, block["id"])
    deadline = block["deadline_at"]
    monkeypatch.setattr(svc._uow.timed_blocks, "now", lambda: deadline)
    result = svc.answer_timed_block(STUDENT, row.id, 0, "A")
    assert result["finished"] and result["finish_reason"] == "deadline"
    assert result["correct"] == 0 and result["skipped"] == 5
    assert result["elapsed_seconds"] == 600
    assert not row.answers


def test_stale_request_crossing_deadline_is_rejected_by_update(svc, seeded_session, monkeypatch):
    block = svc.start_timed_block(STUDENT)
    row = seeded_session.get(TimedBlockORM, block["id"])
    actual = svc._uow.timed_blocks.now()
    row.deadline_at = actual - timedelta(seconds=2)
    seeded_session.commit()
    times = iter([actual - timedelta(seconds=3), actual])
    monkeypatch.setattr(svc._uow.timed_blocks, "now", lambda: next(times))
    result = svc.answer_timed_block(STUDENT, row.id, 0, "A")
    assert result["finished"] and result["skipped"] == 5
    assert not row.answers


def test_previous_block_is_familiar_without_changing_new_block(svc, seeded_session):
    first = svc.start_timed_block(STUDENT)
    first_ids = seeded_session.get(TimedBlockORM, first["id"]).task_ids
    svc.finish_timed_block(STUDENT, first["id"])
    assert set(first_ids) <= svc._uow.timed_blocks.familiar_ids(STUDENT)
    second = svc.start_timed_block(STUDENT)
    assert second["id"] != first["id"]
    assert not any(task["familiar"] for task in second["tasks"])  # fresh pool first
    svc.answer_timed_block(STUDENT, first["id"], 0, "A")
    assert not seeded_session.get(TimedBlockORM, second["id"]).answers


def test_foreign_student_and_question_cannot_change_block(svc):
    from uuid import uuid4

    block = svc.start_timed_block(STUDENT)
    with pytest.raises(ValueError):
        svc.answer_timed_block(STUDENT, block["id"], 5, "A")
    with pytest.raises(ValueError):
        svc.answer_timed_block(STUDENT, block["id"], 0, "A or B")
    with pytest.raises(LookupError):
        svc.active_timed_block(uuid4(), block["id"])


def test_delivery_has_navigation_without_key_and_does_not_start_on_preview(svc):
    import asyncio

    from app.adapters.telegram import timed_practice as ui

    message = AsyncMock()
    with patch.object(ui, "SessionLocal"), patch.object(ui, "_service", return_value=svc):
        asyncio.run(ui.on_timed(message))
        message.answer.assert_awaited_once()
        assert not svc.active_timed_block(STUDENT)
        block = svc.start_timed_block(STUDENT)
        with patch.object(ui, "schedule"):
            asyncio.run(ui.show(message, block))
    call = message.answer_photo.call_args
    assert "ключ:" not in call.kwargs["caption"].lower()
    buttons = call.kwargs["reply_markup"].inline_keyboard
    assert len(buttons[0]) == 5 and len(buttons[1]) == 5
    assert max(len(b.callback_data.encode()) for row in buttons for b in row) <= 64
