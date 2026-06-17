"""Computed topic lifecycle (REQUIREMENTS §9) driven through the real flow.

States are reached the way they happen in production — submit_attempt + review
results — using topics/categories taken from the real "срезы знаний" corpus
(e.g. sign-transfer errors on logarithmic equations from Срез №4).
"""

import asyncio
from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import select

from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService
from app.domain.enums import (
    AiPolicy,
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    MissionStatus,
    ReviewStatus,
    Subject,
    TopicState,
)
from app.infrastructure.models import ErrorEventORM, MissionORM, ReviewItemORM, TopicORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts import seed as seed_module

STUDENT = seed_module.DEMO_STUDENT_ID
LOG_TOPIC = "Уравнения и неравенства с ОДЗ"
PERCENT_TOPIC = "Вероятность: теорема сложения"


class StaticReviewer:
    def __init__(self, draft: EvidenceDraft) -> None:
        self._draft = draft

    async def review_attempt(self, _attempt: AttemptForReview) -> EvidenceDraft:
        return self._draft


def draft(score: float, category: ErrorCategory = ErrorCategory.NONE) -> EvidenceDraft:
    return EvidenceDraft(
        score_percent=score,
        error_category=category,
        feedback="checked",
        next_action="next",
        model_id="test-model",
        prompt_version="test",
        rubric_version="test",
    )


def service(session, reviewer: object | None = None) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), reviewer or StaticReviewer(draft(0)))


def lifecycle_by_title(session) -> dict[str, dict]:
    rows = service(session).list_topic_lifecycle(STUDENT)
    return {row["topic_title"]: row for row in rows}


def mission_for_topic(session, title: str) -> MissionORM:
    topic = session.scalar(select(TopicORM).where(TopicORM.title == title))
    mission = session.scalar(select(MissionORM).where(MissionORM.topic_id == topic.id))
    assert mission is not None
    return mission


def submit(session, mission: MissionORM, reviewer_draft: EvidenceDraft) -> dict:
    return asyncio.run(
        service(session, StaticReviewer(reviewer_draft)).submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "attempt",
            }
        )
    )


def test_open_topic_from_imported_error_only(seeded_session):
    # Seed hangs an active mission on every seeded topic, so OPEN must be tested on a
    # topic that only has a historical error (mirrors importing the срез error journal).
    topic = TopicORM(
        id=uuid4(),
        subject=Subject.MATH_PROFILE,
        title="Импортированная тема из журнала",
        spec_year=2026,
        task_number=None,
    )
    seeded_session.add(topic)
    seeded_session.add(
        ErrorEventORM(
            id=uuid4(),
            student_id=STUDENT,
            subject=Subject.MATH_PROFILE,
            topic_id=topic.id,
            category=ErrorCategory.SIGN_TRANSFER,
            detail="знаковая ошибка при переносе",
            created_at=datetime.now(UTC),
        )
    )
    seeded_session.commit()

    row = lifecycle_by_title(seeded_session)[topic.title]
    assert row["state"] == TopicState.OPEN
    assert row["error_count"] == 1
    assert row["top_error_category"] == ErrorCategory.SIGN_TRANSFER


def test_seeded_topic_starts_in_work(seeded_session):
    row = lifecycle_by_title(seeded_session)[LOG_TOPIC]
    assert row["state"] == TopicState.IN_WORK


def test_failed_attempt_keeps_in_work_with_dominant_error(seeded_session):
    mission = mission_for_topic(seeded_session, LOG_TOPIC)
    submit(seeded_session, mission, draft(50, ErrorCategory.SIGN_TRANSFER))

    row = lifecycle_by_title(seeded_session)[LOG_TOPIC]
    assert row["state"] == TopicState.IN_WORK
    assert row["error_count"] == 1
    assert row["top_error_category"] == ErrorCategory.SIGN_TRANSFER


def test_passed_attempt_moves_to_under_review(seeded_session):
    mission = mission_for_topic(seeded_session, LOG_TOPIC)
    submit(seeded_session, mission, draft(90))

    row = lifecycle_by_title(seeded_session)[LOG_TOPIC]
    assert row["state"] == TopicState.UNDER_REVIEW
    assert row["passed"] is True
    assert row["active_missions"] == 0
    assert row["reviews_due"] == 2


def test_confirmed_only_after_both_reviews_done(seeded_session):
    mission = mission_for_topic(seeded_session, LOG_TOPIC)
    result = submit(seeded_session, mission, draft(90))
    reviews = seeded_session.scalars(
        select(ReviewItemORM).where(ReviewItemORM.source_evidence_id == result["evidence_id"])
    ).all()
    assert len(reviews) == 2

    # one card done → still under review, not confirmed
    service(seeded_session).record_review_result(reviews[0].id, passed=True)
    row = lifecycle_by_title(seeded_session)[LOG_TOPIC]
    assert row["state"] == TopicState.UNDER_REVIEW

    service(seeded_session).record_review_result(reviews[1].id, passed=True)
    row = lifecycle_by_title(seeded_session)[LOG_TOPIC]
    assert row["state"] == TopicState.CONFIRMED
    assert row["reviews_done"] == 2
    assert row["reviews_due"] == 0


def test_failed_review_sends_topic_back_to_work(seeded_session):
    mission = mission_for_topic(seeded_session, LOG_TOPIC)
    result = submit(seeded_session, mission, draft(90))
    reviews = seeded_session.scalars(
        select(ReviewItemORM).where(ReviewItemORM.source_evidence_id == result["evidence_id"])
    ).all()

    service(seeded_session).record_review_result(reviews[0].id, passed=False)

    row = lifecycle_by_title(seeded_session)[LOG_TOPIC]
    assert row["state"] == TopicState.BACK_TO_WORK
    assert row["back_to_work_reviews"] == 1


def test_top_error_category_tie_break_is_deterministic(seeded_session):
    topic = TopicORM(
        id=uuid4(),
        subject=Subject.MATH_PROFILE,
        title="Тема с равными категориями",
        spec_year=2026,
        task_number=None,
    )
    seeded_session.add(topic)
    for category in (ErrorCategory.ODZ_LOGIC, ErrorCategory.ARITHMETIC):
        seeded_session.add(
            ErrorEventORM(
                id=uuid4(),
                student_id=STUDENT,
                subject=Subject.MATH_PROFILE,
                topic_id=topic.id,
                category=category,
                detail="x",
                created_at=datetime.now(UTC),
            )
        )
    seeded_session.commit()

    row = lifecycle_by_title(seeded_session)[topic.title]
    # equal counts → category asc wins ("arithmetic" < "odz_logic")
    assert row["top_error_category"] == ErrorCategory.ARITHMETIC


def _active_missions_for_topic(session, topic_id) -> list[MissionORM]:
    return list(
        session.scalars(
            select(MissionORM)
            .where(MissionORM.topic_id == topic_id)
            .where(MissionORM.status == MissionStatus.ACTIVE)
        ).all()
    )


def test_failed_review_opens_new_active_mission_for_topic(seeded_session):
    mission = mission_for_topic(seeded_session, LOG_TOPIC)
    topic_id = mission.topic_id
    result = submit(seeded_session, mission, draft(90))
    # the original mission is DONE → no active missions for the topic yet
    assert _active_missions_for_topic(seeded_session, topic_id) == []
    review = seeded_session.scalars(
        select(ReviewItemORM).where(ReviewItemORM.source_evidence_id == result["evidence_id"])
    ).first()

    service(seeded_session).record_review_result(review.id, passed=False)

    actives = _active_missions_for_topic(seeded_session, topic_id)
    assert len(actives) == 1
    new_mission = actives[0]
    assert new_mission.id != mission.id  # history preserved, DONE mission not reopened
    assert new_mission.title == f"Повтор: {LOG_TOPIC}"
    assert new_mission.status == MissionStatus.ACTIVE
    assert new_mission.ai_policy == AiPolicy.ATTEMPT_FIRST
    assert new_mission.threshold_percent == 80.0
    assert new_mission.due_date is not None
    # original mission stays DONE
    assert seeded_session.get(MissionORM, mission.id).status == MissionStatus.DONE


def test_passed_review_creates_no_new_mission(seeded_session):
    mission = mission_for_topic(seeded_session, LOG_TOPIC)
    topic_id = mission.topic_id
    result = submit(seeded_session, mission, draft(90))
    review = seeded_session.scalars(
        select(ReviewItemORM).where(ReviewItemORM.source_evidence_id == result["evidence_id"])
    ).first()

    service(seeded_session).record_review_result(review.id, passed=True)

    assert _active_missions_for_topic(seeded_session, topic_id) == []


def test_failed_imported_review_without_prior_mission_uses_defaults(seeded_session):
    # Imported review card for a topic that never had a mission (tracker import case).
    topic = TopicORM(
        id=uuid4(),
        subject=Subject.INFORMATICS,
        title="Импортированная тема без миссий",
        spec_year=2026,
        task_number=None,
    )
    seeded_session.add(topic)
    review = ReviewItemORM(
        id=uuid4(),
        student_id=STUDENT,
        topic_id=topic.id,
        due_date=date(2026, 6, 1),
        status=ReviewStatus.DUE,
        source_ref="import:review:1",
    )
    seeded_session.add(review)
    seeded_session.commit()

    service(seeded_session).record_review_result(review.id, passed=False)

    actives = _active_missions_for_topic(seeded_session, topic.id)
    assert len(actives) == 1
    new_mission = actives[0]
    assert new_mission.title == "Повтор: Импортированная тема без миссий"
    assert new_mission.subject == Subject.INFORMATICS
    assert new_mission.ai_policy == AiPolicy.ATTEMPT_FIRST
    assert new_mission.threshold_percent == 80.0


def test_srez_like_scenario_surfaces_weak_topics(seeded_session):
    # Mirrors Срез №4: logs topic fails on sign transfer, percent topic is confirmed.
    log_mission = mission_for_topic(seeded_session, LOG_TOPIC)
    submit(seeded_session, log_mission, draft(50, ErrorCategory.SIGN_TRANSFER))

    pct_mission = mission_for_topic(seeded_session, PERCENT_TOPIC)
    result = submit(seeded_session, pct_mission, draft(90))
    for review in seeded_session.scalars(
        select(ReviewItemORM).where(ReviewItemORM.source_evidence_id == result["evidence_id"])
    ).all():
        service(seeded_session).record_review_result(review.id, passed=True)

    rows = lifecycle_by_title(seeded_session)
    assert rows[LOG_TOPIC]["state"] == TopicState.IN_WORK
    assert rows[LOG_TOPIC]["top_error_category"] == ErrorCategory.SIGN_TRANSFER
    assert rows[PERCENT_TOPIC]["state"] == TopicState.CONFIRMED
    assert rows[PERCENT_TOPIC]["error_count"] == 0
