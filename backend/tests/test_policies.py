from datetime import date

from app.domain.enums import AttemptKind, AttemptMode, EvidenceStatus, ReviewStatus
from app.domain.policies import affects_clean_sheet, clean_sheet_ratio, evidence_status, is_topic_closed, review_due_dates, review_result_to_status


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
