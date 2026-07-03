"""Score-event rules (REQUIREMENTS §11): current_score follows the newest occurred_on."""

from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.adapters.api.dependencies import get_learning_service
from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService
from app.domain.enums import Subject
from app.infrastructure.models import SubjectTrackORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from app.main import create_app
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


def _event(score: int, occurred_on: date, kind: str = "exam_variant", note: str | None = None) -> dict:
    return {
        "student_id": STUDENT,
        "subject": Subject.MATH_PROFILE,
        "score": score,
        "kind": kind,
        "occurred_on": occurred_on,
        "note": note,
    }


def test_newer_score_event_updates_current_score(seeded_session):
    service(seeded_session).record_score_event(_event(72, date.today() + timedelta(days=1)))
    assert math_score(seeded_session) == 72


def test_older_backfilled_score_event_does_not_regress(seeded_session):
    service(seeded_session).record_score_event(_event(72, date.today() + timedelta(days=1)))
    service(seeded_session).record_score_event(_event(40, date.today() - timedelta(days=180)))
    assert math_score(seeded_session) == 72


def test_topic_check_score_event_does_not_move_current_score(seeded_session):
    service(seeded_session).record_score_event(_event(99, date.today() + timedelta(days=1), "topic_check"))
    assert math_score(seeded_session) == 65


def test_list_score_events_returns_newest_first(seeded_session):
    svc = service(seeded_session)
    older = date.today() - timedelta(days=30)
    newer = date.today() + timedelta(days=1)
    svc.record_score_event(_event(72, newer, note="July timed mock"))
    svc.record_score_event(_event(40, older, note="Old backfill"))

    events = svc.list_score_events(STUDENT)

    assert events[0]["score"] == 72
    assert events[0]["occurred_on"] == newer
    assert events[0]["note"] == "July timed mock"
    assert any(event["score"] == 40 and event["occurred_on"] == older for event in events)


def test_score_events_endpoint_returns_history():
    occurred_on = date.today() + timedelta(days=1)

    class ScoreHistoryService:
        def list_score_events(self, student_id, limit):
            assert student_id == STUDENT
            assert limit == 3
            return [
                {
                    "id": "00000000-0000-0000-0000-000000000074",
                    "student_id": STUDENT,
                    "subject": Subject.MATH_PROFILE,
                    "score": 74,
                    "kind": "exam_variant",
                    "occurred_on": occurred_on,
                    "note": "First mock",
                }
            ]

    app = create_app()
    app.dependency_overrides[get_learning_service] = lambda: ScoreHistoryService()
    client = TestClient(app)

    response = client.get(
        f"/api/students/{STUDENT}/score-events?limit=3",
        headers={"X-EGE-MENTOR-TOKEN": "change-this-family-token"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body[0]["score"] == 74
    assert body[0]["note"] == "First mock"
    assert body[0]["subject"] == "math_profile"


def test_weekly_digest_includes_score_spine(seeded_session):
    svc = service(seeded_session)
    svc.record_score_event(_event(74, date.today() + timedelta(days=1), note="First mock"))

    digest = svc.weekly_digest(STUDENT)

    assert digest["scores"]["recent"][0]["score"] == 74
    assert digest["scores"]["latest_by_subject"]["math_profile"]["current_score"] == 74
    assert digest["scores"]["latest_by_subject"]["math_profile"]["target_score"] == 85


def _diagnostic(session, occurred_on: date) -> None:
    SqlAlchemyUnitOfWork(session).dashboard.add_diagnostic(
        {
            "id": uuid4(),
            "student_id": STUDENT,
            "subject": Subject.MATH_PROFILE,
            "occurred_on": occurred_on,
            "topic_title": "Retention check",
            "tasks_total": 3,
            "tasks_correct": 2,
            "percent_correct": 2 / 3,
            "note": None,
            "details_json": [],
        }
    )
    session.commit()


def test_retention_warns_from_wednesday_below_three_active_days(seeded_session):
    svc = service(seeded_session)
    wednesday = date(2099, 7, 8)
    monday = date(2099, 7, 6)
    tuesday = date(2099, 7, 7)
    _diagnostic(seeded_session, monday)
    svc.record_score_event(_event(70, tuesday, "topic_check"))
    svc.record_score_event(_event(71, tuesday, "topic_check"))

    retention = svc._retention_summary(STUDENT, today=wednesday)

    assert retention["active_days"] == 2
    assert retention["target_active_days"] == 3
    assert retention["at_risk"] is True


def test_retention_does_not_warn_before_wednesday(seeded_session):
    svc = service(seeded_session)
    monday = date(2099, 7, 6)
    svc.record_score_event(_event(70, monday, "topic_check"))

    retention = svc._retention_summary(STUDENT, today=monday)

    assert retention["active_days"] == 1
    assert retention["at_risk"] is False


def test_retention_three_active_days_clear_risk_and_dashboard_exposes_block(seeded_session):
    svc = service(seeded_session)
    wednesday = date(2099, 7, 8)
    _diagnostic(seeded_session, date(2099, 7, 6))
    svc.record_score_event(_event(70, date(2099, 7, 7), "topic_check"))
    svc.record_score_event(_event(71, wednesday, "topic_check"))

    retention = svc._retention_summary(STUDENT, today=wednesday)
    dashboard = svc.get_dashboard(STUDENT)

    assert retention["active_days"] == 3
    assert retention["at_risk"] is False
    assert dashboard["retention"]["target_active_days"] == 3
    assert dashboard["retention"]["daily_task_target"] >= 1
