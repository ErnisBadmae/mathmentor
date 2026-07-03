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


def parse_interval_answer_from_text(text: str | None) -> list[Interval] | None:
    """Robust interval extraction from raw Telegram text that may include
    conversational prefixes/suffixes like "ответ", "х принадлежит", "решение:",
    line breaks, etc.

    Strategy:
    1. Try the existing ``parse_interval_answer`` first (exact clean input).
    2. If text contains an "ответ" marker, parse only the substring after the
        last "ответ"/"ответ:" marker — the student's answer is the last
        occurrence.
    3. If no "ответ" marker, extract bracket/paren cluster(s) from the whole
        text, join adjacent ones with ∪ for union parsing.
    4. Support common Russian variants: х принадлежит, x∈, бесконечность, беск.

    Returns None when no interval can be recovered (caller shows no figure).
    """
    if not text:
        return None

    # Fast-path: clean input already handled by the strict parser.
    result = parse_interval_answer(text)
    if result is not None:
        return result

    # Normalise common Russian infinity variants so the bracket search sees
    # consistent tokens.
    for v in ("бесконечность", "беск", "беск.", "∞", "inf"):
        text = text.replace(v, "∞")

    # If an "ответ" marker exists, take only the substring after the last one.
    answer_marker_positions = []
    for marker in ("ответ:", "ответ ", "ответ"):
        idx = text.rfind(marker)
        if idx != -1:
            answer_marker_positions.append(idx)
    if answer_marker_positions:
        text = text[max(answer_marker_positions) + len("ответ"):].strip()

    # If no answer marker, strip everything after section keywords (solution,
    # explanation, etc.) so we don't accidentally parse numbers from the
    # solution text.
    if not answer_marker_positions:
        for kw in ("\nреш", "\nответ", "\nперев", "\nпокаж", "\nпровер"):
            idx = text.find(kw)
            if idx != -1:
                text = text[:idx]

        # Strip "решение:", "x=", "х=" prefixes.
        for kw in ("решение:", "решение", "x=", "х="):
            text = text.replace(kw, " ").replace("  ", " ").strip()

    import re

    # Find all bracket/paren groups that contain a semicolon (interval hallmark).
    single = re.findall(r'[\(\[][^()\[\]]*;[^()\[\]]*[\)\]]', text)
    if not single:
        return None

    # Join adjacent bracket groups separated by "и" or just whitespace to form
    # unions: e.g. "(-∞; -2) и [1; +∞)" -> "(-∞; -2) ∪ [1; +∞)".
    joined = []
    for s in single:
        if joined:
            joined.append(" ∪ ")
        joined.append(s)

    combined = "".join(joined)
    parsed = parse_interval_answer(combined)
    if parsed is not None:
        return parsed

    # Fallback: try each individual candidate.
    for cand in single:
        parsed = parse_interval_answer(cand)
        if parsed is not None:
            return parsed

    return None
