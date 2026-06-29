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


def _dot(ax, x: float, closed: bool, color: str) -> None:
    if closed:
        ax.plot(x, 0, "o", color=color, markersize=12, zorder=4)
    else:
        ax.plot(x, 0, "o", mfc="white", mec=color, mew=2.2, markersize=12, zorder=4)


def render_number_line(intervals: list[Interval], label: str) -> bytes:
    """Render intervals as a number line and return PNG bytes."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    finite = [x for iv in intervals for x in (iv[0], iv[2]) if abs(x) != POS]
    if finite:
        lo, hi = min(finite), max(finite)
        pad = max((hi - lo) * 0.35, 1.5)
        xmin, xmax = lo - pad, hi + pad
    else:
        xmin, xmax = -5.0, 5.0

    fig, ax = plt.subplots(figsize=(8, 1.7))
    ax.annotate("", xy=(xmax, 0), xytext=(xmin, 0),
                arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#333"))
    for t in range(math.ceil(xmin), math.floor(xmax) + 1):
        ax.plot([t, t], [-0.07, 0.07], color="#bbb", lw=1, zorder=1)
        ax.text(t, -0.22, str(t), ha="center", va="top", fontsize=9, color="#888")

    color = "#2563eb"
    for lo, lc, hi, hc in intervals:
        a = xmin if lo == NEG else lo
        b = xmax if hi == POS else hi
        ax.plot([a, b], [0, 0], color=color, lw=6, solid_capstyle="butt", zorder=3)
        if lo != NEG:
            _dot(ax, lo, lc, color)
        if hi != POS:
            _dot(ax, hi, hc, color)

    ax.set_xlim(xmin - 0.3, xmax + 0.3)
    ax.set_ylim(-0.55, 0.55)
    ax.axis("off")
    ax.set_title(f"Решение: {label}", fontsize=13)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
