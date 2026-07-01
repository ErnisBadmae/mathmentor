"""Parser is the non-trivial logic (the render is verified by eye); test it.
A wrong parse would draw a wrong figure, so unknown forms must return None."""

import importlib.util

import pytest

from app.domain.figures import NEG, POS, parse_interval_answer, parse_interval_answer_from_text
from app.infrastructure.figures_render import render_number_line


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


def test_from_text_clean_passthrough():
    # Clean input goes through parse_interval_answer first.
    assert parse_interval_answer_from_text("(2; 7)") == [(2.0, False, 7.0, False)]


def test_from_text_with_russian_prefix():
    assert parse_interval_answer_from_text(
        "ответ х принадлежит (-бесконечность; -2) и [1; +бесконечность)\nрешение: длинный текст"
    ) == [
        (NEG, False, -2.0, False),
        (1.0, True, POS, False),
    ]


def test_from_text_with_x_in():
    assert parse_interval_answer_from_text("x∈(-∞; 5] и [10; +∞)") == [
        (NEG, False, 5.0, True),
        (10.0, True, POS, False),
    ]


def test_from_text_with_abbrev_infinity():
    assert parse_interval_answer_from_text("ответ: (-беск; 3] [7; +беск)") == [
        (NEG, False, 3.0, True),
        (7.0, True, POS, False),
    ]


def test_from_text_full_sentence_returns_none():
    assert parse_interval_answer_from_text("полный текст без интервала, просто объяснение") is None


def test_from_text_malformed_returns_none():
    assert parse_interval_answer_from_text("(1; )") is None
    assert parse_interval_answer_from_text("[3; 1]") is None


def test_from_text_with_brief():
    assert parse_interval_answer_from_text("ответ: (0; 5]\nперевод: ...") == [(0.0, False, 5.0, True)]


def test_from_text_scalar_returns_none():
    assert parse_interval_answer_from_text("5") is None


def test_from_text_uses_last_answer_marker():
    # When "ответ" appears twice, use the LAST occurrence.
    assert parse_interval_answer_from_text(
        "решение: проверила (1; 2)\nответ: (3; 4)"
    ) == [(3.0, False, 4.0, False)]


@pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None, reason="matplotlib not installed"
)
def test_render_returns_png():
    png = render_number_line(parse_interval_answer("(1; 9)"), "(1; 9)")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic
