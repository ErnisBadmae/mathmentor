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

from app.domain.figures import NEG, POS, Interval


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
