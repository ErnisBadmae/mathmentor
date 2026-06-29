"""Pure, leak-safe parsing of an inequality answer into intervals.

This is the *spec* half of the visualization feature and lives in the domain
because it is pure logic with no I/O and no heavy deps. The rendering half
(matplotlib) lives in ``app.infrastructure.figures_render`` — keep it out of the
domain. An answer we cannot parse returns None, so the caller shows no figure
(we never render a wrong one)."""

from __future__ import annotations

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
