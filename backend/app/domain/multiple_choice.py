"""Strict official-key grading for the historical CISIA sample."""

import re

CISIA_SOURCE = "cisia_sample"
CISIA_PREFIX = "cisia:english-tolc-i:sample-2021:q"


def choice_answer(text: str | None) -> str:
    """Require one explicit Latin A–E; never infer a choice from prose."""
    value = (text or "").strip().upper()
    match = re.fullmatch(r"(?:ОТВЕТ\s*[:=]\s*)?([A-E])[.)]?", value)
    if match is None:
        raise ValueError("Пришли одну латинскую букву A, B, C, D или E.")
    return match.group(1)


def cisia_number(source_ref: str | None) -> int | None:
    match = re.fullmatch(re.escape(CISIA_PREFIX) + r"(\d+)", source_ref or "")
    number = int(match.group(1)) if match else 0
    return number if 1 <= number <= 20 else None
