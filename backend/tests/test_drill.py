"""Часть-1 дрилл: мгновенная точная проверка ответа без LLM (Telegram-флоу).

Дрилл-миссия помечена ``source_ref="daily:"`` и связана с одобренной exact-answer задачей.
Верный ответ закрывает миссию и планирует повторы +7/+30; неверный — пишет ошибку с
категорией задачи и помечает миссию на повтор. Ревьюер (LLM) при этом не вызывается.
"""

import asyncio
import importlib.util
from datetime import date
from uuid import UUID

import pytest
from sqlalchemy import select

from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService, VisualAid
from app.domain.figures import NEG, POS, parse_interval_answer_from_text
from app.domain.enums import (
    AiPolicy,
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    MissionStatus,
    Subject,
)
from app.infrastructure.models import ErrorEventORM, MissionORM, ReviewItemORM, TopicORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts import seed as seed_module

STUDENT = seed_module.DEMO_STUDENT_ID
VECTORS = "Векторы"


class BoomReviewer:
    """Проваливает тест, если дрилл всё-таки уходит в LLM-ревьюер."""

    async def review_attempt(self, _attempt: AttemptForReview) -> EvidenceDraft:
        raise AssertionError("LLM reviewer must not be called for a daily drill")


def service(session, reviewer: object | None = None) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), reviewer or BoomReviewer())


def _approved_task(svc: LearningService, session, answer: str, category: ErrorCategory | None):
    topic = session.scalar(select(TopicORM).where(TopicORM.title == VECTORS))
    url = f"https://example.org/drill/{answer}/{category}"
    task = svc.add_task(
        {
            "subject": Subject.MATH_PROFILE,
            "statement": "Найдите длину вектора (3; 4).",
            "expected_answer": answer,
            "source": "official",
            "source_url": url,
            "source_ref": url,
            "topic_id": topic.id,
            "error_category": category,
        }
    )
    svc.approve_task(task.id)
    if task.topic_id is not None:
        topic = session.get(TopicORM, task.topic_id)
    return task, topic


def _approved_task_with_source_ref(
    svc: LearningService,
    session,
    *,
    statement: str,
    answer: str,
    source_ref: str,
    category: ErrorCategory | None = None,
):
    topic = session.scalar(select(TopicORM).where(TopicORM.title == VECTORS))
    task = svc.add_task(
        {
            "subject": Subject.MATH_PROFILE,
            "statement": statement,
            "expected_answer": answer,
            "source": "official",
            "source_url": f"https://example.org/{source_ref}",
            "source_ref": source_ref,
            "topic_id": topic.id,
            "error_category": category,
        }
    )
    svc.approve_task(task.id)
    if task.topic_id is not None:
        topic = session.get(TopicORM, task.topic_id)
    return task, topic


def _drill_mission(svc: LearningService, topic, task) -> UUID:
    payload = svc.create_mission(
        {
            "student_id": STUDENT,
            "subject": Subject.MATH_PROFILE,
            "title": "Дрилл: Векторы",
            "instructions": "",
            "status": MissionStatus.ACTIVE,
            "ai_policy": AiPolicy.ATTEMPT_FIRST,
            "threshold_percent": 80.0,
            "topic_id": topic.id,
            "task_id": task.id,
            "due_date": date.today(),
            "source_ref": "daily:manual",
        }
    )
    mission_id = payload["id"]
    assert isinstance(mission_id, UUID)
    return mission_id


def _submit(session, mission_id: UUID, answer: str) -> dict:
    return asyncio.run(
        service(session).submit_attempt(
            {
                "mission_id": mission_id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.UNKNOWN,
                "answer_text": answer,
            }
        )
    )


def test_correct_drill_passes_and_schedules_reviews(seeded_session):
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "5", None)
    mission_id = _drill_mission(svc, topic, task)

    result = _submit(seeded_session, mission_id, "5")  # BoomReviewer would raise if used

    assert result["status"] == EvidenceStatus.PASSED
    assert result["score_percent"] == 100.0
    assert seeded_session.get(MissionORM, mission_id).status == MissionStatus.DONE
    reviews = seeded_session.scalars(
        select(ReviewItemORM).where(ReviewItemORM.source_evidence_id == result["evidence_id"])
    ).all()
    assert len(reviews) == 2  # +7 / +30 spaced review cards


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_drill_solution_figure_for_interval_answer(seeded_session):
    # post-attempt разбор: интервальный ответ -> PNG числовой прямой
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "(1; 9)", None)
    mission_id = _drill_mission(svc, topic, task)
    png = svc.drill_solution_figure(mission_id)
    assert png is not None and png[:8] == b"\x89PNG\r\n\x1a\n"


def test_drill_solution_figure_none_for_scalar_answer(seeded_session):
    # скалярный ответ уравнения -> фигуры нет (никогда не рисуем неверное)
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "5", None)
    mission_id = _drill_mission(svc, topic, task)
    assert svc.drill_solution_figure(mission_id) is None


def test_wrong_drill_fails_with_task_error_category(seeded_session):
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "5", ErrorCategory.SIGN_TRANSFER)
    mission_id = _drill_mission(svc, topic, task)

    result = _submit(seeded_session, mission_id, "7")

    assert result["status"] == EvidenceStatus.FAILED
    assert result["error_category"] == ErrorCategory.SIGN_TRANSFER
    assert seeded_session.get(MissionORM, mission_id).status == MissionStatus.REPEAT
    error = seeded_session.scalar(
        select(ErrorEventORM).where(ErrorEventORM.attempt_id == result["attempt_id"])
    )
    assert error is not None
    assert error.category == ErrorCategory.SIGN_TRANSFER


def test_answer_normalization_accepts_decimal_comma(seeded_session):
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "2.5", None)
    mission_id = _drill_mission(svc, topic, task)

    result = _submit(seeded_session, mission_id, " 2,5 ")  # comma + spaces

    assert result["status"] == EvidenceStatus.PASSED


def test_list_daily_drill_excludes_non_drill_missions(seeded_session):
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "5", None)
    mission_id = _drill_mission(svc, topic, task)

    drills = svc.list_daily_drill(STUDENT)
    ids = {d["id"] for d in drills}

    assert mission_id in ids
    assert all(d["statement"] for d in drills)  # every drill carries a task statement
    # seeded non-drill missions (mcp/seed source_ref) must not leak into the chat queue
    non_drill = seeded_session.scalars(
        select(MissionORM).where(MissionORM.source_ref.is_(None))
    ).all()
    assert non_drill  # sanity: seed created plain missions
    assert all(m.id not in ids for m in non_drill)


# ---- drill_solution_visual tests ----


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_drill_solution_visual_interval_only(seeded_session):
    """Only expected_answer is an interval -> VisualAid with correct solution only."""
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "(1; 9)", None)
    mission_id = _drill_mission(svc, topic, task)

    # No student answer provided
    visual = svc.drill_solution_visual(mission_id, None)
    assert visual is not None
    assert isinstance(visual, VisualAid)
    assert visual.kind == "number_line"
    assert visual.png[:8] == b"\x89PNG\r\n\x1a\n"
    assert "Решение" in visual.caption


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_drill_solution_visual_both_intervals(seeded_session):
    """Both expected and student answers are parseable intervals -> both drawn."""
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "(1; 9)", None)
    mission_id = _drill_mission(svc, topic, task)

    visual = svc.drill_solution_visual(mission_id, student_answer="(2; 7)")
    assert visual is not None
    assert isinstance(visual, VisualAid)
    assert visual.kind == "number_line"
    assert visual.png[:8] == b"\x89PNG\r\n\x1a\n"
    assert "твой ответ" in visual.caption


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_drill_solution_visual_unparseable_student(seeded_session):
    """Unparseable student answer -> only correct interval shown."""
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "(1; 9)", None)
    mission_id = _drill_mission(svc, topic, task)

    visual = svc.drill_solution_visual(mission_id, student_answer="как-то так")
    assert visual is not None
    assert isinstance(visual, VisualAid)
    assert visual.png[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_drill_solution_visual_scalar_returns_none(seeded_session):
    """Scalar expected answer -> no visual aid."""
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "5", None)
    mission_id = _drill_mission(svc, topic, task)

    visual = svc.drill_solution_visual(mission_id, student_answer="5")
    assert visual is None


def test_drill_solution_figure_still_works_as_wrapper(seeded_session):
    """drill_solution_figure returns PNG bytes via the new visual path."""
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "(1; 9)", None)
    mission_id = _drill_mission(svc, topic, task)

    png = svc.drill_solution_figure(mission_id)
    assert png is not None and png[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_drill_solution_visual_robust_text_parsing(seeded_session):
    """Real TG text with prefixes should parse and produce overlay."""
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "(1; 9)", None)
    mission_id = _drill_mission(svc, topic, task)

    raw = "ответ х принадлежит (2; 7)\nрешение: подставим значения и проверим"
    visual = svc.drill_solution_visual(mission_id, raw)
    assert visual is not None
    assert isinstance(visual, VisualAid)
    assert visual.png[:8] == b"\x89PNG\r\n\x1a\n"
    assert "твой ответ" in visual.caption
    # Caption must NOT contain the full raw text
    assert "подставим" not in visual.caption
    assert "проверим" not in visual.caption


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_drill_solution_visual_unparseable_robust_returns_correct_only(seeded_session):
    """Unparseable student text -> correct-only PNG, not None."""
    svc = service(seeded_session)
    task, topic = _approved_task(svc, seeded_session, "(1; 9)", None)
    mission_id = _drill_mission(svc, topic, task)

    visual = svc.drill_solution_visual(mission_id, student_answer="что-то вроде 3 или 4")
    assert visual is not None
    assert isinstance(visual, VisualAid)
    assert visual.png[:8] == b"\x89PNG\r\n\x1a\n"
    assert "твой ответ" not in visual.caption


def test_parse_interval_answer_from_text_short_caption():
    """Caption should not contain raw long text."""
    raw = "ответ х принадлежит (-бесконечность; -2) и [1; +бесконечность)\nрешение: переносим, возводим в квадрат, получаем неравенство..."
    parsed = parse_interval_answer_from_text(raw)
    assert parsed == [
        (NEG, False, -2.0, False),
        (1.0, True, POS, False),
    ]


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_drill_solution_visual_probability_task(seeded_session):
    """Known probability source_ref -> post-attempt probability visual."""
    svc = service(seeded_session)
    statement = (
        "В коробке 30 шаров: 12 красных, 8 синих и 10 зелёных. "
        "Найдите вероятность достать красный или синий шар."
    )
    task, topic = _approved_task_with_source_ref(
        svc,
        seeded_session,
        statement=statement,
        answer="2/3",
        source_ref="corpus:probability:task-a",
        category=ErrorCategory.PROBABILITY_DOUBLE_COUNT,
    )
    mission_id = _drill_mission(svc, topic, task)

    visual = svc.drill_solution_visual(mission_id, student_answer="1/2")
    assert visual is not None
    assert visual.kind == "probability"
    assert visual.png[:8] == b"\x89PNG\r\n\x1a\n"
    assert visual.caption == "Схема к задаче на вероятность"


def test_drill_solution_visual_unknown_scalar_still_none(seeded_session):
    """Scalar tasks without a known probability source_ref keep old behavior."""
    svc = service(seeded_session)
    task, topic = _approved_task_with_source_ref(
        svc,
        seeded_session,
        statement="Найдите длину вектора (3; 4).",
        answer="5",
        source_ref="corpus:unknown:task",
    )
    mission_id = _drill_mission(svc, topic, task)

    assert svc.drill_solution_visual(mission_id, student_answer="5") is None
