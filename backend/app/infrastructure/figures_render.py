"""Render solution figures to PNG. Infrastructure: depends on matplotlib and
does drawing/I/O, so it stays out of the domain (which holds only the pure,
leak-safe parse in ``app.domain.figures``).

ponytail: matplotlib is the experimental renderer (already proven, no Cairo pain
on Windows). A number line is simple enough for hand-rolled SVG if this feature
graduates and the image weight starts to bite.
"""

from __future__ import annotations

import io
import math
from typing import TYPE_CHECKING

from app.domain.figures import NEG, POS, Interval

if TYPE_CHECKING:
    from app.domain.probability_visual import ProbabilityVisualSpec


def _dot(ax, x: float, closed: bool, color: str, y: float) -> None:
    if closed:
        ax.plot(x, y, "o", color=color, markersize=12, zorder=4)
    else:
        ax.plot(x, y, "o", mfc="white", mec=color, mew=2.2, markersize=12, zorder=4)


def render_number_line(
    intervals: list[Interval],
    label: str,
    *,
    student_intervals: list[Interval] | None = None,
    student_label: str | None = None,
) -> bytes:
    """Render intervals as a number line and return PNG bytes.

    When *student_intervals* is provided, draw the correct solution in blue
    and the student's answer in orange on the same axis so the learner can
    compare them at a glance.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    all_intervals = list(intervals)
    if student_intervals:
        all_intervals.extend(student_intervals)
    finite = [x for iv in all_intervals for x in (iv[0], iv[2]) if abs(x) != POS]
    if finite:
        lo, hi = min(finite), max(finite)
        pad = max((hi - lo) * 0.35, 1.5)
        xmin, xmax = lo - pad, hi + pad
    else:
        xmin, xmax = -5.0, 5.0

    fig, ax = plt.subplots(figsize=(8, 2.4))
    ax.annotate("", xy=(xmax, 0), xytext=(xmin, 0),
                arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#333"))
    for t in range(math.ceil(xmin), math.floor(xmax) + 1):
        ax.plot([t, t], [-0.07, 0.07], color="#bbb", lw=1, zorder=1)
        ax.text(t, -0.22, str(t), ha="center", va="top", fontsize=9, color="#888")

    # Correct solution in blue — drawn on the lower track so student's
    # orange does not obscure it when intervals overlap.
    color = "#2563eb"
    blue_y = -0.12
    for lo, lc, hi, hc in intervals:
        a = xmin if lo == NEG else lo
        b = xmax if hi == POS else hi
        ax.plot([a, b], [blue_y, blue_y], color=color, lw=6,
                solid_capstyle="butt", zorder=3)
        if lo != NEG:
            _dot(ax, lo, lc, color, blue_y)
        if hi != POS:
            _dot(ax, hi, hc, color, blue_y)

    if student_intervals:
        orange = "#f97316"
        orange_y = 0.12
        for lo, lc, hi, hc in student_intervals:
            a = xmin if lo == NEG else lo
            b = xmax if hi == POS else hi
            ax.plot([a, b], [orange_y, orange_y], color=orange, lw=6,
                    solid_capstyle="butt", zorder=3)
            if lo != NEG:
                _dot(ax, lo, lc, orange, orange_y)
            if hi != POS:
                _dot(ax, hi, hc, orange, orange_y)

    ax.set_xlim(xmin - 0.3, xmax + 0.3)
    ax.set_ylim(-0.55, 0.75)
    ax.axis("off")
    if student_label:
        ax.set_title("Решение  |  Ответ", fontsize=13)
    else:
        ax.set_title("Решение", fontsize=13)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


# ── Probability visualisation renderers (spike) ──────────────────────────────


def render_probability_bar_chart(spec: ProbabilityVisualSpec) -> bytes:
    """Render task-4013: three disjoint colour groups as a bar chart.

    Bars for "красные" and "синие" are highlighted (darker);
    "зелёные" is muted. A line marks P(красные или синие) = sum.
    """
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    matplotlib.use("Agg")

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.set_title("Шары в коробке", fontsize=13, pad=12)

    counts = [
        (spec.group_a_count or 0, spec.label_a or "группа A", "#e74c3c", "#c0392b"),
        (spec.group_b_count or 0, spec.label_b or "группа B", "#3498db", "#2980b9"),
        (spec.group_c_count or 0, spec.label_c or "группа C", "#95a5a6", "#7f8c8d"),
    ]

    bar_width = 0.4
    x = [0.5, 1.5, 2.5]
    heights = [c[0] for c in counts]
    max_h = max(heights) if heights else 10

    # Y-axis: normalised to probability (0..1)
    total = spec.total_count or 1
    heights_norm = [h / total for h in heights]

    bars = []
    for i, (count, label, light_color, dark_color) in enumerate(counts):
        if i < 2:
            bar_color = dark_color
        else:
            bar_color = dark_color
        bar = ax.bar(x[i], heights_norm[i], bar_width, color=bar_color,
                      edgecolor="#333", linewidth=1, alpha=0.8)
        bars.append(bar)
        # Count label
        ax.text(x[i], heights_norm[i] + 0.02, str(count),
                ha="center", va="bottom", fontsize=9, color="#333")
        # X label
        ax.text(x[i], -0.04, label, ha="center", va="top", fontsize=8, color="#666")

    ax.set_ylim(0, max(heights_norm) + 0.15)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0", "0.25", "0.5", "0.75", "1"])
    ax.set_xticks(x)
    ax.set_xticklabels([])
    ax.set_ylabel("Вероятность", fontsize=9, color="#888")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def render_probability_2x2_table(spec: ProbabilityVisualSpec) -> bytes:
    """Render a 2x2 contingency table for probability tasks 4014/4015.

    Rows: A / not-A.  Columns: B / not-B.  Cells: only_a, only_b, both, neither.

    One cell is highlighted based on ``spec.highlight_cell``:

    - ``"neither"`` — task 4014: answer is the "neither" cell
    - ``"only_a"``  — task 4015: answer is the "only A" cell

    Values are formatted with Russian decimal comma for consistency.
    """
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.use("Agg")

    def _fmt(v: float) -> str:
        return f"{v:.2f}"

    labels = spec.label_a or "A", spec.label_b or "B"
    only_a = _fmt(spec.cell_only_a) if spec.cell_only_a is not None else ""
    only_b = _fmt(spec.cell_only_b) if spec.cell_only_b is not None else ""
    both = _fmt(spec.cell_both) if spec.cell_both is not None else ""
    neither = _fmt(spec.cell_neither) if spec.cell_neither is not None else ""

    row_labels = [f"{labels[0]}", f"не {labels[0]}"]
    col_labels = [f"{labels[1]}", f"не {labels[1]}"]

    # Data matrix: rows = A / not-A, cols = B / not-B
    #   A ∩ B       A \ B       = both / only_a
    #   B \ A      ~(A U B)    = only_b / neither
    data = [[both, only_a], [only_b, neither]]

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.axis("off")

    if spec.highlight_cell == "neither":
        title = f"P(ни одного) = {neither}  (1 - P(A U B))"
    elif spec.highlight_cell == "only_a":
        title = f"P({labels[0]} без {labels[1]}) = {only_a}  (P(A) - P(A n B))"
    else:
        title = f"Таблица 2x2: P({labels[0]}), P({labels[1]})"

    ax.set_title(title, fontsize=12, pad=12)

    # Build table with highlighted cell
    cell_colors = [
        ["#f0f0f0", "#f0f0f0"],  # row 0: both, only_a
        ["#f0f0f0", "#f0f0f0"],  # row 1: only_b, neither
    ]
    if spec.highlight_cell == "neither":
        cell_colors[1][1] = "#d4edda"
    elif spec.highlight_cell == "only_a":
        cell_colors[0][1] = "#d4edda"

    # cellColours must be 2D: 2 data rows x 2 cols (labels don't use it)
    colour_grid = [[cell_colors[r][c] for c in range(2)] for r in range(2)]

    table = ax.table(
        cellText=data,
        rowLabels=row_labels,
        colLabels=col_labels,
        cellColours=colour_grid,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.2)

    # Style header cells (row 0 = column labels, col -1 = row labels)
    for (r, c), cell in table.get_celld().items():
        if r == 0 or c == -1:
            cell.set_facecolor("#e8e8e8")
            cell.set_text_props(fontweight="bold")

    # Data cells (loc='center'): (1,0)=both, (1,1)=only_a, (2,0)=only_b, (2,1)=neither
    # Use set_cellprops to override cellColours for the highlight cell
    if spec.highlight_cell == "neither":
        table[(2, 1)].set_facecolor("#28a745")
        table[(2, 1)].set_text_props(color="white", fontweight="bold")
    elif spec.highlight_cell == "only_a":
        table[(1, 1)].set_facecolor("#28a745")
        table[(1, 1)].set_text_props(color="white", fontweight="bold")

    # Force redraw so set_facecolor takes effect over cellColours
    fig.canvas.draw()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def render_probability_visual(spec: ProbabilityVisualSpec) -> bytes:
    """Dispatch to the correct probability chart renderer.

    Spike: only ``"bar_chart"`` and ``"table_2x2"`` are supported.
    Unknown chart_type raises ``ValueError``.
    """
    if spec.chart_type == "bar_chart":
        return render_probability_bar_chart(spec)
    if spec.chart_type == "table_2x2":
        return render_probability_2x2_table(spec)
    raise ValueError(f"Unsupported probability chart_type: {spec.chart_type}")
