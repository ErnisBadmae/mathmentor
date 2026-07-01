"""Sandbox student-flow simulator.

Runs against an in-memory SQLite database, not production Postgres and not
Telegram. The goal is to exercise the same application use cases a learner hits:
mission -> attempt -> verdict -> post-attempt visual.

This is intentionally deterministic so local Qwen can run it as a read-only
report task and collect raw output without touching learner data.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.application.use_cases import LearningService, RuleBasedReviewer  # noqa: E402
from app.domain.enums import (  # noqa: E402
    AiPolicy,
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    MissionStatus,
    Subject,
    TaskStatus,
)
from app.infrastructure.db import Base  # noqa: E402
from app.infrastructure.models import MissionORM, TaskORM, TopicORM  # noqa: E402
from app.infrastructure.repositories import SqlAlchemyUnitOfWork  # noqa: E402
from scripts import seed as seed_module  # noqa: E402

STUDENT = seed_module.DEMO_STUDENT_ID


def _service(session) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer())


def _seeded_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed_module.SessionLocal = session_factory
    seed_module.seed()
    return session_factory()


def _topic(session) -> TopicORM:
    topic = session.scalar(select(TopicORM).where(TopicORM.title == "Векторы"))
    if topic is None:
        raise RuntimeError("seed did not create the expected topic")
    return topic


def _ensure_interval_task(session) -> TaskORM:
    svc = _service(session)
    topic = _topic(session)
    source_ref = "sim:interval:visual"
    task = session.scalar(select(TaskORM).where(TaskORM.source_ref == source_ref))
    if task is None:
        task = svc.add_task(
            {
                "subject": Subject.MATH_PROFILE,
                "statement": "Решите неравенство: 1 < x < 9.",
                "expected_answer": "(1; 9)",
                "source": "simulation",
                "source_ref": source_ref,
                "topic_id": topic.id,
                "error_category": ErrorCategory.CONDITION_READING,
            }
        )
    if task.status != TaskStatus.APPROVED:
        svc.approve_task(task.id)
    return task


def _probability_task(session) -> TaskORM:
    task = session.scalar(
        select(TaskORM).where(TaskORM.source_ref == "corpus:probability:task-a")
    )
    if task is None:
        raise RuntimeError("seed did not create probability task-a")
    if task.status != TaskStatus.APPROVED:
        _service(session).approve_task(task.id)
    return task


def _mission_for_task(session, task: TaskORM, suffix: str) -> UUID:
    svc = _service(session)
    payload = svc.create_mission(
        {
            "student_id": STUDENT,
            "subject": task.subject,
            "title": f"Simulation: {suffix}",
            "instructions": "",
            "status": MissionStatus.ACTIVE,
            "ai_policy": AiPolicy.ATTEMPT_FIRST,
            "threshold_percent": 80.0,
            "topic_id": task.topic_id,
            "task_id": task.id,
            "due_date": date.today(),
            "source_ref": f"daily:simulation:{suffix}",
        }
    )
    mission_id = payload["id"]
    if not isinstance(mission_id, UUID):
        raise TypeError("mission id is not a UUID")
    return mission_id


async def _attempt(session, mission_id: UUID, answer: str) -> dict[str, object]:
    return await _service(session).submit_attempt(
        {
            "mission_id": mission_id,
            "kind": AttemptKind.TEXT,
            "mode": AttemptMode.UNKNOWN,
            "answer_text": answer,
        }
    )


def _run_case(
    session,
    *,
    name: str,
    task: TaskORM,
    answer: str,
    expected_status: EvidenceStatus,
    expected_visual_kind: str,
) -> dict[str, object]:
    mission_id = _mission_for_task(session, task, name)
    result = asyncio.run(_attempt(session, mission_id, answer))
    visual = _service(session).drill_solution_visual(mission_id, answer)
    mission = session.get(MissionORM, mission_id)

    ok = (
        result["status"] == expected_status
        and visual is not None
        and visual.kind == expected_visual_kind
        and visual.png[:8] == b"\x89PNG\r\n\x1a\n"
    )
    return {
        "name": name,
        "ok": ok,
        "answer": answer,
        "status": getattr(result["status"], "value", str(result["status"])),
        "mission_status": getattr(mission.status, "value", str(mission.status)),
        "visual_kind": visual.kind if visual is not None else None,
        "visual_caption": visual.caption if visual is not None else None,
        "png_bytes": len(visual.png) if visual is not None else 0,
    }


def build_report() -> dict[str, object]:
    session = _seeded_session()
    try:
        interval_task = _ensure_interval_task(session)
        probability_task = _probability_task(session)
        cases = [
            _run_case(
                session,
                name="interval_wrong_overlay",
                task=interval_task,
                answer="(2; 7)",
                expected_status=EvidenceStatus.FAILED,
                expected_visual_kind="number_line",
            ),
            _run_case(
                session,
                name="interval_unparseable_answer",
                task=interval_task,
                answer="примерно между числами",
                expected_status=EvidenceStatus.FAILED,
                expected_visual_kind="number_line",
            ),
            _run_case(
                session,
                name="probability_wrong_answer",
                task=probability_task,
                answer="1/2",
                expected_status=EvidenceStatus.FAILED,
                expected_visual_kind="probability",
            ),
        ]
    finally:
        session.close()

    return {"ok": all(case["ok"] for case in cases), "cases": cases}


def run_json() -> str:
    return json.dumps(build_report(), ensure_ascii=False, indent=2)


def main() -> int:
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
