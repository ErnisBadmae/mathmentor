"""Experimental: a number-line figure built deterministically from a task's
KNOWN answer string. The figure is a pure function of the bank answer, so it is
correct by construction — no LLM in the drawing loop. An answer we cannot parse
returns None (no figure is shown — we never render a wrong one).

ponytail: matplotlib is the renderer for this experiment (it also gives us SVG
for the web and PNG for Telegram from one call). A number line is simple enough
to emit as hand-rolled SVG without the dependency if this feature graduates.
"""

from __future__ import annotations

import io
import math
import re

NEG, POS = float("-inf"), float("inf")
# (lo, lo_closed, hi, hi_closed); lo/hi may be ±inf (then *_closed is ignored)
Interval = tuple[float, bool, float, bool]


def _num(tok: str) -> float | None:
    t = tok.strip().replace("−", "-").replace(" ", "").replace(",", ".")
    if t in ("-∞", "-inf", "-oo"):
        return NEG
    if t in ("+∞", "∞", "+inf", "oo", "+oo"):
        return POS
    try:
        return float(t)
    except ValueError:
        return None


def _piece(part: str) -> Interval | None:
    part = part.strip()
    m = re.match(r"^([\(\[])(.+?);(.+?)([\)\]])$", part)
    if m:
        lo, hi = _num(m.group(2)), _num(m.group(3))
        if lo is None or hi is None or lo > hi:
            return None
        return (lo, m.group(1) == "[", hi, m.group(4) == "]")
    q = part.replace(" ", "").replace("≥", ">=").replace("≤", "<=")
    m = re.match(r"^x(>=|<=|>|<)(.+)$", q)
    if m:
        v = _num(m.group(2))
        if v is None or abs(v) == POS:
            return None
        op = m.group(1)
        return {
            ">": (v, False, POS, False),
            ">=": (v, True, POS, False),
            "<": (NEG, False, v, False),
            "<=": (NEG, False, v, True),
        }[op]
    return None


def parse_interval_answer(answer: str | None) -> list[Interval] | None:
    """Parse EGE inequality answers ('x > 3', '(1; 9)', '[-2; 3]',
    '(-∞; -2) ∪ [1; +∞)') into intervals. Returns None for anything we don't
    recognise (e.g. a scalar equation answer) so the caller shows no figure."""
    if not answer:
        return None
    s = answer.strip().replace("−", "-").replace("x∈", "").replace("x ∈", "").strip()
    out: list[Interval] = []
    for part in s.split("∪"):
        iv = _piece(part)
        if iv is None:
            return None  # unknown form -> safe: no figure
        out.append(iv)
    return out or None


def _dot(ax, x: float, closed: bool, color: str) -> None:
    if closed:
        ax.plot(x, 0, "o", color=color, markersize=12, zorder=4)
    else:
        ax.plot(x, 0, "o", mfc="white", mec=color, mew=2.2, markersize=12, zorder=4)


def render_number_line(intervals: list[Interval], label: str) -> tuple[bytes, str]:
    """Render intervals as a number line. Returns (png_bytes, svg_text)."""
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

    png = io.BytesIO()
    svg = io.StringIO()
    fig.savefig(png, format="png", dpi=130, bbox_inches="tight")
    fig.savefig(svg, format="svg", bbox_inches="tight")
    plt.close(fig)
    return png.getvalue(), svg.getvalue()
