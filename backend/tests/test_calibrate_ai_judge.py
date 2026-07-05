"""Калибровка ИИ-судьи (scripts/calibrate_ai_judge.py): pure-часть без сети и БД."""

import asyncio

from app.application.ports import AiAssessment
from scripts.calibrate_ai_judge import (
    ReplayRow,
    build_report,
    cohen_kappa,
    dedupe_rows,
    disagreement_records,
    judge_rows,
)


class ScriptedJudge:
    """Судья по сценарию: словарь answer -> equivalent|None."""

    def __init__(self, verdicts: dict[str, bool | None]):
        self._verdicts = verdicts

    async def assess(self, statement, correct_answer, student_answer):
        verdict = self._verdicts.get(student_answer)
        if verdict is None:
            return None
        return AiAssessment(
            equivalent=verdict,
            extracted_answer=student_answer,
            feedback="ok",
            model_id="fake",
            prompt_version="t",
            rubric_version="t",
        )


def test_dedupe_collapses_and_weights():
    raw = [
        ("2+2?", "4", "4"),
        ("2+2?", "4", "4"),
        ("2+2?", "4", "5"),
    ]
    rows = dedupe_rows(raw)
    assert len(rows) == 2
    by_answer = {r.answer: r for r in rows}
    assert by_answer["4"].weight == 2
    assert by_answer["4"].exact is True
    assert by_answer["5"].exact is False
    assert by_answer["5"].numeric_stop is True


def test_judge_rows_marks_failures_none_not_zero():
    rows = dedupe_rows([("q", "4", "4"), ("q", "4", "abc")])
    judge = ScriptedJudge({"4": True, "abc": None})
    judged = asyncio.run(judge_rows(rows, judge))
    labels = {r.answer: r.judge_label for r in judged}
    assert labels["4"] == 1
    assert labels["abc"] is None


def test_build_report_confusion_and_failures():
    rows = [
        ReplayRow("q", "4", "4", 1, exact=True, numeric_stop=False, judge_label=1),  # tp
        ReplayRow("q", "4", "0.5", 1, exact=False, numeric_stop=True, judge_label=1),  # fp
        ReplayRow("q", "4", "4.0", 1, exact=True, numeric_stop=False, judge_label=0),  # fn
        ReplayRow("q", "4", "7", 1, exact=False, numeric_stop=True, judge_label=0),  # tn
        ReplayRow("q", "4", "x", 1, exact=False, numeric_stop=False, judge_label=None),
    ]
    report = build_report(rows, total_attempts=9)
    assert report["confusion"] == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}
    assert report["compared"] == 4
    assert report["judge_failures"] == 1
    assert report["total_attempts"] == 9
    assert report["judge_rescues_to_review"] == 1
    assert report["judge_rejects_of_correct"] == 1


def test_kappa_matches_expert_agent_reference():
    # Та же референс-точка, что в каноническом источнике: po=0.7, pe=0.5 -> 0.4
    assert abs(cohen_kappa(tp=20, fp=5, fn=10, tn=15) - 0.4) < 1e-9
    assert cohen_kappa(tp=10, fp=0, fn=0, tn=10) == 1.0
    assert cohen_kappa(tp=5, fp=0, fn=0, tn=0) is None


def test_disagreements_only_and_shape():
    rows = [
        ReplayRow("q", "4", "4", 2, exact=True, numeric_stop=False, judge_label=1),  # agree
        ReplayRow("q", "1/2", "0.5", 1, exact=False, numeric_stop=False, judge_label=1),
        ReplayRow("q", "4", "4,0", 3, exact=True, numeric_stop=False, judge_label=0),
        ReplayRow("q", "4", "x", 1, exact=False, numeric_stop=False, judge_label=None),
    ]
    records = disagreement_records(rows)
    kinds = sorted(r["kind"] for r in records)
    assert kinds == ["judge_reject", "judge_rescue"]
    rescue = next(r for r in records if r["kind"] == "judge_rescue")
    assert rescue["answer"] == "0.5"
    assert rescue["human_verdict"] is None
