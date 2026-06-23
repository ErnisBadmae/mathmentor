"""Срез по выбранной теме: пул ограничен темой, диагностика подписана темой."""

from uuid import uuid4

from sqlalchemy import select

from app.application.use_cases import LearningService, RuleBasedReviewer
from app.domain.enums import Subject
from app.infrastructure.models import StudyLogEntryORM, TaskORM, TopicORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts import seed as seed_module

STUDENT = seed_module.DEMO_STUDENT_ID


def service(session) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer())


def _topic_with_tasks(svc, session, title, answers) -> TopicORM:
    topic = TopicORM(
        id=uuid4(), subject=Subject.MATH_PROFILE, title=title, spec_year=2026, task_number=None
    )
    session.add(topic)
    session.commit()
    for i, answer in enumerate(answers):
        url = f"https://example.org/slice/{topic.id}/{i}"
        task = svc.add_task(
            {
                "subject": Subject.MATH_PROFILE,
                "statement": f"{title} задача {i}",
                "expected_answer": answer,
                "source": "official",
                "source_url": url,
                "source_ref": url,
                "topic_id": topic.id,
            }
        )
        svc.approve_task(task.id)
    return topic


def test_draw_slice_scoped_to_one_topic(seeded_session):
    svc = service(seeded_session)
    topic_a = _topic_with_tasks(svc, seeded_session, "Тема A", ["1", "2", "3"])
    _topic_with_tasks(svc, seeded_session, "Тема B", ["4", "5"])

    items = svc.draw_slice(Subject.MATH_PROFILE, 10, topic_id=topic_a.id)

    assert len(items) == 3  # только пул темы A
    for item in items:
        task = seeded_session.get(TaskORM, item["task_id"])
        assert task.topic_id == topic_a.id
        assert "expected_answer" not in item  # ключ не утекает


def test_grade_slice_labels_diagnostic_by_topic(seeded_session):
    svc = service(seeded_session)
    topic = _topic_with_tasks(svc, seeded_session, "Вероятность сложение", ["5", "6"])
    items = svc.draw_slice(Subject.MATH_PROFILE, 10, topic_id=topic.id)

    svc.grade_slice(
        STUDENT,
        Subject.MATH_PROFILE,
        [{"task_id": item["task_id"], "answer_text": "0"} for item in items],
    )

    labels = [e.topic_title for e in seeded_session.scalars(select(StudyLogEntryORM)).all()]
    assert "Срез — Вероятность сложение" in labels
