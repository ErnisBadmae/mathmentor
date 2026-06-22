import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.adapters.api.dependencies import get_learning_service
from app.adapters.api.schemas import MissionOut
from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService, RuleBasedReviewer
from app.domain.enums import (
    AiPolicy,
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    MissionStatus,
    Subject,
    TaskStatus,
)
from app.infrastructure.db import Base
from app.infrastructure.importers import tracker_importer
from app.infrastructure.importers.xlsx_reader import SheetPreview
from app.infrastructure.models import (
    ErrorEventORM,
    EvidenceORM,
    MissionORM,
    ReviewItemORM,
    SubjectTrackORM,
    TaskORM,
)
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


class CapturingReviewer:
    def __init__(self, draft: EvidenceDraft) -> None:
        self._draft = draft
        self.attempts: list[AttemptForReview] = []

    async def review_attempt(self, attempt: AttemptForReview) -> EvidenceDraft:
        self.attempts.append(attempt)
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
    dashboard = SqlAlchemyUnitOfWork(seeded_session).dashboard.get_dashboard(
        seed_module.DEMO_STUDENT_ID
    )

    tracks = {track["subject"]: track for track in dashboard["tracks"]}
    assert tracks[Subject.MATH_PROFILE]["current_score"] == 65
    assert tracks[Subject.INFORMATICS]["current_score"] == 50
    assert dashboard["clean_sheet_ratio"] == 0.4


def test_seed_creates_approved_task_bank_and_links_starter_mission(
    seeded_session, session_factory, monkeypatch
):
    tasks = seeded_session.scalars(
        select(TaskORM).where(TaskORM.status == TaskStatus.APPROVED)
    ).all()
    assert len(tasks) >= 24
    before = len(tasks)

    monkeypatch.setattr(seed_module, "SessionLocal", session_factory)
    seed_module.seed()
    session = session_factory()
    try:
        after = session.scalars(select(TaskORM).where(TaskORM.status == TaskStatus.APPROVED)).all()
        assert len(after) == before
        mission = session.scalar(
            select(MissionORM).where(MissionORM.title == "Решить уравнение с учётом ОДЗ")
        )
        assert mission is not None
        assert mission.task_id is not None
        task = session.get(TaskORM, mission.task_id)
        assert task is not None
        assert "log₃(2x" in task.statement
    finally:
        session.close()


def test_seed_today_missions_all_have_statements_and_no_probability_duplicate(seeded_session):
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))

    missions = service.list_today(seed_module.DEMO_STUDENT_ID)
    titles = [mission["title"] for mission in missions]

    assert all(mission["statement"] for mission in missions)
    assert "Задача на проценты" not in titles
    assert titles.count("Вероятность: совместные события") == 1


def test_seed_adds_active_inequality_missions(seeded_session):
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))

    missions = service.list_today(seed_module.DEMO_STUDENT_ID)
    by_title = {mission["title"]: mission for mission in missions}

    expected = {
        "Неравенство: квадратное": "x² − x − 6 ≤ 0",
        "Неравенство: показательное": "(1/2)^x < 1/8",
        "Неравенство: логарифмическое": "log₂(x − 1) < 3",
        "Неравенство: рациональное": "(x − 1)/(x + 2) ≥ 0",
    }
    for title, statement_part in expected.items():
        assert title in by_title
        assert statement_part in by_title[title]["statement"]


def test_seed_adds_active_informatics_foundation_missions(seeded_session):
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))

    missions = service.list_today(seed_module.DEMO_STUDENT_ID)
    by_title = {mission["title"]: mission for mission in missions}

    expected_titles = [
        "Python: Thonny и ввод-вывод",
        "Логика: таблица истинности",
        "Python: арифметика и типы",
        "Python: условия",
        "Python: for и range",
        "Кодирование: объём файла",
        "Комбинаторика: подсчёт слов",
    ]
    for title in expected_titles:
        assert title in by_title
        assert by_title[title]["subject"] == Subject.INFORMATICS
        assert by_title[title]["statement"]


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
    reviews = seeded_session.scalars(
        select(ReviewItemORM).where(ReviewItemORM.source_evidence_id == result["evidence_id"])
    ).all()
    assert len(reviews) == 2
    track = seeded_session.scalar(
        select(SubjectTrackORM).where(SubjectTrackORM.subject == mission.subject)
    )
    assert track.current_score == 65


def test_today_mission_response_contains_statement_without_answer_key(seeded_session):
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))
    payload = service.list_today(seed_module.DEMO_STUDENT_ID)
    task_linked = next(item for item in payload if "log₃(2x" in item["statement"])
    assert "log₃(2x" in task_linked["statement"]
    public_payload = MissionOut.model_validate(task_linked).model_dump(mode="json")
    assert "expected_answer" not in public_payload
    assert "solution" not in public_payload


def test_submit_attempt_uses_task_expected_answer(seeded_session):
    mission = first_mission(seeded_session)
    reviewer = CapturingReviewer(draft(90))
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), reviewer)

    asyncio.run(
        service.submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "x=5",
            }
        )
    )

    assert reviewer.attempts
    assert reviewer.attempts[0].expected_answer == "5"
    assert reviewer.attempts[0].instructions is not None
    assert "log₃(2x" in reviewer.attempts[0].instructions


def test_create_mission_with_approved_task_returns_statement(seeded_session):
    task = seeded_session.scalar(
        select(TaskORM).where(TaskORM.status == TaskStatus.APPROVED).order_by(TaskORM.id)
    )
    assert task is not None
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))

    result = service.create_mission(
        {
            "student_id": seed_module.DEMO_STUDENT_ID,
            "subject": task.subject,
            "title": "Extra approved task mission",
            "instructions": "Solve independently.",
            "status": MissionStatus.ACTIVE,
            "ai_policy": AiPolicy.ATTEMPT_FIRST,
            "task_id": task.id,
        }
    )

    assert result["statement"] == task.statement
    assert result["id"] is not None


def test_mission_cannot_reference_draft_task(seeded_session):
    topic_id = first_mission(seeded_session).topic_id
    draft_task = TaskORM(
        id=uuid4(),
        subject=Subject.MATH_PROFILE,
        topic_id=topic_id,
        task_number="draft",
        statement="Draft task",
        expected_answer="1",
        solution=None,
        error_category=None,
        status=TaskStatus.DRAFT,
        source="test",
        source_ref="test:draft-task",
        created_at=seed_module.datetime.now(seed_module.UTC),
    )
    seeded_session.add(draft_task)
    seeded_session.commit()

    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))

    with pytest.raises(ValueError, match="approved"):
        service.create_mission(
            {
                "student_id": seed_module.DEMO_STUDENT_ID,
                "subject": Subject.MATH_PROFILE,
                "title": "Draft linked mission",
                "instructions": "Should fail",
                "task_id": draft_task.id,
            }
        )


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
    assert (
        seeded_session.scalar(
            select(ErrorEventORM).where(ErrorEventORM.evidence_id == result["evidence_id"])
        )
        is not None
    )


def test_daily_set_counts_override_score_and_pass_at_eight_of_ten(seeded_session):
    mission = first_mission(seeded_session)
    service = LearningService(
        SqlAlchemyUnitOfWork(seeded_session),
        StaticReviewer(draft(5, ErrorCategory.ARITHMETIC)),
    )

    result = asyncio.run(
        service.submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "set result",
                "tasks_total": 10,
                "tasks_correct": 8,
            }
        )
    )

    evidence = seeded_session.get(EvidenceORM, result["evidence_id"])
    assert result["status"] == EvidenceStatus.PASSED
    assert result["score_percent"] == 80.0
    assert result["tasks_total"] == 10
    assert result["tasks_correct"] == 8
    assert evidence is not None
    assert evidence.tasks_total == 10
    assert evidence.tasks_correct == 8
    assert seeded_session.get(MissionORM, mission.id).status == MissionStatus.DONE


def test_daily_set_counts_fail_below_threshold_and_mark_repeat(seeded_session):
    mission = first_mission(seeded_session)
    service = LearningService(
        SqlAlchemyUnitOfWork(seeded_session),
        StaticReviewer(draft(95, ErrorCategory.NONE)),
    )

    result = asyncio.run(
        service.submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "set result",
                "tasks_total": 10,
                "tasks_correct": 7,
            }
        )
    )

    assert result["status"] == EvidenceStatus.FAILED
    assert result["score_percent"] == 70.0
    assert seeded_session.get(MissionORM, mission.id).status == MissionStatus.REPEAT


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

    dashboard = SqlAlchemyUnitOfWork(seeded_session).dashboard.get_dashboard(
        seed_module.DEMO_STUDENT_ID
    )
    assert dashboard["clean_sheet_ratio"] < 0.4


def test_single_task_attempt_still_uses_reviewer_score_without_counts(seeded_session):
    mission = first_mission(seeded_session)
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))

    result = asyncio.run(
        service.submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "single task",
            }
        )
    )

    evidence = seeded_session.get(EvidenceORM, result["evidence_id"])
    assert result["status"] == EvidenceStatus.PASSED
    assert result["score_percent"] == 90.0
    assert result["tasks_total"] is None
    assert result["tasks_correct"] is None
    assert evidence is not None
    assert evidence.tasks_total is None
    assert evidence.tasks_correct is None


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
        headers={"X-EGE-MENTOR-TOKEN": "change-this-family-token"},
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
        SheetPreview(
            "Дневной лог", [["46181", "матем", "срез", "11", "10", "0.91", "закрыта", "note"]]
        ),
        SheetPreview(
            "Журнал ошибок",
            [["46181", "Профматематика", "Вероятность", "ошибка в алгоритме", "двойной счет"]],
        ),
        SheetPreview("Чистый лист", [["03.06", "5", "2", "0.4", "baseline"]]),
        SheetPreview(
            "Повторение", [["Логарифмы", "Математика", "46183", "46190", "зачёт", "46213", ""]]
        ),
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


def test_topic_check_score_event_does_not_move_current_score(seeded_session):
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(0)))
    service.record_score_event(
        {
            "student_id": seed_module.DEMO_STUDENT_ID,
            "subject": Subject.MATH_PROFILE,
            "score": 40,
            "kind": "topic_check",
        }
    )
    track = seeded_session.scalar(
        select(SubjectTrackORM).where(SubjectTrackORM.subject == Subject.MATH_PROFILE)
    )
    assert track.current_score == 65


def test_exam_like_score_event_moves_current_score(seeded_session):
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(0)))
    service.record_score_event(
        {
            "student_id": seed_module.DEMO_STUDENT_ID,
            "subject": Subject.MATH_PROFILE,
            "score": 78,
            "kind": "exam_like_slice",
        }
    )
    track = seeded_session.scalar(
        select(SubjectTrackORM).where(SubjectTrackORM.subject == Subject.MATH_PROFILE)
    )
    assert track.current_score == 78


def test_manual_decision_with_counts_scores_from_counts_over_button(seeded_session):
    mission = first_mission(seeded_session)
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(0)))
    submitted = asyncio.run(
        service.submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "x",
            }
        )
    )
    # Operator presses "passed" but records 5/10 -> objective counts win -> FAILED at 50%.
    result = service.apply_manual_decision(
        submitted["evidence_id"],
        {"status": EvidenceStatus.PASSED, "tasks_total": 10, "tasks_correct": 5},
    )
    assert result["status"] == EvidenceStatus.FAILED
    assert result["score_percent"] == 50.0
    assert result["tasks_total"] == 10
    assert result["tasks_correct"] == 5


def test_submit_with_only_one_count_raises_value_error(seeded_session):
    mission = first_mission(seeded_session)
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))
    with pytest.raises(ValueError):
        asyncio.run(
            service.submit_attempt(
                {
                    "mission_id": mission.id,
                    "kind": AttemptKind.TEXT,
                    "mode": AttemptMode.CLEAN_SHEET,
                    "answer_text": "x",
                    "tasks_total": 10,
                }
            )
        )


def test_submit_with_correct_exceeding_total_raises_value_error(seeded_session):
    mission = first_mission(seeded_session)
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))
    with pytest.raises(ValueError):
        asyncio.run(
            service.submit_attempt(
                {
                    "mission_id": mission.id,
                    "kind": AttemptKind.TEXT,
                    "mode": AttemptMode.CLEAN_SHEET,
                    "answer_text": "x",
                    "tasks_total": 10,
                    "tasks_correct": 11,
                }
            )
        )


def test_value_error_is_mapped_to_400():
    app = create_app()

    class RaisingService:
        async def submit_attempt(self, _values):
            raise ValueError("tasks_correct cannot exceed tasks_total")

    app.dependency_overrides[get_learning_service] = lambda: RaisingService()
    client = TestClient(app)

    response = client.post(
        "/api/attempts",
        headers={"X-EGE-MENTOR-TOKEN": "change-this-family-token"},
        json={
            "mission_id": "00000000-0000-0000-0000-000000000123",
            "kind": "text",
            "mode": "clean_sheet",
            "answer_text": "x",
        },
    )

    assert response.status_code == 400


def test_publish_feedback_appears_in_dashboard_feed(seeded_session):
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))
    service.publish_feedback(
        {"student_id": seed_module.DEMO_STUDENT_ID, "body": "Хорошая работа, продолжай."}
    )
    dashboard = service.get_dashboard(seed_module.DEMO_STUDENT_ID)
    bodies = [note["body"] for note in dashboard["mentor_notes"]]
    assert "Хорошая работа, продолжай." in bodies


def test_answer_is_correct_normalizes_short_answers():
    from app.domain.policies import answer_is_correct

    assert answer_is_correct("3,5", "3.5")
    assert answer_is_correct(" -3 ", "-3")
    assert answer_is_correct("5", "5 ")
    assert not answer_is_correct("4", "5")
    assert not answer_is_correct(None, "5")
    assert not answer_is_correct("5", "")


def test_draw_slice_returns_approved_tasks_without_answer_key(seeded_session):
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))
    items = service.draw_slice(Subject.MATH_PROFILE, 5)
    assert 1 <= len(items) <= 5
    for item in items:
        assert item["statement"]
        assert item["task_id"] is not None
        assert "expected_answer" not in item


def test_grade_slice_records_diagnostic_and_errors_without_moving_score(seeded_session):
    uow = SqlAlchemyUnitOfWork(seeded_session)
    service = LearningService(uow, StaticReviewer(draft(90)))
    pool = uow.tasks.list_gradable(Subject.MATH_PROFILE)
    assert len(pool) >= 3
    items = [{"task_id": task.id, "answer_text": task.expected_answer} for task in pool]
    # Make exactly two answers wrong.
    items[0]["answer_text"] = "___wrong___"
    items[1]["answer_text"] = "___wrong___"
    expected_correct = len(pool) - 2
    before = seeded_session.scalar(
        select(SubjectTrackORM).where(SubjectTrackORM.subject == Subject.MATH_PROFILE)
    ).current_score

    result = service.grade_slice(seed_module.DEMO_STUDENT_ID, Subject.MATH_PROFILE, items)

    assert result["tasks_total"] == len(pool)
    assert result["tasks_correct"] == expected_correct
    assert result["percent"] == round(expected_correct / len(pool) * 100)
    assert result["passed"] == (expected_correct / len(pool) >= 0.8)
    # Diagnostic is surfaced on the dashboard "Диагностика (срезы)" feed.
    diagnostics = uow.dashboard.list_diagnostics(seed_module.DEMO_STUDENT_ID)
    assert any(
        d["tasks_total"] == len(pool) and d["tasks_correct"] == expected_correct
        for d in diagnostics
    )
    # The two misses land in the error journal.
    errors = uow.errors.list_errors(seed_module.DEMO_STUDENT_ID, subject=Subject.MATH_PROFILE)
    assert len(errors) >= 2
    # §11: a diagnostic slice must not move current_score.
    after = seeded_session.scalar(
        select(SubjectTrackORM).where(SubjectTrackORM.subject == Subject.MATH_PROFILE)
    ).current_score
    assert after == before


def test_grade_slice_rejects_unapproved_task(seeded_session):
    service = LearningService(SqlAlchemyUnitOfWork(seeded_session), StaticReviewer(draft(90)))
    draft_task = service.add_task(
        {"subject": Subject.MATH_PROFILE, "statement": "2+2?", "expected_answer": "4"}
    )
    with pytest.raises(ValueError):
        service.grade_slice(
            seed_module.DEMO_STUDENT_ID,
            Subject.MATH_PROFILE,
            [{"task_id": draft_task.id, "answer_text": "4"}],
        )
