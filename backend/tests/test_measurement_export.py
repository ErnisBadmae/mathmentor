"""Synthetic tests for the read-only measurement export.

No live database, no real learner data. The ORM test runs against in-memory
SQLite built from the project's own metadata, so the queries are proven against
the real schema rather than against a hand-written fixture.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from scripts.export_measurement_cycles import (
    AttemptFact,
    ReviewFact,
    build_records,
    fetch_facts,
    learner_hash,
)
from scripts import export_measurement_cycles as exporter

SALT = "a-stable-secret-for-tests"
DAY1 = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)
DAY3 = datetime(2026, 3, 4, 10, 0, tzinfo=UTC)
DAY10 = datetime(2026, 3, 11, 10, 0, tzinfo=UTC)

STUDENT = "11111111-1111-1111-1111-111111111111"
TOPIC = "22222222-2222-2222-2222-222222222222"


def attempt(**over: Any) -> AttemptFact:
    values: dict[str, Any] = {
        "student_id": STUDENT,
        "subject": "math_profile",
        "topic_id": TOPIC,
        "task_id": "task-a",
        "task_number": "10",
        "mission_id": "mission-a",
        "mission_source_ref": None,
        "threshold_percent": 80.0,
        "attempt_id": "attempt-a",
        "attempt_mode": "clean_sheet",
        "time_spent_minutes": 12,
        "submitted_at": DAY1,
        "evidence_id": "evidence-a",
        "evidence_status": "passed",
        "score_percent": 90.0,
        "error_category": "none",
        "rubric_version": "ege-v1",
        "model_id": "exact-answer",
        "prompt_version": "p1",
    }
    values.update(over)
    return AttemptFact(**values)


def cycle_facts(**over: Any) -> tuple[list[AttemptFact], list[ReviewFact]]:
    """Baseline fails on day 1, the topic closes on day 3, the drill runs on day 10."""
    review_id = "review-1"
    baseline = attempt(
        task_id="task-baseline", attempt_id="a1", mission_id="m1",
        evidence_id="e1", evidence_status="failed", score_percent=40.0,
        error_category="odz_logic", submitted_at=DAY1,
    )
    immediate = attempt(
        task_id="task-immediate", attempt_id="a2", mission_id="m2",
        evidence_id="e2", submitted_at=DAY3,
    )
    delayed = attempt(
        **{
            "task_id": "task-delayed",
            "attempt_id": "a3",
            "mission_id": "m3",
            "evidence_id": "e3",
            "submitted_at": DAY10,
            "mission_source_ref": f"daily:review:{review_id}",
            **over.pop("delayed", {}),
        }
    )
    review = ReviewFact(
        review_id=review_id, student_id=STUDENT, topic_id=TOPIC,
        due_date=over.pop("due_date", date(2026, 3, 11)), source_evidence_id="e2",
    )
    return [baseline, immediate, delayed], [review]


def phases(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {r["phase"]: r for r in records}


# --- happy path ------------------------------------------------------------ #


def test_full_cycle_is_emitted_with_three_phases():
    attempts, reviews = cycle_facts()
    records, summary = build_records(attempts, reviews, salt=SALT)

    assert summary["cycles_emitted"] == 1
    assert summary["records_emitted"] == 3
    assert summary["scheduled_windows"] == {"primary_plus_7": 1}
    assert set(phases(records)) == {"baseline", "immediate", "delayed_transfer"}
    assert {r["cycle_id"] for r in records} == {"ege:review-1"}


def test_equivalence_evidence_travels_with_the_records():
    records, _ = build_records(*cycle_facts(), salt=SALT)
    by_phase = phases(records)

    assert len({r["task_family"] for r in records}) == 1
    assert by_phase["delayed_transfer"]["task_family"].startswith("ege-equivalence-v1:")
    assert by_phase["delayed_transfer"]["task_id"] != by_phase["baseline"]["task_id"]
    assert by_phase["delayed_transfer"]["previously_exposed"] is False
    assert {r["threshold_original"] for r in records} == {80.0}
    assert {r["rubric_version"] for r in records} == {"ege-v1"}


def test_verdicts_and_scores_are_carried_without_reinterpretation():
    records, _ = build_records(*cycle_facts(), salt=SALT)
    by_phase = phases(records)

    assert by_phase["baseline"]["rubric_status"] == "fail"
    assert by_phase["baseline"]["score_original"] == 40.0
    assert by_phase["immediate"]["rubric_status"] == "pass"
    assert by_phase["delayed_transfer"]["score_original"] == 90.0
    assert all(r["score_scale_max"] == 100.0 for r in records)


def test_nothing_is_invented():
    records, _ = build_records(*cycle_facts(), salt=SALT)
    for record in records:
        assert record["days_since_intervention"] is None  # derived from timestamps
        assert record["mentor_minutes"] is None  # never inferred from DB timestamps
        assert record["hints_used"] is None  # EGE counts modes, not hints
        assert record["task_revision"] is None
    assert phases(records)["baseline"]["learner_minutes"] == 12


# --- privacy --------------------------------------------------------------- #


def test_records_carry_no_text_and_no_direct_identifier():
    records, _ = build_records(*cycle_facts(), salt=SALT)
    payload = json.dumps(records)

    for record in records:
        assert not exporter.FORBIDDEN_FIELDS.intersection(record)
        assert set(record) <= set(exporter.RECORD_FIELDS)
    assert STUDENT not in payload
    assert TOPIC in payload  # a topic UUID is curriculum structure, not identity


def test_learner_hash_is_salted_stable_and_opaque():
    first = learner_hash(STUDENT, SALT)
    assert first == learner_hash(STUDENT, SALT)
    assert first != learner_hash(STUDENT, SALT + "x")
    assert STUDENT not in first
    assert len(first) == 32


def test_short_salt_is_refused():
    with pytest.raises(ValueError):
        learner_hash(STUDENT, "short")


def test_cli_refuses_to_write_inside_the_repository(monkeypatch, tmp_path):
    monkeypatch.setenv("MEASUREMENT_EXPORT_SALT", SALT)
    inside = Path(exporter.__file__).resolve().parents[2] / "leak.jsonl"
    code = exporter.main(
        ["--database-url", "postgresql://unused", "--out", str(inside)]
    )
    assert code == 2
    assert not inside.exists()


def test_cli_refuses_a_weak_salt(monkeypatch, tmp_path):
    monkeypatch.setenv("MEASUREMENT_EXPORT_SALT", "tiny")
    code = exporter.main(
        ["--database-url", "postgresql://unused", "--out", str(tmp_path / "o.jsonl")]
    )
    assert code == 2


# --- proofs the exporter must establish ------------------------------------ #


def test_delayed_task_reused_from_the_baseline_is_marked_exposed():
    attempts, reviews = cycle_facts(delayed={"task_id": "task-baseline"})
    records, _ = build_records(attempts, reviews, salt=SALT)
    assert phases(records)["delayed_transfer"]["previously_exposed"] is True


def test_topic_closed_on_the_first_attempt_yields_a_passing_baseline():
    """No training happened; the instrument must see baseline_at_ceiling."""
    review_id = "review-1"
    head = attempt(attempt_id="a1", mission_id="m1", evidence_id="e1", submitted_at=DAY1)
    delayed = attempt(
        task_id="task-delayed", attempt_id="a3", mission_id="m3", evidence_id="e3",
        submitted_at=DAY10, mission_source_ref=f"daily:review:{review_id}",
    )
    review = ReviewFact(
        review_id=review_id, student_id=STUDENT, topic_id=TOPIC,
        due_date=date(2026, 3, 9), source_evidence_id="e1",
    )
    records, summary = build_records([head, delayed], [review], salt=SALT)

    assert summary["cycles_emitted"] == 1
    assert phases(records)["baseline"]["rubric_status"] == "pass"


def test_plus_thirty_card_is_exported_and_bucketed_separately():
    attempts, reviews = cycle_facts(due_date=date(2026, 4, 3))
    _, summary = build_records(attempts, reviews, salt=SALT)
    assert summary["scheduled_windows"] == {"scheduled_plus_30": 1}
    assert summary["cycles_emitted"] == 1


@pytest.mark.parametrize(
    "mutate, reason",
    [
        ({"source_evidence_id": None}, "review_without_source_evidence"),
        ({"source_evidence_id": "missing"}, "head_evidence_not_found"),
    ],
)
def test_unlinkable_review_cards_are_counted_not_guessed(mutate, reason):
    attempts, reviews = cycle_facts()
    review = ReviewFact(**{**reviews[0].__dict__, **mutate})
    records, summary = build_records(attempts, [review], salt=SALT)

    assert records == []
    assert summary["skipped"] == {reason: 1}


def test_failed_head_evidence_cannot_open_a_cycle():
    attempts, reviews = cycle_facts()
    attempts[1] = attempt(
        task_id="task-immediate", attempt_id="a2", mission_id="m2", evidence_id="e2",
        submitted_at=DAY3, evidence_status="failed", score_percent=50.0,
    )
    records, summary = build_records(attempts, reviews, salt=SALT)
    assert records == []
    assert summary["skipped"] == {"head_evidence_not_passed": 1}


def test_a_review_drill_cannot_father_another_cycle():
    attempts, reviews = cycle_facts()
    attempts[1] = attempt(
        task_id="task-immediate", attempt_id="a2", mission_id="m2", evidence_id="e2",
        submitted_at=DAY3, mission_source_ref="daily:review:earlier",
    )
    records, summary = build_records(attempts, reviews, salt=SALT)
    assert records == []
    assert summary["skipped"] == {"head_is_review_drill": 1}


def test_unattempted_drill_is_pending_not_incomplete():
    attempts, reviews = cycle_facts()
    records, summary = build_records(attempts[:2], reviews, salt=SALT)
    assert records == []
    assert summary["skipped"] == {"drill_not_attempted_yet": 1}


def test_retried_drill_is_not_one_independent_measurement():
    attempts, reviews = cycle_facts()
    retry = attempt(
        task_id="task-delayed", attempt_id="a4", mission_id="m3", evidence_id="e4",
        submitted_at=DAY10 + timedelta(hours=1),
        mission_source_ref="daily:review:review-1",
    )
    records, summary = build_records([*attempts, retry], reviews, salt=SALT)
    assert records == []
    assert summary["skipped"] == {"drill_multiple_attempts": 1}


def test_missing_task_number_blocks_the_equivalence_claim():
    attempts, reviews = cycle_facts(delayed={"task_number": None})
    records, summary = build_records(attempts, reviews, salt=SALT)
    assert records == []
    assert summary["skipped"] == {"task_number_missing": 1}


def test_attempt_without_evidence_is_skipped():
    attempts, reviews = cycle_facts(delayed={"evidence_id": None, "evidence_status": None})
    records, summary = build_records(attempts, reviews, salt=SALT)
    assert records == []
    assert summary["skipped"] == {"phase_without_evidence": 1}


# --- field mapping --------------------------------------------------------- #


@pytest.mark.parametrize(
    "mode, expected", [("clean_sheet", "clean_sheet"), ("with_hint", "with_hint"),
                       ("unknown", "unknown"), ("weird", "unknown")]
)
def test_attempt_mode_is_carried_and_never_upgraded(mode, expected):
    attempts, reviews = cycle_facts(delayed={"attempt_mode": mode})
    records, _ = build_records(attempts, reviews, salt=SALT)
    assert phases(records)["delayed_transfer"]["attempt_mode"] == expected


@pytest.mark.parametrize(
    "model_id, expected",
    [("manual-review", "human"), ("operator-recovery", "human"),
     ("exact-answer", "deterministic"), ("qwen2.5-7b", "llm_shadow"), (None, "llm_shadow")],
)
def test_assessor_provenance_defaults_to_the_least_trusted_option(model_id, expected):
    attempts, reviews = cycle_facts(delayed={"model_id": model_id})
    records, _ = build_records(attempts, reviews, salt=SALT)
    assert phases(records)["delayed_transfer"]["assessor"] == expected


def test_needs_manual_review_is_carried_verbatim():
    attempts, reviews = cycle_facts(delayed={"evidence_status": "needs_manual_review"})
    records, _ = build_records(attempts, reviews, salt=SALT)
    assert phases(records)["delayed_transfer"]["rubric_status"] == "needs_manual_review"


def test_critical_error_is_false_until_the_tutor_declares_categories(monkeypatch):
    attempts, reviews = cycle_facts(delayed={"error_category": "odz_logic"})
    records, _ = build_records(attempts, reviews, salt=SALT)
    assert phases(records)["delayed_transfer"]["critical_error"] is False

    monkeypatch.setattr(exporter, "CRITICAL_ERROR_CATEGORIES", frozenset({"odz_logic"}))
    records, _ = build_records(attempts, reviews, salt=SALT)
    assert phases(records)["delayed_transfer"]["critical_error"] is True


# --- contract conformance -------------------------------------------------- #

CONTRACT_SCHEMA = (
    Path(__file__).resolve().parents[3] / "measurement" / "record_v0.schema.json"
)


@pytest.mark.skipif(not CONTRACT_SCHEMA.exists(), reason="portfolio contract not present")
def test_emitted_records_validate_against_the_portfolio_contract():
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(
        json.loads(CONTRACT_SCHEMA.read_text(encoding="utf-8"))
    )
    records, _ = build_records(*cycle_facts(), salt=SALT)
    for record in records:
        assert list(validator.iter_errors(record)) == []


# --- the queries, against the real schema ---------------------------------- #


def test_fetch_facts_reads_the_real_schema(session_factory):
    from app.domain.enums import (
        AiPolicy,
        AttemptKind,
        AttemptMode,
        ErrorCategory,
        EvidenceStatus,
        MissionStatus,
        ReviewStatus,
        Subject,
        TaskStatus,
    )
    from app.infrastructure.models import (
        AttemptORM,
        EvidenceORM,
        MissionORM,
        ReviewItemORM,
        TaskORM,
    )

    student_id, topic_id, task_id = uuid4(), uuid4(), uuid4()
    mission_id, attempt_id, evidence_id = uuid4(), uuid4(), uuid4()
    session = session_factory()
    session.add_all(
        [
            TaskORM(
                id=task_id, subject=Subject.MATH_PROFILE, topic_id=topic_id,
                task_number="10", statement="not exported", expected_answer="secret",
                status=TaskStatus.APPROVED, source="synthetic",
                created_at=datetime.now(UTC),
            ),
            MissionORM(
                id=mission_id, student_id=student_id, subject=Subject.MATH_PROFILE,
                topic_id=topic_id, task_id=task_id, title="t", instructions="",
                status=MissionStatus.DONE, ai_policy=AiPolicy.ATTEMPT_FIRST,
                threshold_percent=80.0, source_ref="daily:review:abc",
            ),
            AttemptORM(
                id=attempt_id, mission_id=mission_id, student_id=student_id,
                kind=AttemptKind.TEXT, mode=AttemptMode.WITH_HINT,
                answer_text="never exported", time_spent_minutes=9,
                submitted_at=DAY10,
            ),
            EvidenceORM(
                id=evidence_id, attempt_id=attempt_id, mission_id=mission_id,
                student_id=student_id, topic_id=topic_id,
                status=EvidenceStatus.PASSED, score_percent=88.0,
                error_category=ErrorCategory.NONE, feedback="never exported",
                next_action="never exported", model_id="qwen2.5-7b",
                prompt_version="p7", rubric_version="ege-v1",
                created_at=DAY10,
            ),
            ReviewItemORM(
                id=uuid4(), student_id=student_id, topic_id=topic_id,
                due_date=date(2026, 3, 18), status=ReviewStatus.DUE,
                source_evidence_id=evidence_id,
            ),
        ]
    )
    session.commit()

    attempts, reviews = fetch_facts(session)
    session.close()

    assert len(attempts) == 1 and len(reviews) == 1
    fact = attempts[0]
    assert fact.task_number == "10"
    assert fact.attempt_mode == "with_hint"
    assert fact.evidence_status == "passed"
    assert fact.threshold_percent == 80.0
    assert fact.rubric_version == "ege-v1"
    assert fact.is_review_drill is True
    # The fact carries the raw student id because hashing needs it; it never
    # carries learner-authored text, so no text can reach a record by accident.
    assert "answer_text" not in fact.__dict__ and "feedback" not in fact.__dict__

    records, summary = build_records(attempts, reviews, salt=SALT)
    assert records == [] and summary["skipped"] == {"head_is_review_drill": 1}
