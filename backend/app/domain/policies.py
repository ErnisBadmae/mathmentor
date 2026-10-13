import re
from datetime import date, timedelta
from fractions import Fraction

from app.domain.enums import (
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    ReviewStatus,
    TopicState,
)


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


_INFO_UNIT_SUFFIXES = (
    (("кбайт", "кб", "kb"), "kb"),
    (("мбайт", "мб", "mb"), "mb"),
    (("гбайт", "гб", "gb"), "gb"),
)


def _normalize_information_unit_suffix(value: str) -> str:
    for aliases, canonical in _INFO_UNIT_SUFFIXES:
        for alias in aliases:
            if value.endswith(alias):
                return value[: -len(alias)] + canonical
    return value


def normalize_answer(value: str) -> str:
    """Normalize a short exact answer for deterministic comparison: casefold, decimal
    comma -> dot, unit synonyms, and drop all whitespace. Suits numeric/short answers."""
    compact = "".join(value.strip().casefold().replace(",", ".").split())
    return _normalize_information_unit_suffix(compact)


def _as_fraction(value: str | None) -> Fraction | None:
    """Скаляр как точная дробь: '1/2','0,5','-3','2.50' → Fraction; иначе None (нечисловое/None).
    Fraction(s) парсит и дроби, и десятичные напрямую — Decimal не нужен."""
    if not value:
        return None
    s = value.strip().casefold().replace(",", ".").replace(" ", "")
    try:
        return Fraction(s)
    except (ValueError, ZeroDivisionError):
        return None


_GROUPED_INTEGER_RE = re.compile(r"^[+-]?[1-9]\d{0,2}(?:\.\d{3})+$")


def _as_grouped_integer(value: str | None) -> int | None:
    """Thousands-grouped integer: 7.776 -> 7776, but 0.667 stays decimal."""
    if not value:
        return None
    s = value.strip().replace(" ", "")
    if not _GROUPED_INTEGER_RE.fullmatch(s):
        return None
    return int(s.replace(".", ""))


def answer_is_correct(submitted: str | None, expected: str | None) -> bool:
    if not submitted or not expected:
        return False
    a, b = _as_fraction(submitted), _as_fraction(expected)
    if a is not None and b is not None:
        grouped = _as_grouped_integer(submitted)
        if grouped is not None and b.denominator == 1 and abs(b.numerator) >= 1000:
            return grouped == b.numerator
        return a == b  # 0,5 == 1/2 (детерминированно, без ИИ)
    return normalize_answer(submitted) == normalize_answer(expected)


def answer_fits_exam_blank(answer: str | None) -> bool:
    """Записывается ли эталонный ответ в бланк ЕГЭ: целое или КОНЕЧНАЯ десятичная дробь.

    Инцидент 2026-08-11: задача части 1 с эталоном ``2/3``. Ученица ответила ``0,667`` —
    верно по сути, но точное сравнение честно сказало «не равно», и в журнал ошибок ушёл
    ложный провал. Виноват контент, а не грейдер: 2/3 в бланк не записать в принципе,
    поэтому у задачи не было ни одного правильного ответа. Ослаблять ``answer_is_correct``
    нельзя — это открыло бы дорогу ложным зачётам; отсекать надо негодную задачу.

    Нечисловые ответы (интервалы, единицы вроде «768 Кбайт», текст) не трогаем — у них
    свой формат, и эта проверка про них ничего не знает."""
    fraction = _as_fraction(answer)
    if fraction is None:
        return True
    denominator = fraction.denominator
    for prime in (2, 5):  # конечная десятичная ⇔ знаменатель вида 2^a·5^b
        while denominator % prime == 0:
            denominator //= prime
    return denominator == 1


def numeric_mismatch(submitted: str | None, expected: str | None) -> bool:
    """Both values are numeric and not equivalent under exact-answer policy."""
    if answer_is_correct(submitted, expected):
        return False
    a, b = _as_fraction(submitted), _as_fraction(expected)
    return a is not None and b is not None and a != b


_DECLARED_ANSWER_RE = re.compile(r"^ответ(?=[\s:=]|$)\s*[:=]?\s*(.*)$", re.IGNORECASE)


def extract_declared_answer(text: str | None) -> str | None:
    """A learner sometimes writes a multiline solution with one explicit ``Ответ ...``
    line. Extract that declared value deterministically (no LLM, no scanning for
    arbitrary numbers). Returns None when no line is labelled or labelled lines
    disagree, so an unlabelled/ambiguous solution never grades itself."""
    if not text:
        return None
    candidates: list[str] = []
    for line in text.splitlines():
        match = _DECLARED_ANSWER_RE.match(line.strip())
        if not match:
            continue
        candidate = match.group(1).strip()
        if candidate:
            candidates.append(candidate)
    if not candidates:
        return None
    first = candidates[0]
    if any(candidate != first for candidate in candidates[1:]):
        return None
    return first


DAILY_NEW_TOPIC_QUOTA = 1


def daily_budget(open_count: int, limit: int) -> int:
    """Сколько миссий можно создать сегодня: лимит минус уже открытые carry-over.

    Долги не копим и новое не наваливаем сверх лимита."""
    return max(0, limit - open_count)


def select_daily_queue(
    open_count: int,
    due_reviews: list,
    back_to_work: list,
    new_topics: list,
    limit: int,
) -> list:
    """Порядок кандидатов дня: повторы вперёд (due → back_to_work), но ``DAILY_NEW_TOPIC_QUOTA``
    слот бюджета резервируется под новую тему.

    Возвращает ВЕСЬ упорядоченный список кандидатов, а не обрезанный по бюджету: под
    кандидата может не найтись свежей задачи, и вызывающий добирает следующего из хвоста —
    иначе день оказывается полупустым при полном банке. Резерв под новую тему нужен потому,
    что хвост просроченных повторов бывает длиннее бюджета, и без резерва новые темы не
    попадают в очередь никогда. Чистая функция, без БД."""
    budget = daily_budget(open_count, limit)
    reviews = [*due_reviews, *back_to_work]
    reserved = min(DAILY_NEW_TOPIC_QUOTA, budget, len(new_topics))
    if reserved == 0:
        return [*reviews, *new_topics]
    head = reviews[: budget - reserved]
    return [*head, *new_topics[:reserved], *reviews[len(head) :], *new_topics[reserved:]]


def describe_pick(reason: dict) -> str:
    """Презентер #1 (оператор/агент): структурный ``reason`` → компактная строка «почему».

    ``reason`` — единый источник правды из domain (только данные). Детский и родительский
    тексты, когда понадобятся, будут отдельными тонкими форматтерами над ТЕМ ЖЕ dict —
    domain при этом не меняется. LLM ни в одном из них: объяснение = честный след выбора."""
    kind = reason.get("kind")
    if kind == "due_review":
        return "повтор по расписанию (интервальное закрепление)"
    if kind == "back_to_work":
        return "вернулась в работу после проваленного повтора"
    if kind == "new_topic":
        prereqs = reason.get("prerequisites") or []
        base = "новая тема"
        if prereqs:
            base += f"; пререквизиты закрыты: {', '.join(prereqs)}"
        base += f"; доступна по фазе «{reason.get('phase')}»"
        if reason.get("error_count"):
            base += f"; прошлых ошибок: {reason['error_count']}"
        return base
    if kind == "self_pick":
        return "выбрана самой ученицей из списка тем трека"
    return "выбрана планировщиком дня"


def select_intervention_queue(
    errors_by_category: dict[ErrorCategory, int],
    *,
    min_count: int = 2,
    limit: int = 3,
) -> list[ErrorCategory]:
    """Pure selector for future repeated-error interventions.

    Not wired into the product loop yet: the deterministic intervention rule is still
    frozen until weekly reviews produce enough signal. ``OTHER`` and ``NONE`` are not
    actionable categories, so they never trigger a drill by themselves.
    """
    actionable = [
        (category, count)
        for category, count in errors_by_category.items()
        if category not in (ErrorCategory.NONE, ErrorCategory.OTHER) and count >= min_count
    ]
    actionable.sort(key=lambda item: (-item[1], item[0].value))
    return [category for category, _count in actionable[: max(0, limit)]]


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
