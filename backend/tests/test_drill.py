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
from app.application.use_cases import LearningService
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
