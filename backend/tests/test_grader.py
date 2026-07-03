"""Политика оценки короткого ответа (exact-авторитет + ИИ) и аудит record_slice."""

import asyncio
from uuid import uuid4

from sqlalchemy import select

from app.application.ports import AiAssessment
from app.application.use_cases import ExactOnlyJudge, LearningService, RuleBasedReviewer
from app.domain.enums import Subject
from app.domain.policies import answer_is_correct, numeric_mismatch
from app.infrastructure.models import StudyLogEntryORM, TopicORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts import seed as seed_module

STUDENT = seed_module.DEMO_STUDENT_ID


class MockJudge:
    """ИИ-судья с заданным мнением (для проверки политики в сервисе)."""

    def __init__(
        self, equivalent: bool, feedback: str = "подсказка", extracted: str | None = None
    ) -> None:
        self._equivalent = equivalent
        self._feedback = feedback
        self._extracted = extracted

    async def assess(self, statement, correct_answer, student_answer):
        return AiAssessment(
            self._equivalent, self._extracted, self._feedback, "mock-model", "p1", "r1"
        )


def _svc(session, judge) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer(), judge=judge)


def _grade(session, judge, key, answer, statement="2x=10, x=?"):
    return asyncio.run(_svc(session, judge)._grade_answer(statement, key, answer))


def test_exact_correct_is_authoritative_over_ai(seeded_session):
    # exact верно, но ИИ говорит «не эквивалентно» → всё равно верно + безопасный фидбек
    judgment = _grade(seeded_session, MockJudge(equivalent=False, feedback="ерунда"), "5", "5")
    assert judgment.correct is True
    assert judgment.grading_method == "exact"
    assert judgment.feedback == "Верно."  # противоречащий ИИ-текст заменён безопасным


def test_exact_miss_ai_equivalent_accepts_with_provenance(seeded_session):
    # нечисловая эквивалентность (интервал vs неравенство) — здесь ИИ-мост реально нужен
    judgment = _grade(seeded_session, MockJudge(True, "то же множество"), "(2;+∞)", "x>2")
    assert judgment.correct is True
    assert judgment.grading_method == "llm_equivalent"
    assert judgment.model_id == "mock-model" and judgment.prompt_version == "p1"


def test_exact_miss_ai_rejects(seeded_session):
    judgment = _grade(seeded_session, MockJudge(False, "не то"), "0.5", "7")
    assert judgment.correct is False
    assert judgment.grading_method == "llm_rejected"


def test_exact_only_judge_is_deterministic_fail_open(seeded_session):
    # без ИИ числовая эквивалентность ловится точно (Fraction), нечисловая — нет
    assert _grade(seeded_session, ExactOnlyJudge(), "0.5", "1/2").correct is True
    assert _grade(seeded_session, ExactOnlyJudge(), "(2;+∞)", "x>2").correct is False
    norm = _grade(seeded_session, ExactOnlyJudge(), "0.5", "0,5")
    assert norm.correct is True and norm.grading_method == "exact"


def test_sanitize_strips_leaked_key(seeded_session):
    judgment = _grade(seeded_session, MockJudge(False, "смотри ответ это 0.5 рядом"), "0.5", "7")
    assert "0.5" not in judgment.feedback  # утёкший эталон замаскирован
    assert "рядом" in judgment.feedback  # но разбор сохранён, не затёрт целиком


def test_correct_feedback_not_contradicted(seeded_session):
    # регресс: верный ответ не превращается в противоречивое «Близко — проверь ещё раз.»
    judge = MockJudge(equivalent=True, feedback="Верно, 0.5 — правильно")
    judgment = _grade(seeded_session, judge, "0.5", "0.5")
    assert judgment.correct is True
    assert judgment.feedback != "Близко — проверь ещё раз."
    assert "правильно" in judgment.feedback  # разбор сохранён (эталон замаскирован)


def test_ai_cannot_override_numeric_mismatch(seeded_session):
    # ИИ говорит «эквивалентно» и даже «извлёк» эталон, но сырое число доказуемо ≠ ключу
    judge = MockJudge(equivalent=True, feedback="ок", extracted="2/3")
    judgment = _grade(seeded_session, judge, "2/3", "0,667")
    assert judgment.correct is False
    assert judgment.grading_method == "llm_rejected"


def test_grouped_integer_answer_is_not_numeric_mismatch(seeded_session):
    assert answer_is_correct("7.776", "7776") is True
    assert numeric_mismatch("7.776", "7776") is False
    assert _grade(seeded_session, ExactOnlyJudge(), "7776", "7.776").correct is True


def test_decimal_approximation_still_not_treated_as_thousands(seeded_session):
    assert answer_is_correct("0.667", "667") is False
    assert answer_is_correct("0.667", "2/3") is False
    assert numeric_mismatch("0.667", "2/3") is True


def test_show_work_grounds_verdict_on_extracted_answer(seeded_session):
    # ученик прислал ход решения; сырой текст ≠ ключу, но ИИ извлёк финальный ответ "12"
    judge = MockJudge(equivalent=True, feedback="метод ок", extracted="12")
    judgment = _grade(seeded_session, judge, "12", "...раскрыл, получил x=12", statement="13: ...")
    assert judgment.correct is True
    # сырой текст ≠ ключу, заземление по извлечённому → llm_equivalent (для record_slice)
    assert judgment.grading_method == "llm_equivalent"


def test_show_work_flags_right_answer_wrong_method(seeded_session):
    judge = MockJudge(
        equivalent=True, feedback="⚠️ ответ верный, но метод неверный", extracted="12"
    )
    judgment = _grade(seeded_session, judge, "12", "угадал, написал 12", statement="13: ...")
    assert judgment.correct is True  # вердикт по финальному ответу (заземлён)
    assert "метод" in judgment.feedback  # но ход помечен как неверный


def _two_tasks(session):
    svc = _svc(session, ExactOnlyJudge())
    topic = TopicORM(
        id=uuid4(), subject=Subject.MATH_PROFILE, title="Грейдер тема", spec_year=2026,
        task_number=None,
    )
    session.add(topic)
    session.commit()
    tasks = []
    for i, answer in enumerate(["5", "6"]):
        url = f"https://example.org/grader/{topic.id}/{i}"
        task = svc.add_task(
            {
                "subject": Subject.MATH_PROFILE,
                "statement": f"задача {i}",
                "expected_answer": answer,
                "source": "official",
                "source_url": url,
                "source_ref": url,
                "topic_id": topic.id,
            }
        )
        svc.approve_task(task.id)
        tasks.append(task)
    return tasks


def test_record_slice_reverifies_exact_and_persists_details(seeded_session):
    t1, t2 = _two_tasks(seeded_session)
    svc = _svc(seeded_session, ExactOnlyJudge())
    judged = [
        # exact совпадает ("5"), но grading_method врёт «llm_rejected» → re-verify exact → верно
        {"task_id": t1.id, "answer_text": "5", "grading_method": "llm_rejected",
         "feedback": "x", "model_id": None, "prompt_version": None, "rubric_version": None},
        # exact мимо, но доверяем флагу llm_equivalent (server-produced) → верно
        {"task_id": t2.id, "answer_text": "мимо", "grading_method": "llm_equivalent",
         "feedback": "ок", "model_id": "mock-model", "prompt_version": "p1",
         "rubric_version": "r1"},
    ]

    result = svc.record_slice(STUDENT, Subject.MATH_PROFILE, judged)

    assert result["tasks_total"] == 2
    assert result["tasks_correct"] == 2  # exact-reverify + доверие флагу
    entry = seeded_session.scalars(
        select(StudyLogEntryORM).order_by(StudyLogEntryORM.occurred_on.desc())
    ).first()
    assert entry.details_json is not None and len(entry.details_json) == 2
    assert {d["grading_method"] for d in entry.details_json} == {"llm_rejected", "llm_equivalent"}


def test_record_slice_counts_extracted_correct(seeded_session):
    # «покажи ход»: сырой текст ≠ ключу, но извлечён верный финал → grading_method=llm_equivalent →
    # record_slice засчитывает верным, без ложного error-event (регресс Дефекта B).
    t1, _ = _two_tasks(seeded_session)  # expected_answer "5"
    svc = _svc(seeded_session, MockJudge(equivalent=True, extracted="5"))
    judged = asyncio.run(svc.judge_task_answer(t1.id, "расписала и получила x=5"))
    assert judged["correct"] is True and judged["grading_method"] == "llm_equivalent"
    result = svc.record_slice(STUDENT, Subject.MATH_PROFILE, [judged])
    assert result["tasks_correct"] == 1


def test_weekly_digest_uses_existing_learning_events(seeded_session):
    t1, _ = _two_tasks(seeded_session)
    svc = _svc(seeded_session, ExactOnlyJudge())
    svc.record_slice(
        STUDENT,
        Subject.MATH_PROFILE,
        [
            {
                "task_id": t1.id,
                "answer_text": "0",
                "grading_method": "llm_rejected",
                "feedback": "wrong",
                "model_id": None,
                "prompt_version": None,
                "rubric_version": None,
            }
        ],
    )

    digest = svc.weekly_digest(STUDENT)

    assert digest["period"]["days"] == 7
    assert digest["diagnostics"]["count"] >= 1
    assert digest["diagnostics"]["captured"] >= 1
    assert digest["errors"]["count"] >= 1
    assert digest["manual_reviews_pending"] >= 0
