"""Шаблонный генератор: ответ считается кодом и проходит формат-guard; вставка DRAFT
идемпотентна по source_ref."""

import random

from sqlalchemy import select

from app.application.use_cases import LearningService
from app.domain.enums import TaskStatus
from app.infrastructure.models import TaskORM, TopicORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts.generate_tasks import _INTERVAL_TOPICS as INTERVAL_TOPICS
from scripts.generate_tasks import (
    TEMPLATES,
    _NoReviewer,
    _verify,
    generate_for_topic,
)


def test_every_template_produces_verifiable_answer():
    # Прогоняем каждый шаблон на многих зерно-difficulty комбинациях: внутренний assert
    # шаблона не должен падать, а ответ — проходить формат-guard (_verify).
    for title, templates in TEMPLATES.items():
        is_interval = title in INTERVAL_TOPICS
        for template in templates:
            for seed in range(30):
                rng = random.Random(seed)
                difficulty = 1 + seed % 3
                statement, expected, solution = template(rng, difficulty)
                assert statement and expected and solution
                assert _verify(expected, is_interval), (title, statement, expected)


def _service(session) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), _NoReviewer())


def test_generate_for_topic_inserts_drafts(seeded_session):
    svc = _service(seeded_session)
    topic = seeded_session.scalar(
        select(TopicORM).where(TopicORM.title == "Вычисления: степени и корни")
    )
    assert topic is not None

    created = generate_for_topic(svc, topic, count=5, seed=0)

    assert len(created) == 5
    rows = seeded_session.scalars(select(TaskORM).where(TaskORM.topic_id == topic.id)).all()
    gen = [t for t in rows if t.source == "generated"]
    assert len(gen) == 5
    assert all(t.status == TaskStatus.DRAFT for t in gen)
    assert all(str(t.source_ref).startswith("gen:") for t in gen)
    assert all(t.expected_answer for t in gen)


def test_generate_for_topic_is_idempotent_on_same_seed(seeded_session):
    svc = _service(seeded_session)
    topic = seeded_session.scalar(
        select(TopicORM).where(TopicORM.title == "Делители числа (Задание 25)")
    )
    assert topic is not None

    generate_for_topic(svc, topic, count=5, seed=0)
    first = seeded_session.scalars(
        select(TaskORM).where(TaskORM.topic_id == topic.id)
    ).all()
    # повторный прогон с тем же зерном → те же условия → дедуп по source_ref, без роста
    generate_for_topic(svc, topic, count=5, seed=0)
    second = seeded_session.scalars(
        select(TaskORM).where(TaskORM.topic_id == topic.id)
    ).all()
    assert len(second) == len(first)


def test_interval_topic_answers_parse_as_intervals(seeded_session):
    svc = _service(seeded_session)
    topic = seeded_session.scalar(select(TopicORM).where(TopicORM.title == "Неравенства"))
    assert topic is not None

    created = generate_for_topic(svc, topic, count=6, seed=1)

    assert created
    from app.domain.figures import parse_interval_answer

    rows = seeded_session.scalars(
        select(TaskORM).where(TaskORM.topic_id == topic.id, TaskORM.source == "generated")
    ).all()
    assert all(parse_interval_answer(t.expected_answer) is not None for t in rows)
