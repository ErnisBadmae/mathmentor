"""Unit tests for the golden-gate evaluator (no live model)."""

from app.application.ports import EvidenceDraft
from app.domain.enums import AttemptKind, ErrorCategory, EvidenceStatus, Subject
from scripts.llm_review_gate import (
    SCENARIOS_PATH,
    GoldenScenario,
    evaluate_review,
    load_scenarios,
    summarize,
)

SCENARIO = GoldenScenario(
    name="sign_transfer",
    tier="mainline",
    subject=Subject.MATH_PROFILE,
    kind=AttemptKind.TEXT,
    expected_category=ErrorCategory.SIGN_TRANSFER,
    must_contain_any=["знак"],
)


def _draft(
    category: ErrorCategory,
    feedback: str = "Перепутан знак при переносе",
    status=None,
) -> EvidenceDraft:
    return EvidenceDraft(
        score_percent=50,
        error_category=category,
        feedback=feedback,
        next_action="next",
        model_id="test-model",
        prompt_version="test",
        rubric_version="test",
        status=status,
    )


def test_correct_category_passes():
    result = evaluate_review(SCENARIO, _draft(ErrorCategory.SIGN_TRANSFER))
    assert result.passed


def test_wrong_category_fails():
    result = evaluate_review(SCENARIO, _draft(ErrorCategory.ARITHMETIC))
    assert not result.passed
    assert any("категория" in f for f in result.failures)


def test_manual_review_is_fail_closed():
    result = evaluate_review(
        SCENARIO,
        _draft(ErrorCategory.SIGN_TRANSFER, status=EvidenceStatus.NEEDS_MANUAL_REVIEW),
    )
    assert not result.passed
    assert any("fail-closed" in f for f in result.failures)


def test_empty_feedback_is_silent_fallback():
    result = evaluate_review(SCENARIO, _draft(ErrorCategory.SIGN_TRANSFER, feedback=""))
    assert not result.passed
    assert any("silent-fallback" in f for f in result.failures)


def test_missing_marker_fails():
    draft = _draft(ErrorCategory.SIGN_TRANSFER, feedback="ошибка в вычислениях")
    result = evaluate_review(SCENARIO, draft)
    assert not result.passed
    assert any("маркер" in f for f in result.failures)


def test_summarize_red_when_mainline_fails():
    results = [
        evaluate_review(SCENARIO, _draft(ErrorCategory.ARITHMETIC)),  # mainline fail
    ]
    report = summarize(results)
    assert report["gate_green"] is False
    assert report["mainline_failed"] == 1


def test_summarize_green_when_all_mainline_pass():
    report = summarize([evaluate_review(SCENARIO, _draft(ErrorCategory.SIGN_TRANSFER))])
    assert report["gate_green"] is True


def test_golden_scenarios_file_loads():
    scenarios = load_scenarios(SCENARIOS_PATH)
    assert scenarios
    names = {s.name for s in scenarios}
    assert {"sign_transfer", "probability_double_count", "odz_logic"} <= names
    assert any(s.tier == "mainline" for s in scenarios)
