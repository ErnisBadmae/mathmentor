"""Parser is the non-trivial logic (the render is verified by eye); test it.
A wrong parse would draw a wrong figure, so unknown forms must return None."""

import importlib.util

import pytest

from app.domain.figures import NEG, POS, parse_interval_answer, render_number_line


def test_parses_brackets_and_unions():
    assert parse_interval_answer("(1; 9)") == [(1.0, False, 9.0, False)]
    assert parse_interval_answer("[-2; 3]") == [(-2.0, True, 3.0, True)]
    assert parse_interval_answer("[1; 9)") == [(1.0, True, 9.0, False)]
    assert parse_interval_answer("(-∞; -2) ∪ [1; +∞)") == [
        (NEG, False, -2.0, False),
        (1.0, True, POS, False),
    ]


def test_parses_inequalities_and_comma_decimal():
    assert parse_interval_answer("x > 3") == [(3.0, False, POS, False)]
    assert parse_interval_answer("x ≤ 5") == [(NEG, False, 5.0, True)]
    assert parse_interval_answer("x >= -1,5") == [(-1.5, True, POS, False)]


def test_unparseable_answers_return_none():
    # scalar equation answers and noise -> no figure (never a wrong one)
    for s in ["5", "3,5", "-3", "", "π/3", "a = 1/4", "(1; )", "[3; 1]"]:
        assert parse_interval_answer(s) is None


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_render_returns_png_and_svg():
    png, svg = render_number_line(parse_interval_answer("(1; 9)"), "(1; 9)")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic
    assert "<svg" in svg
