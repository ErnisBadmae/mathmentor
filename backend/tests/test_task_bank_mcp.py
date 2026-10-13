"""Service layer behind the MCP server: task bank add/approve/list + attempt history."""

import asyncio

import pytest
from sqlalchemy import select

from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService
from app.domain.enums import (
    AiPolicy,
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    Subject,
    TaskStatus,
)
from app.infrastructure.models import MissionORM, TaskORM, TopicORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts import seed as seed_module

STUDENT = seed_module.DEMO_STUDENT_ID


class StaticReviewer:
    def __init__(self, draft: EvidenceDraft) -> None:
        self._draft = draft

    async def review_attempt(self, _attempt: AttemptForReview) -> EvidenceDraft:
        return self._draft


def draft(score: float) -> EvidenceDraft:
    return EvidenceDraft(
        score_percent=score,
        error_category=ErrorCategory.NONE,
        feedback="checked",
        next_action="next",
        model_id="local-model",
        prompt_version="p",
        rubric_version="r",
    )


def service(session, reviewer: object | None = None) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), reviewer or StaticReviewer(draft(0)))


def _vectors_topic(session) -> TopicORM:
    return session.scalar(select(TopicORM).where(TopicORM.title == "Векторы"))


def _task_values(session, source_url: str) -> dict:
    return {
        "subject": Subject.MATH_PROFILE,
        "statement": "Найдите длину вектора (3; 4).",
        "expected_answer": "5",
        "source": "official",
        "source_url": source_url,
        "source_ref": source_url,
        "topic_id": _vectors_topic(session).id,
    }


def test_add_task_is_draft_and_idempotent(seeded_session):
    svc = service(seeded_session)
    first = svc.add_task(_task_values(seeded_session, "https://example.org/task/1"))
    assert first.status == TaskStatus.DRAFT
    assert first.source == "official"
    again = svc.add_task(_task_values(seeded_session, "https://example.org/task/1"))
    assert again.id == first.id  # idempotent by source_ref

    drafts = svc.list_tasks(TaskStatus.DRAFT)
    drafted = next(d for d in drafts if d["id"] == first.id)
    assert drafted["source_url"] == "https://example.org/task/1"


def test_draft_not_counted_until_approved(seeded_session):
    svc = service(seeded_session)

    def vectors_bank() -> int:
        june = next(
            p for p in svc.list_program_progress(STUDENT) if p["key"] == "june_diagnostics"
        )
        return {r["topic_title"]: r["tasks_in_bank"] for r in june["topics"]}["Векторы"]

    assert vectors_bank() == 0
    task = svc.add_task(_task_values(seeded_session, "https://example.org/task/2"))
    assert vectors_bank() == 0  # draft excluded
    svc.approve_task(task.id)
    assert vectors_bank() == 1  # approved counts toward progress denominator


def test_approve_rejects_answer_not_writable_in_exam_blank(seeded_session):
    """Регресс 2026-08-11: задача с эталоном `2/3` дошла до ученицы. Она ответила 0,667 —
    верно по сути, точное сравнение сказало «не равно», в журнал ушёл ложный провал.
    У такой задачи нет ни одного правильного ответа, и одобрять её нельзя."""
    svc = service(seeded_session)
    values = _task_values(seeded_session, "https://example.org/task/blank-1")
    values["expected_answer"] = "2/3"
    task = svc.add_task(values)

    with pytest.raises(ValueError, match="EGE answer blank"):
        svc.approve_task(task.id)

    assert seeded_session.get(TaskORM, task.id).status == TaskStatus.DRAFT


def test_approve_accepts_fraction_equal_to_a_finite_decimal(seeded_session):
    """`3/8` записывается как 0,375 — запись дробью не мешает, важна представимость."""
    svc = service(seeded_session)
    values = _task_values(seeded_session, "https://example.org/task/blank-2")
    values["expected_answer"] = "3/8"
    task = svc.add_task(values)

    assert svc.approve_task(task.id).status == TaskStatus.APPROVED


def test_attempt_history_records_solution_and_interpretation(seeded_session):
    mission = seeded_session.scalar(select(MissionORM).order_by(MissionORM.id))
    asyncio.run(
        service(seeded_session, StaticReviewer(draft(90))).submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "моё решение",
            }
        )
    )
    history = service(seeded_session).list_attempt_history(STUDENT)
    assert history
    latest = history[0]
    assert latest["answer_text"] == "моё решение"
    assert latest["status"] == EvidenceStatus.PASSED
    assert latest["model_id"] == "local-model"


def test_seed_includes_part2_manual_gate_missions(seeded_session):
    rows = (
        seeded_session.query(MissionORM)
        .filter(MissionORM.source_ref.like("part2:text:%"))
        .order_by(MissionORM.source_ref)
        .all()
    )

    assert [row.source_ref for row in rows] == [
        "part2:text:13:trig-equation-a",
        "part2:text:15:log-inequality-a",
    ]
    assert all(row.ai_policy == AiPolicy.MANUAL_GATE for row in rows)
    assert all(row.task is not None for row in rows)
    assert all(row.task.expected_answer == "" for row in rows)


def test_seed_part2_13_mission_and_task_share_math_topic(seeded_session):
    mission = seeded_session.scalar(
        select(MissionORM).where(MissionORM.source_ref == "part2:text:13:trig-equation-a")
    )

    assert mission is not None
    assert mission.task is not None
    assert mission.topic_id == mission.task.topic_id
    assert mission.topic is not None
    assert mission.topic.subject == Subject.MATH_PROFILE
    assert mission.topic.task_number == "13"
