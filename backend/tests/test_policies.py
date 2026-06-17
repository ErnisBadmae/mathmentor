from datetime import date

from app.domain.enums import AttemptKind, AttemptMode, EvidenceStatus, ReviewStatus, TopicState
from app.domain.policies import affects_clean_sheet, clean_sheet_ratio, compute_topic_state, evidence_status, is_topic_closed, review_due_dates, review_result_to_status


def test_topic_closes_at_threshold() -> None:
    assert is_topic_closed(80, 80)
    assert not is_topic_closed(79.9, 80)
    assert evidence_status(90, 80) == EvidenceStatus.PASSED
    assert evidence_status(50, 80) == EvidenceStatus.FAILED


def test_hinted_code_does_not_improve_clean_sheet() -> None:
    assert affects_clean_sheet(AttemptKind.CODE, AttemptMode.CLEAN_SHEET, passed=True)
    assert not affects_clean_sheet(AttemptKind.CODE, AttemptMode.WITH_HINT, passed=True)
    assert not affects_clean_sheet(AttemptKind.TEXT, AttemptMode.CLEAN_SHEET, passed=True)
    assert not affects_clean_sheet(AttemptKind.CODE, AttemptMode.CLEAN_SHEET, passed=False)


def test_clean_sheet_ratio() -> None:
    assert clean_sheet_ratio(0, 0) == 0
    assert clean_sheet_ratio(5, 2) == 0.4


def test_review_schedule() -> None:
    plus_7, plus_30 = review_due_dates(date(2026, 6, 1))
    assert plus_7 == date(2026, 6, 8)
    assert plus_30 == date(2026, 7, 1)
    assert review_result_to_status(True) == ReviewStatus.DONE
    assert review_result_to_status(False) == ReviewStatus.BACK_TO_WORK


def test_topic_state_open_when_no_activity() -> None:
    assert compute_topic_state(0, False, 0, 0, 0) == TopicState.OPEN


def test_topic_state_in_work_with_active_mission() -> None:
    assert compute_topic_state(1, False, 0, 0, 0) == TopicState.IN_WORK


def test_topic_state_under_review_when_passed_with_pending_cards() -> None:
    assert compute_topic_state(0, True, 2, 0, 0) == TopicState.UNDER_REVIEW
    # one card done, one still due → not confirmed yet
    assert compute_topic_state(0, True, 1, 1, 0) == TopicState.UNDER_REVIEW


def test_topic_state_confirmed_needs_both_cards_done() -> None:
    assert compute_topic_state(0, True, 0, 2, 0) == TopicState.CONFIRMED
    # a single imported pass without the second card must NOT confirm
    assert compute_topic_state(0, True, 0, 1, 0) == TopicState.UNDER_REVIEW


def test_topic_state_back_to_work_outranks_in_work() -> None:
    # a failed review spawns a fresh ACTIVE mission, yet the topic must read back_to_work
    assert compute_topic_state(1, True, 0, 1, 1) == TopicState.BACK_TO_WORK
