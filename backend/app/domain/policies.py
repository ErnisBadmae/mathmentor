from datetime import date, timedelta

from app.domain.enums import AttemptKind, AttemptMode, EvidenceStatus, ReviewStatus, TopicState


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


# §11: a topic diagnostic (topic_check) creates evidence/error/review work but must NOT
# move current_score; only exam-like signals (baseline, weekly/exam variants, exam-like
# slices, manual guardian scores) do. Diagnostics are the one score-event kind that is
# explicitly non-moving, so a deny-list keeps imported/seeded kinds moving unchanged.
NON_SCORING_SCORE_EVENT_KINDS = frozenset({"topic_check"})


def score_event_moves_score(kind: str) -> bool:
    return kind not in NON_SCORING_SCORE_EVENT_KINDS


def normalize_answer(value: str) -> str:
    """Normalize a short exact answer for deterministic comparison: casefold, decimal
    comma -> dot, and drop all whitespace. Suits numeric/short math answers."""
    return "".join(value.strip().casefold().replace(",", ".").split())


def answer_is_correct(submitted: str | None, expected: str | None) -> bool:
    if not submitted or not expected:
        return False
    return normalize_answer(submitted) == normalize_answer(expected)


def select_daily_queue(
    open_count: int,
    due_reviews: list,
    back_to_work: list,
    new_topics: list,
    limit: int,
) -> list:
    """Состав дневной очереди дрилла (приоритет: due-повторы → back_to_work → новые темы).

    Уже открытые daily-миссии (``open_count``, carry-over) считаются в лимит ПЕРВЫМИ —
    долги не копим и новое не наваливаем сверх лимита. Возвращает упорядоченные ссылки на
    то, что нужно до-создать (длиной не больше остатка бюджета). Чистая функция, без БД."""
    budget = max(0, limit - open_count)
    return ([*due_reviews, *back_to_work, *new_topics])[:budget]


def compute_topic_state(
    active_missions: int,
    has_passed_evidence: bool,
    reviews_due: int,
    reviews_done: int,
    reviews_back_to_work: int,
) -> TopicState:
    """Computed topic lifecycle (REQUIREMENTS §9); state is derived, never stored.

    ``reviews_due`` counts every review card still in DUE (including future ones).
    Priority order matters: back_to_work outranks in_work because a failed review
    spawns a fresh ACTIVE mission (§8). A passed mission becomes DONE and leaves the
    active set, so in_work does not steal under_review/confirmed in the normal flow.
    """
    if reviews_back_to_work > 0:
        return TopicState.BACK_TO_WORK
    if active_missions > 0:
        return TopicState.IN_WORK
    if has_passed_evidence:
        # confirmed only when both +7/+30 cards are done and nothing is pending —
        # reviews_done >= 2, not > 0, so a single imported pass cannot confirm a topic.
        if reviews_done >= 2 and reviews_due == 0:
            return TopicState.CONFIRMED
        return TopicState.UNDER_REVIEW
    return TopicState.OPEN
