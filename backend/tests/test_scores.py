"""Score-event rules (REQUIREMENTS §11): current_score follows the newest occurred_on."""

from datetime import date

from sqlalchemy import select

from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService
from app.domain.enums import Subject
from app.infrastructure.models import SubjectTrackORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts import seed as seed_module

STUDENT = seed_module.DEMO_STUDENT_ID


class _NoReviewer:
    async def review_attempt(self, _attempt: AttemptForReview) -> EvidenceDraft:  # pragma: no cover
        raise AssertionError("reviewer not used in score tests")


def service(session) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), _NoReviewer())


def math_score(session) -> int:
    track = session.scalar(
        select(SubjectTrackORM).where(SubjectTrackORM.subject == Subject.MATH_PROFILE)
    )
    return track.current_score


def _event(score: int, occurred_on: date) -> dict:
    return {
        "student_id": STUDENT,
        "subject": Subject.MATH_PROFILE,
        "score": score,
        "kind": "exam_variant",
        "occurred_on": occurred_on,
    }


def test_newer_score_event_updates_current_score(seeded_session):
    service(seeded_session).record_score_event(_event(72, date(2026, 7, 1)))
    assert math_score(seeded_session) == 72


def test_older_backfilled_score_event_does_not_regress(seeded_session):
    service(seeded_session).record_score_event(_event(72, date(2026, 7, 1)))
    service(seeded_session).record_score_event(_event(40, date(2026, 1, 1)))
    assert math_score(seeded_session) == 72
