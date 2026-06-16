import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.adapters.api.dependencies import get_learning_service
from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService, RuleBasedReviewer
from app.domain.enums import AttemptKind, AttemptMode, ErrorCategory, EvidenceStatus, MissionStatus, Subject
from app.infrastructure.db import Base
from app.infrastructure.importers.xlsx_reader import SheetPreview
from app.infrastructure.importers import tracker_importer
from app.infrastructure.models import ErrorEventORM, MissionORM, ReviewItemORM, SubjectTrackORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from app.main import create_app
from scripts import seed as seed_module


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def seeded_session(session_factory, monkeypatch):
    monkeypatch.setattr(seed_module, "SessionLocal", session_factory)
    seed_module.seed()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


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


def first_mission(session, subject: Subject | None = None) -> MissionORM:
    stmt = select(MissionORM).order_by(MissionORM.id)
    if subject is not None:
        stmt = stmt.where(MissionORM.subject == subject)
    mission = session.scalar(stmt)
    assert mission is not None
    return mission


def test_seed_creates_known_dashboard_baseline(seeded_session):
    dashboard = SqlAlchemyUnitOfWork(seeded_session).dashboard.get_dashboard(seed_module.DEMO_STUDENT_ID)

    tracks = {track["subject"]: track for track in dashboard["tracks"]}
    assert tracks[Subject.MATH_PROFILE]["current_score"] == 65
    assert tracks[Subject.INFORMATICS]["current_score"] == 50
    assert dashboard["clean_sheet_ratio"] == 0.4


def test_passed_attempt_closes_mission_and_schedules_reviews_without_score_change(seeded_session):
    mission = first_mission(seeded_session)
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))

    result = asyncio.run(
        service.submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "solution",
            }
        )
    )

    assert result["status"] == EvidenceStatus.PASSED
    assert seeded_session.get(MissionORM, mission.id).status == MissionStatus.DONE
    reviews = seeded_session.scalars(select(ReviewItemORM).where(ReviewItemORM.source_evidence_id == result["evidence_id"])).all()
    assert len(reviews) == 2
    track = seeded_session.scalar(select(SubjectTrackORM).where(SubjectTrackORM.subject == mission.subject))
    assert track.current_score == 65


def test_failed_attempt_marks_repeat_and_records_error(seeded_session):
    mission = first_mission(seeded_session)
    service = LearningService(
        SqlAlchemyUnitOfWork(seeded_session),
        StaticReviewer(draft(50, ErrorCategory.ARITHMETIC)),
    )

    result = asyncio.run(
        service.submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "wrong",
            }
        )
    )

    assert result["status"] == EvidenceStatus.FAILED
    assert seeded_session.get(MissionORM, mission.id).status == MissionStatus.REPEAT
    assert seeded_session.scalar(select(ErrorEventORM).where(ErrorEventORM.evidence_id == result["evidence_id"])) is not None


def test_hinted_code_attempt_does_not_improve_clean_sheet_ratio(seeded_session):
    mission = first_mission(seeded_session, Subject.INFORMATICS)
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))

    asyncio.run(
        service.submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.CODE,
                "mode": AttemptMode.WITH_HINT,
                "answer_text": "print(1)",
                "code_text": "print(1)",
            }
        )
    )

    dashboard = SqlAlchemyUnitOfWork(seeded_session).dashboard.get_dashboard(seed_module.DEMO_STUDENT_ID)
    assert dashboard["clean_sheet_ratio"] < 0.4


def test_rule_based_reviewer_defaults_to_manual_review_for_non_empty_attempt():
    result = asyncio.run(
        RuleBasedReviewer().review_attempt(
            AttemptForReview(
                subject=Subject.MATH_PROFILE,
                mission_title="test",
                topic_title=None,
                kind=AttemptKind.TEXT,
                mode=AttemptMode.CLEAN_SHEET,
                answer_text="some solution",
                code_text=None,
                expected_answer=None,
                threshold_percent=80,
            )
        )
    )

    assert result.status == EvidenceStatus.NEEDS_MANUAL_REVIEW


def test_lookup_error_is_mapped_to_404():
    app = create_app()

    class MissingMissionService:
        async def submit_attempt(self, _values):
            raise LookupError("Mission not found")

    app.dependency_overrides[get_learning_service] = lambda: MissingMissionService()
    client = TestClient(app)

    response = client.post(
        "/api/attempts",
        json={
            "mission_id": "00000000-0000-0000-0000-000000000123",
            "kind": "text",
            "mode": "clean_sheet",
            "answer_text": "x",
        },
    )

    assert response.status_code == 404


def test_tracker_importer_is_idempotent(seeded_session, monkeypatch):
    sheets = [
        SheetPreview(
            "Дашборд",
            [
                ["Профматематика", "65", "65", "85"],
                ["Информатика", "50", "50", "85"],
                ["Под-трек программирования (опережающий индикатор по информатике)"],
            ],
        ),
        SheetPreview("Дневной лог", [["46181", "матем", "срез", "11", "10", "0.91", "закрыта", "note"]]),
        SheetPreview("Журнал ошибок", [["46181", "Профматематика", "Вероятность", "ошибка в алгоритме", "двойной счет"]]),
        SheetPreview("Чистый лист", [["03.06", "5", "2", "0.4", "baseline"]]),
        SheetPreview("Повторение", [["Логарифмы", "Математика", "46183", "46190", "зачёт", "46213", ""]]),
        SheetPreview("Варианты", [["Неделя 1", "46190", "66", "51", "просело", "вывод"]]),
    ]
    monkeypatch.setattr(tracker_importer, "read_xlsx", lambda _path: sheets)

    first = tracker_importer.import_tracker(seeded_session, Path("tracker.xlsx"))
    second = tracker_importer.import_tracker(seeded_session, Path("tracker.xlsx"))

    assert first.study_log_entries == 1
    assert first.error_events == 1
    assert first.clean_sheet_events == 1
    assert first.review_items == 2
    assert first.score_events == 2
    info_track = seeded_session.scalar(
        select(SubjectTrackORM).where(SubjectTrackORM.subject == Subject.INFORMATICS)
    )
    assert info_track.current_score == 51
    assert second.study_log_entries == 0
    assert second.error_events == 0
    assert second.clean_sheet_events == 0
    assert second.review_items == 0
    assert second.score_events == 0
