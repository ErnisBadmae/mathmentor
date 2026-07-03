"""Авто-сборщик дня (Phase 2): приоритет повторов, свежие задачи, shortage, lifecycle повторов."""

import asyncio
from datetime import date
from uuid import uuid4

from sqlalchemy import select

from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService
from app.domain.enums import (
    AiPolicy,
    AttemptKind,
    AttemptMode,
    EvidenceStatus,
    MissionStatus,
    ReviewStatus,
    Subject,
    TaskStatus,
)
from app.domain.policies import select_daily_queue
from app.infrastructure.models import MissionORM, ReviewItemORM, TaskORM, TopicORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts import seed as seed_module

STUDENT = seed_module.DEMO_STUDENT_ID
FIXED_TODAY = date(2026, 6, 23)  # внутри june_diagnostics


class BoomReviewer:
    async def review_attempt(self, _attempt: AttemptForReview) -> EvidenceDraft:
        raise AssertionError("LLM reviewer must not be called for a drill")


def service(session, monkeypatch=None) -> LearningService:
    svc = LearningService(SqlAlchemyUnitOfWork(session), BoomReviewer())
    if monkeypatch is not None:
        monkeypatch.setattr(svc, "_today", lambda: FIXED_TODAY)
    return svc


def _open_topic_with_tasks(svc, session, title, answers, order=900) -> TopicORM:
    topic = TopicORM(
        id=uuid4(),
        subject=Subject.MATH_PROFILE,
        title=title,
        spec_year=2026,
        task_number=None,
        phase="june_diagnostics",
        program_order=order,
    )
    session.add(topic)
    session.commit()
    for i, answer in enumerate(answers):
        url = f"https://example.org/dq/{topic.id}/{i}"
        task = svc.add_task(
            {
                "subject": Subject.MATH_PROFILE,
                "statement": f"Задача {i} по теме {title}",
                "expected_answer": answer,
                "source": "official",
                "source_url": url,
                "source_ref": url,
                "topic_id": topic.id,
            }
        )
        svc.approve_task(task.id)
    return topic


def _due_card(session, topic_id) -> ReviewItemORM:
    card = ReviewItemORM(
        id=uuid4(),
        student_id=STUDENT,
        topic_id=topic_id,
        due_date=date(2020, 1, 1),
        status=ReviewStatus.DUE,
    )
    session.add(card)
    session.commit()
    return card


def _submit(svc, mission_id, answer) -> dict:
    return asyncio.run(
        svc.submit_attempt(
            {
                "mission_id": mission_id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.UNKNOWN,
                "answer_text": answer,
            }
        )
    )


def test_select_daily_queue_priority_and_open_count():
    due = [{"x": "d1"}, {"x": "d2"}]
    btw = [{"x": "b1"}]
    new = [{"x": "n1"}, {"x": "n2"}]
    # open_count=1, limit=4 → budget 3 → due(2) + btw(1), new не влезает
    assert select_daily_queue(1, due, btw, new, 4) == [due[0], due[1], btw[0]]
    # бюджет исчерпан открытыми миссиями
    assert select_daily_queue(5, due, btw, new, 4) == []
    # порядок: повторы due → back_to_work → новые
    assert select_daily_queue(0, due, btw, new, 10) == [*due, *btw, *new]


def test_build_daily_queue_picks_new_topic_and_is_idempotent(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ степени", ["5", "6", "7"])

    res = svc.build_daily_queue(STUDENT, limit=5)

    assert "Дрилл: DQ степени" in [m["title"] for m in res["filled"]]
    assert res["shortage"] == []
    assert "Дрилл: DQ степени" in [d["title"] for d in svc.list_daily_drill(STUDENT)]
    # повторный сбор не плодит дубль по той же теме (open daily + тема уже не OPEN)
    svc.build_daily_queue(STUDENT, limit=5)
    missions = seeded_session.scalars(
        select(MissionORM).where(MissionORM.source_ref == f"daily:new:{topic.id}")
    ).all()
    assert len(missions) == 1


def test_build_daily_queue_reports_shortage(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ один", ["9"])  # одна задача
    task = seeded_session.scalar(select(TaskORM).where(TaskORM.topic_id == topic.id))
    # единственная задача уже назначена ученику другой миссией → свежей нет
    seeded_session.add(
        MissionORM(
            id=uuid4(),
            student_id=STUDENT,
            subject=Subject.MATH_PROFILE,
            topic_id=topic.id,
            task_id=task.id,
            title="прошлая",
            instructions="",
            status=MissionStatus.DONE,
            ai_policy=AiPolicy.ATTEMPT_FIRST,
            threshold_percent=80.0,
        )
    )
    _due_card(seeded_session, topic.id)

    res = svc.build_daily_queue(STUDENT, limit=5)

    assert topic.id in {s["topic_id"] for s in res["shortage"]}
    assert all(m["title"] != "Дрилл: DQ один" for m in res["filled"])


def test_review_drill_pass_closes_card_without_new_reviews(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ повтор", ["5", "6"])
    card = _due_card(seeded_session, topic.id)

    svc.build_daily_queue(STUDENT, limit=5)
    mission = seeded_session.scalar(
        select(MissionORM).where(MissionORM.source_ref == f"daily:review:{card.id}")
    )
    assert mission is not None
    task = seeded_session.get(TaskORM, mission.task_id)

    result = _submit(svc, mission.id, task.expected_answer)

    assert result["status"] == EvidenceStatus.PASSED
    assert seeded_session.get(ReviewItemORM, card.id).status == ReviewStatus.DONE
    # успешный повтор НЕ планирует новые +7/+30 — остаётся только исходная карточка
    cards = seeded_session.scalars(
        select(ReviewItemORM).where(ReviewItemORM.topic_id == topic.id)
    ).all()
    assert len(cards) == 1


def test_back_to_work_redrill_with_fresh_task_resolves_to_done(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ btw", ["5", "6"])
    card = _due_card(seeded_session, topic.id)

    # 1) первый повтор провален → карточка BACK_TO_WORK, дрилл DONE (не repeat)
    svc.build_daily_queue(STUDENT, limit=5)
    m1 = seeded_session.scalar(
        select(MissionORM).where(MissionORM.source_ref == f"daily:review:{card.id}")
    )
    _submit(svc, m1.id, "неверно")
    assert seeded_session.get(ReviewItemORM, card.id).status == ReviewStatus.BACK_TO_WORK
    assert seeded_session.get(MissionORM, m1.id).status == MissionStatus.DONE

    # 2) пересбор берёт BACK_TO_WORK-карточку со СВЕЖЕЙ задачей
    svc.build_daily_queue(STUDENT, limit=5)
    m2 = seeded_session.scalar(
        select(MissionORM)
        .where(MissionORM.source_ref == f"daily:review:{card.id}")
        .where(MissionORM.status.in_([MissionStatus.ACTIVE, MissionStatus.REPEAT]))
    )
    assert m2 is not None and m2.task_id != m1.task_id  # свежая задача, не та же

    # 3) успешный передрилл → карточка DONE (back_to_work транзиентен)
    task2 = seeded_session.get(TaskORM, m2.task_id)
    _submit(svc, m2.id, task2.expected_answer)
    assert seeded_session.get(ReviewItemORM, card.id).status == ReviewStatus.DONE


def test_list_approved_for_topic_excludes_assigned(seeded_session):
    svc = service(seeded_session)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ assign", ["1", "2"])
    uow = SqlAlchemyUnitOfWork(seeded_session)

    pool = uow.tasks.list_approved_for_topic(topic.id, exclude_assigned_to=STUDENT)
    assert len(pool) == 2

    seeded_session.add(
        MissionORM(
            id=uuid4(),
            student_id=STUDENT,
            subject=Subject.MATH_PROFILE,
            topic_id=topic.id,
            task_id=pool[0].id,
            title="назначена",
            instructions="",
            status=MissionStatus.ACTIVE,
            ai_policy=AiPolicy.ATTEMPT_FIRST,
            threshold_percent=80.0,
        )
    )
    seeded_session.commit()

    remaining = uow.tasks.list_approved_for_topic(topic.id, exclude_assigned_to=STUDENT)
    assert {t.id for t in remaining} == {pool[1].id}
    assert TaskStatus.APPROVED == pool[0].status  # sanity: tasks were approved
