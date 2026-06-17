from app.infrastructure.llm import normalize_student_notation


def test_normalize_student_phone_inequality_notation():
    text = "ответ: х>_ 1 или х<_-2"

    assert normalize_student_notation(text) == "ответ: x>= 1 или x<=-2"
