"""Read-only export of EGE learning cycles into Portfolio Learning Measurement v0.

Direction of dependency: this script -> JSONL -> `develop/measurement`. Nothing in
`app/` imports it, it never writes, and it never touches progression. It reads
missions, attempts, evidence and review cards, and emits one JSONL record per
assessed phase.

What leaves the database: verdicts, scores, thresholds, modes, error categories,
durations, provenance versions and salted hashes. Never answer text, code,
feedback, task statements, expected answers or a direct identifier.

The record field names are duplicated here on purpose. The measurement contract
requires the same fields; it does not require a shared runtime library.

Usage (a database URL is always explicit; there is no implicit default):

    python -m scripts.export_measurement_cycles \
        --database-url postgresql+psycopg://... \
        --salt-env MEASUREMENT_EXPORT_SALT \
        --out  C:/private/exports/ege_cycles.jsonl \
        --summary-out C:/private/exports/ege_summary.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

VERTICAL = "egeMentor"
SCHEMA_VERSION = "learning-measurement/v0"
SCORE_SCALE_MIN = 0.0
SCORE_SCALE_MAX = 100.0

REVIEW_SOURCE_PREFIX = "daily:review:"
PRIMARY_WINDOW_DAYS = 7

# Written into every record. See !DOC/architecture/EGE_EQUIVALENCE_RULE_V1.md.
EQUIVALENCE_RULE_ID = "ege-equivalence-v1"

# EGE does not model a critical error today. The set is empty by declaration, not
# by observation; the tutor populates it when critical categories are defined.
CRITICAL_ERROR_CATEGORIES: frozenset[str] = frozenset()

# `evidence.model_id` is written as the judge's model, or one of these markers.
DETERMINISTIC_ASSESSOR_IDS = frozenset({"exact-answer"})
HUMAN_ASSESSOR_IDS = frozenset({"manual-review", "operator-recovery"})

RECORD_FIELDS = (
    "schema_version", "vertical", "learner_hash", "cycle_id", "competency_key",
    "cohort", "phase", "task_family", "task_id", "task_revision",
    "previously_exposed", "rubric_version", "rubric_status", "score_original",
    "score_scale_min", "score_scale_max", "threshold_original", "hints_used",
    "attempt_mode", "critical_error", "error_category", "occurred_at",
    "days_since_intervention", "learner_minutes", "mentor_minutes", "assessor",
    "model_id", "prompt_version",
)

# Anything on this list must never appear in an emitted record.
FORBIDDEN_FIELDS = frozenset(
    {
        "answer_text", "code_text", "answer", "solution", "feedback", "statement",
        "expected_answer", "details_json", "transcript", "notes", "student_id",
        "user_id", "learner_id", "learner_ref", "telegram_id", "chat_id", "name",
        "full_name", "email", "topic_title",
    }
)

MIN_SALT_LENGTH = 16


@dataclass(frozen=True)
class AttemptFact:
    """One attempt with the mission, task and evidence it belongs to."""

    student_id: str
    subject: str
    topic_id: str | None
    task_id: str | None
    task_number: str | None
    mission_id: str
    mission_source_ref: str | None
    threshold_percent: float | None
    attempt_id: str
    attempt_mode: str
    time_spent_minutes: int | None
    submitted_at: datetime
    evidence_id: str | None
    evidence_status: str | None
    score_percent: float | None
    error_category: str | None
    rubric_version: str | None
    model_id: str | None
    prompt_version: str | None

    @property
    def is_review_drill(self) -> bool:
        return (self.mission_source_ref or "").startswith(REVIEW_SOURCE_PREFIX)


@dataclass(frozen=True)
class ReviewFact:
    review_id: str
    student_id: str
    topic_id: str | None
    due_date: date
    source_evidence_id: str | None


# --------------------------------------------------------------------------- #
# Pure export logic
# --------------------------------------------------------------------------- #


def learner_hash(student_id: str, salt: str) -> str:
    if len(salt) < MIN_SALT_LENGTH:
        raise ValueError(f"export salt must be at least {MIN_SALT_LENGTH} characters")
    return hashlib.sha256(f"{salt}:{student_id}".encode("utf-8")).hexdigest()[:32]


def _rubric_status(evidence_status: str | None) -> str | None:
    return {
        "passed": "pass",
        "failed": "fail",
        "needs_manual_review": "needs_manual_review",
    }.get((evidence_status or "").lower())


def _assessor(model_id: str | None) -> str:
    """An unrecognised assessor is treated as a model, the least trusted option."""
    if model_id in HUMAN_ASSESSOR_IDS:
        return "human"
    if model_id in DETERMINISTIC_ASSESSOR_IDS:
        return "deterministic"
    return "llm_shadow"


def _record(
    fact: AttemptFact,
    *,
    phase: str,
    cycle_id: str,
    hashed_learner: str,
    previously_exposed: bool,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "vertical": VERTICAL,
        "learner_hash": hashed_learner,
        "cycle_id": cycle_id,
        "competency_key": f"{fact.subject}:{fact.topic_id}",
        "cohort": "trained",
        "phase": phase,
        "task_family": f"{EQUIVALENCE_RULE_ID}:{fact.subject}:{fact.topic_id}:{fact.task_number}",
        "task_id": str(fact.task_id),
        "task_revision": None,
        "previously_exposed": previously_exposed,
        "rubric_version": fact.rubric_version,
        "rubric_status": _rubric_status(fact.evidence_status),
        "score_original": fact.score_percent,
        "score_scale_min": SCORE_SCALE_MIN,
        "score_scale_max": SCORE_SCALE_MAX,
        "threshold_original": fact.threshold_percent,
        # Hints are not counted in EGE; independence rides on attempt_mode, and
        # `unknown` deliberately fails closed inside the instrument.
        "hints_used": None,
        "attempt_mode": fact.attempt_mode if fact.attempt_mode in
        ("clean_sheet", "with_hint", "unknown") else "unknown",
        "critical_error": (fact.error_category or "") in CRITICAL_ERROR_CATEGORIES,
        "error_category": fact.error_category,
        "occurred_at": fact.submitted_at.isoformat(),
        # Left to the instrument, which derives the delay from the timestamps.
        "days_since_intervention": None,
        "learner_minutes": fact.time_spent_minutes,
        # AGENTS.md: operator minutes are never inferred from DB timestamps.
        "mentor_minutes": None,
        "assessor": _assessor(fact.model_id),
        "model_id": fact.model_id,
        "prompt_version": fact.prompt_version,
    }


def _first_exposure(attempts: Iterable[AttemptFact]) -> dict[tuple[str, str], datetime]:
    seen: dict[tuple[str, str], datetime] = {}
    for fact in attempts:
        if fact.task_id is None:
            continue
        key = (fact.student_id, str(fact.task_id))
        if key not in seen or fact.submitted_at < seen[key]:
            seen[key] = fact.submitted_at
    return seen


def build_records(
    attempts: list[AttemptFact], reviews: list[ReviewFact], *, salt: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Assemble cycles from the review ledger. Never guesses a missing fact."""
    ordered = sorted(attempts, key=lambda f: f.submitted_at)
    by_evidence = {f.evidence_id: f for f in ordered if f.evidence_id}
    by_source_ref: dict[str, list[AttemptFact]] = {}
    for fact in ordered:
        if fact.mission_source_ref:
            by_source_ref.setdefault(fact.mission_source_ref, []).append(fact)
    first_exposure = _first_exposure(ordered)

    by_topic: dict[tuple[str, str], list[AttemptFact]] = {}
    for fact in ordered:
        if fact.topic_id is not None:
            by_topic.setdefault((fact.student_id, str(fact.topic_id)), []).append(fact)

    records: list[dict[str, Any]] = []
    skipped: dict[str, int] = {}
    scheduled_windows: dict[str, int] = {}
    emitted_cycles = 0

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    for review in sorted(reviews, key=lambda r: (r.due_date, r.review_id)):
        if not review.source_evidence_id:
            skip("review_without_source_evidence")
            continue
        head = by_evidence.get(review.source_evidence_id)
        if head is None:
            skip("head_evidence_not_found")
            continue
        if head.is_review_drill:
            # A review drill must not father another cycle: its predecessor is a
            # review, not a training episode.
            skip("head_is_review_drill")
            continue
        if _rubric_status(head.evidence_status) != "pass":
            skip("head_evidence_not_passed")
            continue

        drill_attempts = by_source_ref.get(f"{REVIEW_SOURCE_PREFIX}{review.review_id}", [])
        if not drill_attempts:
            skip("drill_not_attempted_yet")
            continue
        if len(drill_attempts) > 1:
            # Retries on the delayed task are not one independent measurement.
            skip("drill_multiple_attempts")
            continue
        delayed = drill_attempts[0]

        topic_attempts = by_topic.get((head.student_id, str(head.topic_id)), [])
        baseline = topic_attempts[0] if topic_attempts else None
        if baseline is None or baseline.submitted_at > head.submitted_at:
            skip("baseline_not_found")
            continue

        phases = {"baseline": baseline, "immediate": head, "delayed_transfer": delayed}
        if any(f.evidence_id is None or _rubric_status(f.evidence_status) is None
               for f in phases.values()):
            skip("phase_without_evidence")
            continue
        if any(f.task_id is None for f in phases.values()):
            skip("task_id_missing")
            continue
        if any(f.task_number is None for f in phases.values()):
            # Without an official task number the equivalence rule cannot be
            # evaluated, and a shared `None` would fake a match.
            skip("task_number_missing")
            continue
        if delayed.topic_id != head.topic_id:
            skip("drill_topic_mismatch")
            continue

        scheduled = (review.due_date - head.submitted_at.date()).days
        bucket = "primary_plus_7" if scheduled == PRIMARY_WINDOW_DAYS else f"scheduled_plus_{scheduled}"
        scheduled_windows[bucket] = scheduled_windows.get(bucket, 0) + 1

        hashed = learner_hash(head.student_id, salt)
        cycle_id = f"ege:{review.review_id}"
        for phase, fact in phases.items():
            exposed = first_exposure.get(
                (fact.student_id, str(fact.task_id)), fact.submitted_at
            ) < fact.submitted_at
            records.append(
                _record(
                    fact,
                    phase=phase,
                    cycle_id=cycle_id,
                    hashed_learner=hashed,
                    previously_exposed=exposed,
                )
            )
        emitted_cycles += 1

    _assert_no_private_fields(records)

    summary = {
        "vertical": VERTICAL,
        "equivalence_rule": EQUIVALENCE_RULE_ID,
        "reviews_seen": len(reviews),
        "potential_cycles": len(reviews),
        "cycles_emitted": emitted_cycles,
        "records_emitted": len(records),
        "skipped": dict(sorted(skipped.items())),
        "scheduled_windows": dict(sorted(scheduled_windows.items())),
    }
    return records, summary


def _assert_no_private_fields(records: list[dict[str, Any]]) -> None:
    for record in records:
        leaked = FORBIDDEN_FIELDS.intersection(record)
        if leaked:
            raise AssertionError(f"exporter would leak private fields: {sorted(leaked)}")
        unexpected = set(record) - set(RECORD_FIELDS)
        if unexpected:
            raise AssertionError(f"record carries undeclared fields: {sorted(unexpected)}")


# --------------------------------------------------------------------------- #
# Read-only database access
# --------------------------------------------------------------------------- #


def fetch_facts(session: Any) -> tuple[list[AttemptFact], list[ReviewFact]]:
    """Two read-only selects. No ORM writes, no flush, no service call."""
    from sqlalchemy import select

    from app.infrastructure.models import (
        AttemptORM,
        EvidenceORM,
        MissionORM,
        ReviewItemORM,
        TaskORM,
    )

    rows = session.execute(
        select(AttemptORM, MissionORM, TaskORM, EvidenceORM)
        .join(MissionORM, MissionORM.id == AttemptORM.mission_id)
        .outerjoin(TaskORM, TaskORM.id == MissionORM.task_id)
        .outerjoin(EvidenceORM, EvidenceORM.attempt_id == AttemptORM.id)
        .order_by(AttemptORM.submitted_at)
    ).all()

    attempts = [
        AttemptFact(
            student_id=str(attempt.student_id),
            subject=str(getattr(mission.subject, "value", mission.subject)),
            topic_id=str(mission.topic_id) if mission.topic_id else None,
            task_id=str(mission.task_id) if mission.task_id else None,
            task_number=getattr(task, "task_number", None),
            mission_id=str(mission.id),
            mission_source_ref=mission.source_ref,
            threshold_percent=mission.threshold_percent,
            attempt_id=str(attempt.id),
            attempt_mode=str(getattr(attempt.mode, "value", attempt.mode)),
            time_spent_minutes=attempt.time_spent_minutes,
            submitted_at=attempt.submitted_at,
            evidence_id=str(evidence.id) if evidence is not None else None,
            evidence_status=(
                str(getattr(evidence.status, "value", evidence.status))
                if evidence is not None
                else None
            ),
            score_percent=evidence.score_percent if evidence is not None else None,
            error_category=(
                str(getattr(evidence.error_category, "value", evidence.error_category))
                if evidence is not None
                else None
            ),
            rubric_version=evidence.rubric_version if evidence is not None else None,
            model_id=evidence.model_id if evidence is not None else None,
            prompt_version=evidence.prompt_version if evidence is not None else None,
        )
        for attempt, mission, task, evidence in rows
    ]

    reviews = [
        ReviewFact(
            review_id=str(item.id),
            student_id=str(item.student_id),
            topic_id=str(item.topic_id) if item.topic_id else None,
            due_date=item.due_date,
            source_evidence_id=(
                str(item.source_evidence_id) if item.source_evidence_id else None
            ),
        )
        for item in session.execute(select(ReviewItemORM)).scalars().all()
    ]
    return attempts, reviews


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only EGE measurement export.")
    parser.add_argument("--database-url", required=True, help="Explicit, no default.")
    parser.add_argument("--salt-env", default="MEASUREMENT_EXPORT_SALT")
    parser.add_argument("--out", required=True, type=Path, help="JSONL destination.")
    parser.add_argument("--summary-out", type=Path, default=None)
    args = parser.parse_args(argv)

    salt = os.environ.get(args.salt_env, "")
    if len(salt) < MIN_SALT_LENGTH:
        print(
            f"{args.salt_env} must hold a stable secret of at least "
            f"{MIN_SALT_LENGTH} characters; refusing to export.",
            file=sys.stderr,
        )
        return 2

    resolved = args.out.resolve()
    if Path(__file__).resolve().parents[2] in resolved.parents:
        print(f"refusing to write inside the repository: {resolved}", file=sys.stderr)
        return 2

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(args.database_url)
    if engine.dialect.name == "postgresql":
        # The server, not this script, enforces that nothing can be written.
        engine = engine.execution_options(postgresql_readonly=True)
    with Session(engine) as session:
        attempts, reviews = fetch_facts(session)
        session.rollback()

    records, summary = build_records(attempts, reviews, salt=salt)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    if args.summary_out:
        args.summary_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
