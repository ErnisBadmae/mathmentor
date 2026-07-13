"""L2a: manual mentor confirmation of an actionable category for an existing
answer-only error_event. The raw category is never changed by confirmation."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.use_cases import LearningService
from app.domain.enums import ErrorCategory, Subject
from app.infrastructure.models import ErrorEventORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts import seed as seed_module

STUDENT = seed_module.DEMO_STUDENT_ID


def service(session) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), reviewer=None)


def make_error(session, category: ErrorCategory = ErrorCategory.OTHER):
    event = ErrorEventORM(
        id=uuid4(),
        student_id=STUDENT,
        subject=Subject.MATH_PROFILE,
        category=category,
        detail="answer-only miss",
        created_at=datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    return event


def test_confirmation_stores_actionable_category(seeded_session):
    event = make_error(seeded_session)
    result = service(seeded_session).confirm_error_category(
        event.id, ErrorCategory.ARITHMETIC
    )
    assert result["confirmed_category"] == ErrorCategory.ARITHMETIC
    assert result["category_confirmed_at"] is not None
    assert result["category_confirmation_source"] == "manual"


def test_raw_category_unchanged_after_confirmation(seeded_session):
    event = make_error(seeded_session)
    service(seeded_session).confirm_error_category(event.id, ErrorCategory.ARITHMETIC)
    seeded_session.refresh(event)
    assert event.category == ErrorCategory.OTHER


def test_list_errors_returns_confirmation_fields(seeded_session):
    event = make_error(seeded_session)
    service(seeded_session).confirm_error_category(event.id, ErrorCategory.ODZ_LOGIC)
    rows = SqlAlchemyUnitOfWork(seeded_session).errors.list_errors(STUDENT)
    row = next(r for r in rows if r["id"] == event.id)
    assert row["confirmed_category"] == ErrorCategory.ODZ_LOGIC
    assert row["category_confirmed_at"] is not None
    assert row["category_confirmation_source"] == "manual"


def test_confirming_same_category_twice_is_idempotent(seeded_session):
    event = make_error(seeded_session)
    svc = service(seeded_session)
    first = svc.confirm_error_category(event.id, ErrorCategory.ARITHMETIC)
    second = svc.confirm_error_category(event.id, ErrorCategory.ARITHMETIC)
    assert first["category_confirmed_at"] == second["category_confirmed_at"]


def test_confirming_different_category_raises(seeded_session):
    event = make_error(seeded_session)
    svc = service(seeded_session)
    svc.confirm_error_category(event.id, ErrorCategory.ARITHMETIC)
    with pytest.raises(ValueError):
        svc.confirm_error_category(event.id, ErrorCategory.ODZ_LOGIC)


@pytest.mark.parametrize("category", [ErrorCategory.NONE, ErrorCategory.OTHER])
def test_confirming_none_or_other_raises_and_leaves_unconfirmed(seeded_session, category):
    event = make_error(seeded_session)
    svc = service(seeded_session)
    with pytest.raises(ValueError):
        svc.confirm_error_category(event.id, category)
    seeded_session.refresh(event)
    assert event.confirmed_category is None


def test_confirming_unknown_error_id_raises_lookup_error(seeded_session):
    with pytest.raises(LookupError):
        service(seeded_session).confirm_error_category(uuid4(), ErrorCategory.ARITHMETIC)
