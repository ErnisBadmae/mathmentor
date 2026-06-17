"""Step 5: срез history (diagnostics) + per-topic progress counts."""

import asyncio

from sqlalchemy import func, select

from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService
from app.domain.enums import AttemptKind, AttemptMode, ErrorCategory, TaskStatus
from app.infrastructure.models import ErrorEventORM, MissionORM, StudyLogEntryORM, TaskORM
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
        feedback="f",
        next_action="n",
        model_id="m",
        prompt_version="p",
        rubric_version="r",
    )


def service(session, reviewer: object | None = None) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), reviewer or StaticReviewer(draft(0)))


def test_srez_diagnostics_seeded(seeded_session):
    diags = service(seeded_session).list_diagnostics(STUDENT)
    by_label = {d["label"]: d for d in diags}
    assert "Срез №1 — 4 темы" in by_label
    assert by_label["Срез №1 — 4 темы"]["tasks_total"] == 12
    assert by_label["Срез №1 — 4 темы"]["tasks_correct"] == 10
    assert by_label["Срез №2 — без вероятности"]["tasks_correct"] == 8


def test_srez_error_in_top_errors(seeded_session):
    dashboard = SqlAlchemyUnitOfWork(seeded_session).dashboard.get_dashboard(STUDENT)
    categories = {e["category"] for e in dashboard["top_errors"]}
    assert ErrorCategory.PROBABILITY_DOUBLE_COUNT in categories


def test_srez_seed_is_idempotent(seeded_session):
    def srez_counts() -> tuple[int, int]:
        logs = seeded_session.scalar(
            select(func.count(StudyLogEntryORM.id)).where(
                StudyLogEntryORM.source_ref.like("srez:%")
            )
        )
        errs = seeded_session.scalar(
            select(func.count(ErrorEventORM.id)).where(ErrorEventORM.source_ref.like("srez:%"))
        )
        return logs, errs

    assert srez_counts() == (2, 2)
    seed_module.seed()  # re-run (SessionLocal is monkeypatched by the fixture)
    assert srez_counts() == (2, 2)


def test_lifecycle_counts_solved_and_bank(seeded_session):
    mission = seeded_session.scalar(select(MissionORM).order_by(MissionORM.id))
    asyncio.run(
        service(seeded_session, StaticReviewer(draft(90))).submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "решение",
            }
        )
    )
    rows = {r["topic_id"]: r for r in service(seeded_session).list_topic_lifecycle(STUDENT)}
    row = rows[mission.topic_id]
    assert row["solved_count"] >= 1
    assert row["attempts_count"] >= 1

    expected_bank = seeded_session.scalar(
        select(func.count(TaskORM.id))
        .where(TaskORM.topic_id == mission.topic_id)
        .where(TaskORM.status == TaskStatus.APPROVED)
    )
    assert row["tasks_in_bank"] == expected_bank


def test_program_percent_present(seeded_session):
    phases = service(seeded_session).list_program_progress(STUDENT)
    june = next(p for p in phases if p["key"] == "june_diagnostics")
    assert 0 <= june["percent"] <= 100
    for topic in june["topics"]:
        if topic["tasks_in_bank"] == 0:
            assert topic["percent"] is None
        else:
            assert topic["percent"] == round(topic["solved_count"] / topic["tasks_in_bank"] * 100)
