"""Controller program-progress view (Step 4): topics × lifecycle, grouped by phase."""

import asyncio
from datetime import date
from uuid import uuid4

from sqlalchemy import select

from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService
from app.domain.enums import AiPolicy, AttemptKind, AttemptMode, ErrorCategory, MissionStatus, Subject, TopicState
from app.domain.program import PHASES, current_phase_key
from app.infrastructure.models import MissionORM, ReviewItemORM, TopicORM
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
        model_id="m",
        prompt_version="p",
        rubric_version="r",
    )


def service(session, reviewer: object | None = None) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), reviewer or StaticReviewer(draft(0)))


def test_current_phase_key_is_date_windowed():
    assert current_phase_key(date(2026, 6, 15)) == "june_diagnostics"
    assert current_phase_key(date(2026, 7, 20)) == "july_aug_foundation"
    assert current_phase_key(date(2026, 8, 20)) == "rest_august"
    assert current_phase_key(date(2025, 1, 1)) is None


def test_program_topics_seeded_with_phase(seeded_session):
    topics = seeded_session.scalars(select(TopicORM).where(TopicORM.phase.is_not(None))).all()
    assert topics
    by_title = {t.title: t for t in topics}
    assert by_title["Уравнения и неравенства с ОДЗ"].phase == "june_diagnostics"
    assert by_title["Векторы"].phase == "june_diagnostics"
    assert by_title["Параметр (№18): графический метод"].phase == "july_aug_foundation"


def test_program_progress_grouped_in_phase_order(seeded_session):
    phases = service(seeded_session).list_program_progress(STUDENT)

    assert [p["key"] for p in phases] == [ph.key for ph in PHASES]
    june = next(p for p in phases if p["key"] == "june_diagnostics")
    cov = june["coverage"]
    assert cov["total"] == len(june["topics"]) > 0
    # coverage buckets partition the phase's topics
    assert cov["confirmed"] + cov["in_progress"] + cov["open"] == cov["total"]
    # at most one phase is the current one
    assert sum(1 for p in phases if p["is_current"]) <= 1


def test_passed_program_topic_becomes_confirmed(seeded_session):
    topic = seeded_session.scalar(select(TopicORM).where(TopicORM.title == "Векторы"))
    mission = MissionORM(
        id=uuid4(),
        student_id=STUDENT,
        subject=Subject.MATH_PROFILE,
        topic_id=topic.id,
        title="Векторы — практика",
        instructions="Реши задачу на векторы.",
        status=MissionStatus.ACTIVE,
        ai_policy=AiPolicy.ATTEMPT_FIRST,
        threshold_percent=80.0,
        due_date=date.today(),
    )
    seeded_session.add(mission)
    seeded_session.commit()

    result = asyncio.run(
        service(seeded_session, StaticReviewer(draft(90))).submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "решение",
            }
        )
    )
    for review in seeded_session.scalars(
        select(ReviewItemORM).where(ReviewItemORM.source_evidence_id == result["evidence_id"])
    ).all():
        service(seeded_session).record_review_result(review.id, passed=True)

    june = next(
        p for p in service(seeded_session).list_program_progress(STUDENT) if p["key"] == "june_diagnostics"
    )
    states = {t["topic_title"]: t["state"] for t in june["topics"]}
    assert states["Векторы"] == TopicState.CONFIRMED
    assert june["coverage"]["confirmed"] >= 1
