"""Probability visual spec parser — spike only.

This module is a **research spike**. It parses *only* three known seed
source_ref patterns into a structured ``ProbabilityVisualSpec`` and renders
them as PNG prototypes. Unknown or mismatched patterns return ``None``.

Known source_ref patterns:
- ``corpus:probability:task-a`` (4013) — bar chart of three colour groups
- ``corpus:probability:task-b`` (4014) — 2x2 table for A U B + complement
- ``corpus:probability:task-c`` (4015) — 2x2 table for A \\ B (only A)

This file does **not** touch LearningService, Telegram, DB, prompts, or
the production drill flow.
"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class ProbabilityVisualSpec:
    """Structured spec for a probability visualisation.

    The ``chart_type`` determines which renderer is used:

    - ``"bar_chart"``  — three bars for disjoint colour groups (task 4013)
    - ``"table_2x2"``  — 2x2 contingency table with one cell highlighted
      (tasks 4014, 4015)

    For ``"table_2x2"`` specs the computed cells are pre-calculated so the
    renderer and tests can assert correctness without re-computing.
    """

    chart_type: str  # "bar_chart" | "table_2x2"
    source_ref: str
    task_id: int
    p_a: float
    p_b: float
    p_both: float | None = None
    highlight_cell: str | None = None  # "neither" or "only_a"

    # Computed 2x2 cells (set for table_2x2 specs)
    cell_only_a: float | None = None
    cell_only_b: float | None = None
    cell_both: float | None = None
    cell_neither: float | None = None

    # Bar-chart fields (task 4013)
    group_a_count: int | None = None
    group_b_count: int | None = None
    group_c_count: int | None = None
    total_count: int | None = None

    label_a: str | None = None
    label_b: str | None = None
    label_c: str | None = None


# ── Patterns (source_ref -> handler) ──────────────────────────────────────────


def parse_probability_visual_spec(
    statement: str,
    expected_answer: str,
    source_ref: str | None,
) -> ProbabilityVisualSpec | None:
    """Parse a probability visualisation spec from the *known* seed tasks.

    Returns ``None`` for anything that is not an exact match to one of the
    three handled source_ref patterns.  This is intentional: the spike only
    processes tasks we have verified end-to-end.
    """
    if source_ref is None:
        return None

    handlers: dict[str, object] = {
        "corpus:probability:task-a": _parse_task_a,
        "corpus:probability:task-b": _parse_task_b,
        "corpus:probability:task-c": _parse_task_c,
    }

    handler = handlers.get(source_ref)
    if handler is None:
        return None

    try:
        return handler(statement, expected_answer, source_ref)
    except (ValueError, TypeError):
        return None


# ── Task 4013: "balls in a box" — bar chart ──────────────────────────────────


def _parse_task_a(
    statement: str, expected_answer: str, source_ref: str
) -> ProbabilityVisualSpec:
    """task-a: 'В коробке 30 шаров: 12 красных, 8 синих и 10 зелёных.'"""
    import re

    all_matches = re.findall(r"(\d+)\s+\w+", statement)
    all_ints = [int(m) for m in all_matches]

    if len(all_ints) < 4:
        raise ValueError("task-a requires at least 4 numbers (total + 3 colour groups)")

    total = all_ints[0]
    a, b, c = all_ints[1], all_ints[2], all_ints[3]

    return ProbabilityVisualSpec(
        chart_type="bar_chart",
        source_ref=source_ref,
        task_id=4013,
        p_a=a / total,
        p_b=b / total,
        p_both=None,
        group_a_count=a,
        group_b_count=b,
        group_c_count=c,
        total_count=total,
        label_a="красные",
        label_b="синие",
        label_c="зелёные",
    )


# ── Task 4014: "P(A)+P(B)-P(A n B)" — 2x2 table, highlight neither ──────────


def _parse_task_b(
    statement: str, expected_answer: str, source_ref: str
) -> ProbabilityVisualSpec:
    """task-b: 'Вероятность сдать математику — 0,9, информатику — 0,8, оба — 0,75.'"""
    p_a, p_b, p_both = _extract_probabilities(statement, min_count=3)

    # 2x2 table cells
    neither = 1.0 - (p_a + p_b - p_both)

    return ProbabilityVisualSpec(
        chart_type="table_2x2",
        source_ref=source_ref,
        task_id=4014,
        p_a=p_a,
        p_b=p_b,
        p_both=p_both,
        highlight_cell="neither",
        cell_only_a=p_a - p_both,
        cell_only_b=p_b - p_both,
        cell_both=p_both,
        cell_neither=neither,
        label_a="математика",
        label_b="информатика",
    )


# ── Task 4015: "P(A) - P(A n B)" — 2x2 table, highlight only_a ──────────────


def _parse_task_c(
    statement: str, expected_answer: str, source_ref: str
) -> ProbabilityVisualSpec:
    """task-c: 'Вероятность дождя — 0,4, ветра — 0,3, дождя и ветра — 0,15.'"""
    p_a, p_b, p_both = _extract_probabilities(statement, min_count=3)

    neither = 1.0 - (p_a + p_b - p_both)

    return ProbabilityVisualSpec(
        chart_type="table_2x2",
        source_ref=source_ref,
        task_id=4015,
        p_a=p_a,
        p_b=p_b,
        p_both=p_both,
        highlight_cell="only_a",
        cell_only_a=p_a - p_both,
        cell_only_b=p_b - p_both,
        cell_both=p_both,
        cell_neither=neither,
        label_a="дождь",
        label_b="ветер",
    )


# ── Shared helper ─────────────────────────────────────────────────────────────


def _extract_probabilities(statement: str, min_count: int = 3) -> tuple[float, float, float]:
    """Extract Russian decimal-probability values from a statement.

    Matches patterns like ``0,9`` or ``0,75`` (digit(s) + comma + digit(s)).
    Returns the first three matches as (p_a, p_b, p_both).
    """
    import re

    probs_str = re.findall(r"(\d+[,\.]\d+)", statement)
    probs_float: list[float] = []
    for p in probs_str:
        try:
            probs_float.append(float(p.replace(",", ".")))
        except ValueError:
            continue

    if len(probs_float) < min_count:
        raise ValueError(f"requires at least {min_count} probability values")

    return probs_float[0], probs_float[1], probs_float[2]
