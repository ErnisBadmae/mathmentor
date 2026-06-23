"""Политика оценки короткого ответа (exact-авторитет + ИИ) и аудит record_slice."""

import asyncio
from uuid import uuid4

from sqlalchemy import select

from app.application.ports import AiAssessment
from app.application.use_cases import ExactOnlyJudge, LearningService, RuleBasedReviewer
from app.domain.enums import Subject
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
    judgment = _grade(seeded_session, MockJudge(True, "1/2 это 0.5"), "0.5", "1/2")
    assert judgment.correct is True
    assert judgment.grading_method == "llm_equivalent"
    assert judgment.model_id == "mock-model" and judgment.prompt_version == "p1"


def test_exact_miss_ai_rejects(seeded_session):
    judgment = _grade(seeded_session, MockJudge(False, "не то"), "0.5", "7")
    assert judgment.correct is False
    assert judgment.grading_method == "llm_rejected"


def test_exact_only_judge_is_deterministic_fail_open(seeded_session):
    # без ИИ эквивалентная форма не принимается (детерминизм), но нормализация работает
    assert _grade(seeded_session, ExactOnlyJudge(), "0.5", "1/2").correct is False
    norm = _grade(seeded_session, ExactOnlyJudge(), "0.5", "0,5")
    assert norm.correct is True and norm.grading_method == "exact"


def test_sanitize_strips_leaked_key(seeded_session):
    judgment = _grade(seeded_session, MockJudge(False, "смотри ответ это 0.5 рядом"), "0.5", "7")
    assert "0.5" not in judgment.feedback  # утёкший эталон вырезан


def test_show_work_grounds_verdict_on_extracted_answer(seeded_session):
    # ученик прислал ход решения; сырой текст ≠ ключу, но ИИ извлёк финальный ответ "12"
    judge = MockJudge(equivalent=True, feedback="метод ок", extracted="12")
    judgment = _grade(seeded_session, judge, "12", "...раскрыл, получил x=12", statement="13: ...")
    assert judgment.correct is True
    assert judgment.grading_method == "exact"  # заземление на извлечённый финальный ответ


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
