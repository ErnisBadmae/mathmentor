"""Service layer behind the MCP server: task bank add/approve/list + attempt history."""

import asyncio

from sqlalchemy import select

from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService
from app.domain.enums import (
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    Subject,
    TaskStatus,
)
from app.infrastructure.models import MissionORM, TopicORM
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
