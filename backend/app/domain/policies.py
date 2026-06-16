from datetime import date, timedelta

from app.domain.enums import AttemptKind, AttemptMode, EvidenceStatus, ReviewStatus


def is_topic_closed(score_percent: float, threshold_percent: float) -> bool:
    return score_percent >= threshold_percent


def evidence_status(score_percent: float, threshold_percent: float) -> EvidenceStatus:
    if is_topic_closed(score_percent, threshold_percent):
        return EvidenceStatus.PASSED
    return EvidenceStatus.FAILED


def affects_clean_sheet(kind: AttemptKind, mode: AttemptMode, passed: bool) -> bool:
    return kind == AttemptKind.CODE and mode == AttemptMode.CLEAN_SHEET and passed


def clean_sheet_ratio(total_code_attempts: int, clean_sheet_passed: int) -> float:
    if total_code_attempts <= 0:
        return 0.0
    return clean_sheet_passed / total_code_attempts


def review_due_dates(closed_at: date) -> tuple[date, date]:
    return closed_at + timedelta(days=7), closed_at + timedelta(days=30)


def review_result_to_status(passed: bool) -> ReviewStatus:
    return ReviewStatus.DONE if passed else ReviewStatus.BACK_TO_WORK
