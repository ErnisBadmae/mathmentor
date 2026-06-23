"""MCP server: lets an agent (Claude/Codex) act as the senior mentor over this project.

Thin adapter over ``LearningService`` — read the student's state/progress/history and
edit the track (missions, task bank, score events, reviews). No paid cloud LLM API in
the backend: the senior model is the agent in the session. The local model stays the
per-attempt evaluator. Run from ``backend/`` with the ``mcp`` extra installed:

    python -m app.adapters.mcp.server

Writes are tagged with provenance; new bank tasks land as DRAFT (only APPROVED tasks
reach missions/students). Answer keys are visible to the agent, never to the student.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `app...` importable when an MCP client launches this from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from datetime import date, datetime  # noqa: E402
from enum import Enum  # noqa: E402
from typing import Any  # noqa: E402
from uuid import UUID  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

from app.application.use_cases import LearningService, RuleBasedReviewer  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.domain.enums import AiPolicy, ErrorCategory, MissionStatus, Subject, TaskStatus  # noqa: E402
from app.infrastructure.db import SessionLocal  # noqa: E402
from app.infrastructure.llm import OpenAICompatibleReviewer  # noqa: E402
from app.infrastructure.repositories import SqlAlchemyUnitOfWork  # noqa: E402

# One student in the family pilot (the all-zero UUID the frontend/seed use).
DEFAULT_STUDENT_ID = "00000000-0000-0000-0000-000000000000"

mcp = FastMCP("ege-mentor")


def _serialize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _service(session) -> LearningService:
    settings = get_settings()
    connection = settings.llm_connection()
    reviewer = OpenAICompatibleReviewer(connection) if connection else RuleBasedReviewer()
    return LearningService(SqlAlchemyUnitOfWork(session), reviewer, settings.local_timezone)


def _read(fn: Any) -> Any:
    with SessionLocal() as session:
        return _serialize(fn(_service(session)))


# ---- read tools -------------------------------------------------------------


@mcp.tool()
def student_overview(student_id: str = DEFAULT_STUDENT_ID) -> Any:
    """Dashboard: subject scores, clean-sheet ratio, top errors, due reviews."""
    return _read(lambda s: s.get_dashboard(UUID(student_id)))


@mcp.tool()
def program_progress(student_id: str = DEFAULT_STUDENT_ID) -> Any:
    """Program phases with coverage/percent and per-topic state and bank progress."""
    return _read(lambda s: s.list_program_progress(UUID(student_id)))


@mcp.tool()
def topic_lifecycle(student_id: str = DEFAULT_STUDENT_ID) -> Any:
    """Computed state of every active topic (open/in_work/under_review/confirmed/back_to_work)."""
    return _read(lambda s: s.list_topic_lifecycle(UUID(student_id)))


@mcp.tool()
def diagnostics(student_id: str = DEFAULT_STUDENT_ID) -> Any:
    """Diagnostic slices (срезы) already done: date, score, percent."""
    return _read(lambda s: s.list_diagnostics(UUID(student_id)))


@mcp.tool()
def error_journal(student_id: str = DEFAULT_STUDENT_ID) -> Any:
    """The student's logged mistakes with categories and detail."""
    return _read(lambda s: s.list_errors(UUID(student_id)))


@mcp.tool()
def attempt_history(
    student_id: str = DEFAULT_STUDENT_ID, topic_id: str | None = None, limit: int = 50
) -> Any:
    """How the student solved: attempt content + the reviewer's interpretation."""
    tid = UUID(topic_id) if topic_id else None
    return _read(lambda s: s.list_attempt_history(UUID(student_id), tid, limit))


@mcp.tool()
def reviews(student_id: str = DEFAULT_STUDENT_ID) -> Any:
    """Spaced-review queue (+7/+30)."""
    return _read(lambda s: s.list_reviews(UUID(student_id)))


@mcp.tool()
def manual_reviews(student_id: str = DEFAULT_STUDENT_ID) -> Any:
    """Attempts waiting for manual review (LLM unavailable/unsure)."""
    return _read(lambda s: s.list_manual_reviews(UUID(student_id)))


@mcp.tool()
def list_tasks(status: str | None = None) -> Any:
    """Task bank items, optionally filtered by status (draft|approved)."""
    task_status = TaskStatus(status) if status else None
    return _read(lambda s: s.list_tasks(task_status))


# ---- write tools (provenance-tagged) ----------------------------------------


@mcp.tool()
def create_mission(
    subject: str,
    title: str,
    instructions: str = "",
    topic_id: str | None = None,
    task_id: str | None = None,
    threshold_percent: float = 80.0,
    due_date: str | None = None,
    drill: bool = False,
    student_id: str = DEFAULT_STUDENT_ID,
) -> Any:
    """Create an ACTIVE mission for the student (track edit). Tagged source=mcp:agent.

    Set drill=True for a part-1 Telegram drill: link an approved exact-answer task via
    task_id; the attempt is then graded by exact match (instant, no LLM) and the mission
    is delivered to the Telegram queue (source_ref=daily:manual)."""
    values = {
        "student_id": UUID(student_id),
        "subject": Subject(subject),
        "title": title,
        "instructions": instructions,
        "status": MissionStatus.ACTIVE,
        "ai_policy": AiPolicy.ATTEMPT_FIRST,
        "threshold_percent": threshold_percent,
        "topic_id": UUID(topic_id) if topic_id else None,
        "task_id": UUID(task_id) if task_id else None,
        "due_date": date.fromisoformat(due_date) if due_date else None,
        "source_ref": "daily:manual" if drill else "mcp:agent",
    }
    with SessionLocal() as session:
        return _serialize(_service(session).create_mission(values))


@mcp.tool()
def update_mission(
    mission_id: str,
    title: str | None = None,
    instructions: str | None = None,
    threshold_percent: float | None = None,
    due_date: str | None = None,
) -> Any:
    """Edit an existing mission (only provided fields change)."""
    values: dict[str, Any] = {}
    if title is not None:
        values["title"] = title
    if instructions is not None:
        values["instructions"] = instructions
    if threshold_percent is not None:
        values["threshold_percent"] = threshold_percent
    if due_date is not None:
        values["due_date"] = date.fromisoformat(due_date)
    with SessionLocal() as session:
        return _serialize(_service(session).update_mission(UUID(mission_id), values))


@mcp.tool()
def add_task(
    subject: str,
    statement: str,
    expected_answer: str,
    source_url: str,
    topic_id: str | None = None,
    task_number: str | None = None,
    solution: str | None = None,
    error_category: str | None = None,
    source: str = "official",
) -> Any:
    """Add a task to the bank as DRAFT with an exact source link. Approve separately."""
    values = {
        "subject": Subject(subject),
        "statement": statement,
        "expected_answer": expected_answer,
        "source_url": source_url,
        "source": source,
        "topic_id": UUID(topic_id) if topic_id else None,
        "task_number": task_number,
        "solution": solution,
        "error_category": ErrorCategory(error_category) if error_category else None,
        "status": TaskStatus.DRAFT,
        "source_ref": source_url,
    }
    with SessionLocal() as session:
        task = _service(session).add_task(values)
        return {"id": str(task.id), "status": task.status.value}


@mcp.tool()
def approve_task(task_id: str) -> Any:
    """Approve a DRAFT task so missions can use it."""
    with SessionLocal() as session:
        task = _service(session).approve_task(UUID(task_id))
        return {"id": str(task.id), "status": task.status.value}


@mcp.tool()
def record_score_event(
    subject: str,
    score: int,
    kind: str = "exam_variant",
    occurred_on: str | None = None,
    note: str | None = None,
    student_id: str = DEFAULT_STUDENT_ID,
) -> Any:
    """Record an objective score signal (e.g. external mock). Moves current_score by §11."""
    values = {
        "student_id": UUID(student_id),
        "subject": Subject(subject),
        "score": score,
        "kind": kind,
        "occurred_on": date.fromisoformat(occurred_on) if occurred_on else None,
        "note": note,
    }
    with SessionLocal() as session:
        event = _service(session).record_score_event(values)
        return {"id": str(event.id), "subject": subject, "score": score}


@mcp.tool()
def record_review_result(review_id: str, passed: bool) -> Any:
    """Mark a spaced-review card passed/failed (failed reopens the topic per §8)."""
    with SessionLocal() as session:
        _service(session).record_review_result(UUID(review_id), passed)
        return {"review_id": review_id, "passed": passed}


@mcp.tool()
def publish_feedback(body: str, topic_id: str | None = None, student_id: str = DEFAULT_STUDENT_ID) -> Any:
    """Publish a mentor note the STUDENT reads on the dashboard feed (transparent process).
    Write it for the student in plain language; never include answer keys. Optionally tag a
    topic_id. Published immediately. Tagged source=mcp:agent."""
    values = {
        "student_id": UUID(student_id),
        "topic_id": UUID(topic_id) if topic_id else None,
        "body": body,
        "source_ref": "mcp:agent",
    }
    with SessionLocal() as session:
        return _serialize(_service(session).publish_feedback(values))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
