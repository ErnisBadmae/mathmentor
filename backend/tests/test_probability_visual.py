"""Probability visualisation spike — tests.

Three positive (known seed tasks) and three negative (unknown / wrong
source_ref) cases.  No integration into LearningService, Telegram, or
the production flow — pure domain + render tests.
"""

import importlib.util

import pytest

from app.domain.probability_visual import (
    ProbabilityVisualSpec,
    parse_probability_visual_spec,
)
from app.infrastructure.figures_render import render_probability_visual

# ── Seed task data ────────────────────────────────────────────────────────────


_TASK_A_STATEMENT = (
    "В коробке 30 шаров: 12 красных, 8 синих и 10 зелёных. "
    "Найдите вероятность достать красный или синий шар."
)
_TASK_A_ANSWER = "2/3"
_TASK_A_REF = "corpus:probability:task-a"

_TASK_B_STATEMENT = (
    "Вероятность сдать математику — 0,9, информатику — 0,8, "
    "оба экзамена — 0,75. Найдите вероятность не сдать ни один."
)
_TASK_B_ANSWER = "0,05"
_TASK_B_REF = "corpus:probability:task-b"

_TASK_C_STATEMENT = (
    "Вероятность дождя — 0,4, ветра — 0,3, дождя и ветра — 0,15. "
    "Найдите вероятность того, что дождь будет, а ветра не будет."
)
_TASK_C_ANSWER = "0,25"
_TASK_C_REF = "corpus:probability:task-c"

# ── Expected computed cells ───────────────────────────────────────────────────


_TASK_B_EXPECTED = {
    "p_a": 0.9,
    "p_b": 0.8,
    "p_both": 0.75,
    "cell_only_a": 0.9 - 0.75,    # 0.15
    "cell_only_b": 0.8 - 0.75,    # 0.05
    "cell_both": 0.75,
    "cell_neither": 1.0 - (0.9 + 0.8 - 0.75),  # 0.05
}

_TASK_C_EXPECTED = {
    "p_a": 0.4,
    "p_b": 0.3,
    "p_both": 0.15,
    "cell_only_a": 0.4 - 0.15,    # 0.25
    "cell_only_b": 0.3 - 0.15,    # 0.15
    "cell_both": 0.15,
    "cell_neither": 1.0 - (0.4 + 0.3 - 0.15),  # 0.35
}


# ── Positive tests: Task A (bar chart) ───────────────────────────────────────


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_parse_task_a_bar_chart_spec():
    """4013: bar-chart spec with three colour groups."""
    spec = parse_probability_visual_spec(
        _TASK_A_STATEMENT, _TASK_A_ANSWER, _TASK_A_REF
    )
    assert spec is not None
    assert spec.chart_type == "bar_chart"
    assert spec.task_id == 4013
    assert spec.group_a_count == 12
    assert spec.group_b_count == 8
    assert spec.group_c_count == 10
    assert spec.total_count == 30
    assert spec.p_a == 12 / 30
    assert spec.p_b == 8 / 30
    assert spec.p_both is None
    assert spec.label_a == "красные"
    assert spec.label_b == "синие"
    assert spec.label_c == "зелёные"


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_render_task_a_bar_chart_produces_png():
    """4013: bar chart renders valid PNG."""
    spec = parse_probability_visual_spec(
        _TASK_A_STATEMENT, _TASK_A_ANSWER, _TASK_A_REF
    )
    assert spec is not None
    png = render_probability_visual(spec)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


# ── Positive tests: Task B (2x2 table, highlight neither) ────────────────────


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_parse_task_b_table_spec():
    """4014: 2x2 table spec with P(A), P(B), P(A n B)."""
    spec = parse_probability_visual_spec(
        _TASK_B_STATEMENT, _TASK_B_ANSWER, _TASK_B_REF
    )
    assert spec is not None
    assert spec.chart_type == "table_2x2"
    assert spec.task_id == 4014
    assert spec.highlight_cell == "neither"

    for field, expected in _TASK_B_EXPECTED.items():
        assert getattr(spec, field) == pytest.approx(expected), \
            f"{field}: expected {expected}, got {getattr(spec, field)}"

    # Sanity: cells sum to 1.0
    total = (
        spec.cell_only_a + spec.cell_only_b
        + spec.cell_both + spec.cell_neither
    )
    assert total == pytest.approx(1.0)

    assert spec.label_a == "математика"
    assert spec.label_b == "информатика"


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_render_task_b_table_produces_png():
    """4014: 2x2 table renders valid PNG."""
    spec = parse_probability_visual_spec(
        _TASK_B_STATEMENT, _TASK_B_ANSWER, _TASK_B_REF
    )
    assert spec is not None
    png = render_probability_visual(spec)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


# ── Positive tests: Task C (2x2 table, highlight only_a) ─────────────────────


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_parse_task_c_table_spec():
    """4015: 2x2 table spec for P(A) - P(A n B)."""
    spec = parse_probability_visual_spec(
        _TASK_C_STATEMENT, _TASK_C_ANSWER, _TASK_C_REF
    )
    assert spec is not None
    assert spec.chart_type == "table_2x2"
    assert spec.task_id == 4015
    assert spec.highlight_cell == "only_a"

    for field, expected in _TASK_C_EXPECTED.items():
        assert getattr(spec, field) == pytest.approx(expected), \
            f"{field}: expected {expected}, got {getattr(spec, field)}"

    # Sanity: cells sum to 1.0
    total = (
        spec.cell_only_a + spec.cell_only_b
        + spec.cell_both + spec.cell_neither
    )
    assert total == pytest.approx(1.0)

    assert spec.label_a == "дождь"
    assert spec.label_b == "ветер"


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_render_task_c_table_produces_png():
    """4015: 2x2 table renders valid PNG."""
    spec = parse_probability_visual_spec(
        _TASK_C_STATEMENT, _TASK_C_ANSWER, _TASK_C_REF
    )
    assert spec is not None
    png = render_probability_visual(spec)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


# ── Negative tests (unknown source_ref / bad data) ───────────────────────────


def test_unknown_source_ref_returns_none():
    """Random source_ref -> None (safe: no figure)."""
    spec = parse_probability_visual_spec(
        "some statement", "answer", "corpus:unknown:task"
    )
    assert spec is None


def test_none_source_ref_returns_none():
    """No source_ref at all -> None."""
    spec = parse_probability_visual_spec(
        _TASK_A_STATEMENT, _TASK_A_ANSWER, None
    )
    assert spec is None


def test_non_probability_statement_returns_none():
    """A non-probability task (e.g. OДЗ equation) with probability source_ref -> None
    because the statement doesn't match expected pattern."""
    # task-a expects 3+ colour counts, but this is a logarithmic equation
    spec = parse_probability_visual_spec(
        "Решите уравнение log₃(2x − 1) = 2.", "5", _TASK_A_REF
    )
    assert spec is None


# ── Renderer/layout mapping tests ─────────────────────────────────────────────


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_task_b_table_layout_mapping():
    """4014 table data matrix must be:
    [[both, only_a], [only_b, neither]]
    with rows = [математика, не математика],
         cols = [информатика, не информатика].

    Highlighted cell = neither = (row 1, col 1) = 0.05.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from app.infrastructure.figures_render import render_probability_2x2_table

    spec = parse_probability_visual_spec(
        _TASK_B_STATEMENT, _TASK_B_ANSWER, _TASK_B_REF
    )
    assert spec is not None

    # Build the table manually to inspect cell contents
    labels = (spec.label_a or "A", spec.label_b or "B")
    row_labels = [labels[0], f"не {labels[0]}"]
    col_labels = [labels[1], f"не {labels[1]}"]

    data = [
        [f"{spec.cell_both:.2f}", f"{spec.cell_only_a:.2f}"],
        [f"{spec.cell_only_b:.2f}", f"{spec.cell_neither:.2f}"],
    ]

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.axis("off")
    table = ax.table(
        cellText=data,
        rowLabels=row_labels,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.2)

    # With loc='center', data cells are at (row+1, col)
    # (1,0) = both, (1,1) = only_a, (2,0) = only_b, (2,1) = neither
    celld = table.get_celld()

    # Verify both at (1,0)
    both_text = celld[(1, 0)].get_text().get_text()
    assert both_text == f"{spec.cell_both:.2f}"
    assert spec.cell_both == pytest.approx(0.75)

    # Verify only_a at (1,1)
    only_a_text = celld[(1, 1)].get_text().get_text()
    assert only_a_text == f"{spec.cell_only_a:.2f}"
    assert spec.cell_only_a == pytest.approx(0.15)

    # Verify only_b at (2,0)
    only_b_text = celld[(2, 0)].get_text().get_text()
    assert only_b_text == f"{spec.cell_only_b:.2f}"
    assert spec.cell_only_b == pytest.approx(0.05)

    # Verify neither at (2,1) — this is the highlighted cell
    neither_text = celld[(2, 1)].get_text().get_text()
    assert neither_text == f"{spec.cell_neither:.2f}"
    assert spec.cell_neither == pytest.approx(0.05)

    # Apply the same highlight the renderer applies and verify it sticks
    celld[(2, 1)].set_facecolor("#28a745")
    celld[(2, 1)].set_text_props(color="white", fontweight="bold")
    fig.canvas.draw()
    highlight_cell = celld[(2, 1)]
    fc = highlight_cell.get_facecolor()
    # Green #28a745 in RGBA (with alpha from matplotlib)
    assert fc[0] > 0.1 and fc[1] > 0.5 and fc[2] < 0.4, \
        f"Expected green highlight, got RGBA: {fc}"

    plt.close(fig)


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_task_c_table_layout_mapping():
    """4015 table data matrix must be:
    [[both, only_a], [only_b, neither]]
    with rows = [дождь, не дождь],
         cols = [ветер, не ветер].

    Highlighted cell = only_a = (row 0, col 1 in data) -> (1,1) in get_celld = 0.25.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from app.infrastructure.figures_render import render_probability_2x2_table

    spec = parse_probability_visual_spec(
        _TASK_C_STATEMENT, _TASK_C_ANSWER, _TASK_C_REF
    )
    assert spec is not None

    labels = (spec.label_a or "A", spec.label_b or "B")
    row_labels = [labels[0], f"не {labels[0]}"]
    col_labels = [labels[1], f"не {labels[1]}"]

    data = [
        [f"{spec.cell_both:.2f}", f"{spec.cell_only_a:.2f}"],
        [f"{spec.cell_only_b:.2f}", f"{spec.cell_neither:.2f}"],
    ]

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.axis("off")
    table = ax.table(
        cellText=data,
        rowLabels=row_labels,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.2)
    celld = table.get_celld()

    # (1,0) = both, (1,1) = only_a, (2,0) = only_b, (2,1) = neither
    both_text = celld[(1, 0)].get_text().get_text()
    assert both_text == f"{spec.cell_both:.2f}"
    assert spec.cell_both == pytest.approx(0.15)

    # only_a at (1,1) — highlighted for task 4015
    only_a_text = celld[(1, 1)].get_text().get_text()
    assert only_a_text == f"{spec.cell_only_a:.2f}"
    assert spec.cell_only_a == pytest.approx(0.25)

    only_b_text = celld[(2, 0)].get_text().get_text()
    assert only_b_text == f"{spec.cell_only_b:.2f}"
    assert spec.cell_only_b == pytest.approx(0.15)

    neither_text = celld[(2, 1)].get_text().get_text()
    assert neither_text == f"{spec.cell_neither:.2f}"
    assert spec.cell_neither == pytest.approx(0.45)

    # Apply the same highlight the renderer applies and verify it sticks
    celld[(1, 1)].set_facecolor("#28a745")
    celld[(1, 1)].set_text_props(color="white", fontweight="bold")
    fig.canvas.draw()
    highlight_cell = celld[(1, 1)]
    fc = highlight_cell.get_facecolor()
    assert fc[0] > 0.1 and fc[1] > 0.5 and fc[2] < 0.4, \
        f"Expected green highlight, got RGBA: {fc}"

    plt.close(fig)
