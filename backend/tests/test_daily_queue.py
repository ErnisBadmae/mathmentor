"""Авто-сборщик дня (Phase 2): приоритет повторов, свежие задачи, shortage, lifecycle повторов."""

import asyncio
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.application import use_cases
from app.application.ports import AttemptForReview, EvidenceDraft
from app.application.use_cases import LearningService
from app.domain.enums import (
    AiPolicy,
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    MissionStatus,
    ReviewStatus,
    Subject,
    TaskStatus,
)
from app.domain.policies import daily_budget, describe_pick, select_daily_queue
from app.domain.prerequisites import prerequisites_met
from app.infrastructure.models import (
    AttemptORM,
    EvidenceORM,
    MissionORM,
    ReviewItemORM,
    StudyLogEntryORM,
    TaskORM,
    TopicORM,
)
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


def _due_card(session, topic_id, due_date=date(2020, 1, 1)) -> ReviewItemORM:
    card = ReviewItemORM(
        id=uuid4(),
        student_id=STUDENT,
        topic_id=topic_id,
        due_date=due_date,
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
    # open_count=1, limit=4 → бюджет 3: два повтора + зарезервированный слот новой темы
    picks = select_daily_queue(1, due, btw, new, 4)
    assert picks[:3] == [due[0], due[1], new[0]]
    # хвост возвращается целиком — из него вызывающий добирает, если свежей задачи нет
    assert picks == [due[0], due[1], new[0], btw[0], new[1]]
    # бюджет исчерпан открытыми миссиями
    assert daily_budget(5, 4) == 0
    # порядок: повторы due → back_to_work → новые
    assert select_daily_queue(0, due, btw, new, 10) == [*due, *btw, *new]


def test_select_daily_queue_lets_new_topic_through_long_review_tail():
    """Хвост просроченных повторов длиннее бюджета не должен запирать новые темы."""
    due = [{"x": f"d{i}"} for i in range(18)]
    new = [{"x": "n1"}]

    picks = select_daily_queue(0, due, [], new, 5)

    assert new[0] in picks[:5]
    assert picks[:5] == [due[0], due[1], due[2], due[3], new[0]]


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


def test_operator_close_daily_missions_records_recovery_evidence(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ recovery", ["5"])
    task = seeded_session.scalar(select(TaskORM).where(TaskORM.topic_id == topic.id))
    payload = svc.create_mission(
        {
            "student_id": STUDENT,
            "subject": Subject.MATH_PROFILE,
            "title": "Recovery drill",
            "instructions": "",
            "status": MissionStatus.ACTIVE,
            "ai_policy": AiPolicy.ATTEMPT_FIRST,
            "threshold_percent": 80.0,
            "topic_id": topic.id,
            "task_id": task.id,
            "due_date": FIXED_TODAY,
            "source_ref": "daily:manual:recovery",
        }
    )
    mission_id = payload["id"]

    result = svc.operator_close_daily_missions(STUDENT, "guardian accepted completed drill")

    assert mission_id in {row["mission_id"] for row in result["closed"]}
    assert seeded_session.get(MissionORM, mission_id).status == MissionStatus.DONE
    evidence = seeded_session.scalar(
        select(EvidenceORM).where(EvidenceORM.mission_id == mission_id)
    )
    assert evidence is not None
    assert evidence.status == EvidenceStatus.PASSED
    assert evidence.error_category == ErrorCategory.NONE
    assert evidence.model_id == "operator-recovery"
    attempt = seeded_session.get(AttemptORM, evidence.attempt_id)
    assert attempt.mode == AttemptMode.UNKNOWN
    reviews = seeded_session.scalars(
        select(ReviewItemORM).where(ReviewItemORM.source_evidence_id == evidence.id)
    ).all()
    assert len(reviews) == 2
    assert svc.operator_close_daily_missions(STUDENT)["closed_count"] == 0


def test_operator_skip_daily_missions_retires_without_evidence(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ skip", ["5"])
    task = seeded_session.scalar(select(TaskORM).where(TaskORM.topic_id == topic.id))
    payload = svc.create_mission(
        {
            "student_id": STUDENT,
            "subject": Subject.MATH_PROFILE,
            "title": "Skip drill",
            "instructions": "",
            "status": MissionStatus.ACTIVE,
            "ai_policy": AiPolicy.ATTEMPT_FIRST,
            "threshold_percent": 80.0,
            "topic_id": topic.id,
            "task_id": task.id,
            "due_date": FIXED_TODAY,
            "source_ref": "daily:manual:skip",
        }
    )
    mission_id = payload["id"]

    result = svc.operator_skip_daily_missions([mission_id], "wrong queue")

    assert result["skipped_count"] == 1
    assert seeded_session.get(MissionORM, mission_id).status == MissionStatus.SKIPPED
    evidence = seeded_session.scalar(
        select(EvidenceORM).where(EvidenceORM.mission_id == mission_id)
    )
    assert evidence is None


def test_build_daily_queue_skips_manual_review_part2_topics(seeded_session, monkeypatch):
    svc = service(seeded_session)
    monkeypatch.setattr(svc, "_today", lambda: date(2026, 7, 7))

    result = svc.build_daily_queue(STUDENT, limit=5)

    titles = [mission["title"] for mission in result["filled"]]
    assert all("№14" not in title for title in titles)
    assert all("№16" not in title for title in titles)
    assert all("№17" not in title for title in titles)
    assert all("№18" not in title for title in titles)
    assert all("Задача 13" not in title for title in titles)


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


def test_build_daily_queue_backfills_slot_left_by_shortage(seeded_session, monkeypatch):
    """Кандидат без свежей задачи не должен съедать слот: место занимает следующий.

    Регресс из живого прогона: самый старый повтор висел на теме с пустым банком и
    каждый день гарантированно сжигал слот, а день приходил полупустым при полном банке."""
    svc = service(seeded_session, monkeypatch)
    dry = _open_topic_with_tasks(svc, seeded_session, "DQ сухая", ["9"], order=910)
    task = seeded_session.scalar(select(TaskORM).where(TaskORM.topic_id == dry.id))
    seeded_session.add(  # единственная задача уже назначена → свежей нет
        MissionORM(
            id=uuid4(),
            student_id=STUDENT,
            subject=Subject.MATH_PROFILE,
            topic_id=dry.id,
            task_id=task.id,
            title="прошлая",
            instructions="",
            status=MissionStatus.DONE,
            ai_policy=AiPolicy.ATTEMPT_FIRST,
            threshold_percent=80.0,
        )
    )
    full_a = _open_topic_with_tasks(svc, seeded_session, "DQ полная A", ["5", "6"], order=911)
    full_b = _open_topic_with_tasks(svc, seeded_session, "DQ полная B", ["7", "8"], order=912)
    _due_card(seeded_session, dry.id, date(2019, 1, 1))  # старше → первый в очереди
    _due_card(seeded_session, full_a.id, date(2020, 1, 1))
    _due_card(seeded_session, full_b.id, date(2020, 1, 2))

    res = svc.build_daily_queue(STUDENT, limit=2)

    assert dry.id in {s["topic_id"] for s in res["shortage"]}
    # слот сухой темы добран следующим кандидатом, а не потерян
    assert len(res["filled"]) == 2
    assert dry.id not in {m["topic_id"] for m in res["filled"]}


def test_daily_coverage_reports_a_short_day_and_stays_silent_on_a_full_one(
    seeded_session, monkeypatch
):
    """Недобранный день — отказ покрытия, а не «просто меньше задач».

    Считает `judge_gate.totals` (тот же модуль, что в конвейере вакансий): каждый слот
    бюджета обязан получить явный исход, иначе день из двух задач вместо пяти неотличим
    от нормального — ровно тот дефект, который поймал ребёнок, а не мониторинг."""
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ покрытие", ["5", "6"], order=930)
    _due_card(seeded_session, topic.id)

    short = svc.build_daily_queue(STUDENT, limit=5)

    assert len(short["filled"]) < 5
    assert any("no_fresh_task" in v for v in short["coverage"])

    full = svc.build_daily_queue(STUDENT, limit=len(short["filled"]))
    assert full["coverage"] == []  # бюджет исчерпан переносом — покрывать нечего


def test_daily_coverage_rejects_a_route_outside_the_declared_vocabulary():
    """Опечатка в имени маршрута обязана падать, а не тихо перестать считаться."""
    from judge_gate.totals import TotalsContractError, check_run

    from app.application.use_cases import DAILY_COVERAGE

    with pytest.raises(TotalsContractError):
        check_run([("driil", None)], DAILY_COVERAGE, expected_count=1)


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


def test_ready_mode_serves_marked_topic_and_holds_back_unmarked(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    marked = _open_topic_with_tasks(svc, seeded_session, "DQ ready", ["1", "2"], order=901)
    _open_topic_with_tasks(svc, seeded_session, "DQ не ready", ["3", "4"], order=902)
    svc.set_topic_theory_ready(marked.id, True)

    res = svc.build_daily_queue(STUDENT, limit=5)

    titles = [m["title"] for m in res["filled"]]
    assert "Дрилл: DQ ready" in titles
    # неотмеченная тема текущей фазы придерживается, пока есть хоть одна отметка
    assert "Дрилл: DQ не ready" not in titles


def test_ready_mode_serves_past_phase_topic_on_later_date(seeded_session, monkeypatch):
    svc = service(seeded_session)
    monkeypatch.setattr(svc, "_today", lambda: date(2026, 7, 7))
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ прошлая фаза", ["5", "6"])

    # июньская тема на июльской дате без отметки не выдаётся (фаза не текущая)
    res = svc.build_daily_queue(STUDENT, limit=10)
    assert "Дрилл: DQ прошлая фаза" not in [m["title"] for m in res["filled"]]

    svc.set_topic_theory_ready(topic.id, True)
    res2 = svc.build_daily_queue(STUDENT, limit=10)
    assert "Дрилл: DQ прошлая фаза" in [m["title"] for m in res2["filled"]]


def test_ready_marked_topic_without_fresh_task_reports_shortage(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ ready короткий", ["9"])
    task = seeded_session.scalar(select(TaskORM).where(TaskORM.topic_id == topic.id))
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
    seeded_session.commit()
    svc.set_topic_theory_ready(topic.id, True)

    res = svc.build_daily_queue(STUDENT, limit=5)

    assert topic.id in {s["topic_id"] for s in res["shortage"]}


def test_theory_ready_candidates_and_program_flag(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ candidates", ["1"])

    rows = svc.list_theory_ready_candidates(STUDENT)
    assert next(r for r in rows if r["topic_id"] == topic.id)["theory_ready"] is False
    # part-2/manual-path темы (стерео, параметр и т.п.) в кандидаты не попадают
    assert all("стереометрия" not in str(r["title"]).lower() for r in rows)
    assert all("параметр" not in str(r["title"]).lower() for r in rows)

    svc.set_topic_theory_ready(topic.id, True)
    rows = svc.list_theory_ready_candidates(STUDENT)
    assert next(r for r in rows if r["topic_id"] == topic.id)["theory_ready"] is True

    # флаг виден в program_progress — для бейджа «теория изучена» на «Программе»
    phases = svc.list_program_progress(STUDENT)
    june = next(p for p in phases if p["key"] == "june_diagnostics")
    assert next(t for t in june["topics"] if t["topic_id"] == topic.id)["theory_ready"] is True

    # снятие отметки возвращает прежнее поведение
    svc.set_topic_theory_ready(topic.id, False)
    rows = svc.list_theory_ready_candidates(STUDENT)
    assert next(r for r in rows if r["topic_id"] == topic.id)["theory_ready"] is False


def test_prerequisites_met_gates_until_all_passed():
    prereqs = {"C": ("A", "B")}
    assert prerequisites_met("C", set(), prereqs) is False
    assert prerequisites_met("C", {"A"}, prereqs) is False
    assert prerequisites_met("C", {"A", "B"}, prereqs) is True
    # тема без пререквизитов всегда доступна
    assert prerequisites_met("Z", set(), prereqs) is True


def test_describe_pick_covers_kinds():
    assert describe_pick({"kind": "due_review"}) == "повтор по расписанию (интервальное закрепление)"
    assert describe_pick({"kind": "back_to_work"}) == "вернулась в работу после проваленного повтора"
    new = describe_pick(
        {"kind": "new_topic", "prerequisites": ["A"], "phase": "june_diagnostics", "error_count": 2}
    )
    assert "новая тема" in new and "A" in new and "june_diagnostics" in new and "2" in new
    # неизвестный вид не падает, а даёт нейтральную строку
    assert describe_pick({}) == "выбрана планировщиком дня"


def test_build_daily_queue_gates_new_topic_until_prerequisite_passed(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    base = _open_topic_with_tasks(svc, seeded_session, "DQ база", ["1", "2"], order=910)
    dependent = _open_topic_with_tasks(svc, seeded_session, "DQ зависимая", ["3", "4"], order=911)
    monkeypatch.setattr(use_cases, "PREREQUISITES", {"DQ зависимая": ("DQ база",)})
    # ready-mode изолирует от сеяных тем: кандидаты в новые — только эти две
    svc.set_topic_theory_ready(base.id, True)
    svc.set_topic_theory_ready(dependent.id, True)

    res = svc.build_daily_queue(STUDENT, limit=5)
    titles = [m["title"] for m in res["filled"]]
    assert "Дрилл: DQ база" in titles
    assert "Дрилл: DQ зависимая" not in titles  # пререквизит не закрыт → заблокирована

    base_mission = seeded_session.scalar(
        select(MissionORM).where(MissionORM.source_ref == f"daily:new:{base.id}")
    )
    task = seeded_session.get(TaskORM, base_mission.task_id)
    assert _submit(svc, base_mission.id, task.expected_answer)["status"] == EvidenceStatus.PASSED

    res2 = svc.build_daily_queue(STUDENT, limit=5)
    assert "Дрилл: DQ зависимая" in [m["title"] for m in res2["filled"]]  # база закрыта → доступна


def test_build_daily_queue_attaches_reason_and_why(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    new_topic = _open_topic_with_tasks(svc, seeded_session, "DQ новая", ["1", "2"], order=920)
    rev_topic = _open_topic_with_tasks(svc, seeded_session, "DQ повтор-повод", ["5", "6"], order=921)
    _due_card(seeded_session, rev_topic.id)
    svc.set_topic_theory_ready(new_topic.id, True)  # изоляция новых от сеяных

    res = svc.build_daily_queue(STUDENT, limit=5)
    by_title = {m["title"]: m for m in res["filled"]}

    assert by_title["Дрилл: DQ новая"]["reason"]["kind"] == "new_topic"
    assert isinstance(by_title["Дрилл: DQ новая"]["why"], str) and by_title["Дрилл: DQ новая"]["why"]
    assert by_title["Дрилл: DQ повтор-повод"]["reason"]["kind"] == "due_review"
    assert (
        by_title["Дрилл: DQ повтор-повод"]["why"]
        == "повтор по расписанию (интервальное закрепление)"
    )


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


def test_list_self_pick_candidates_excludes_manual_review_topics(seeded_session, monkeypatch):
    svc = service(seeded_session)
    monkeypatch.setattr(svc, "_today", lambda: date(2026, 7, 7))

    rows = svc.list_self_pick_candidates(STUDENT)

    titles = [str(r["title"]) for r in rows]
    assert all("№14" not in title for title in titles)
    assert all("№16" not in title for title in titles)
    assert all("№17" not in title for title in titles)
    assert all("№18" not in title for title in titles)
    assert all("Задача 13" not in title for title in titles)


def test_list_self_pick_candidates_excludes_topic_already_open_today(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ self уже открыта", ["1", "2"])

    before = {r["topic_id"] for r in svc.list_self_pick_candidates(STUDENT)}
    assert topic.id in before

    svc.set_topic_theory_ready(topic.id, True)  # изоляция от сеяных тем при авто-пике
    svc.build_daily_queue(STUDENT, limit=5)

    after = {r["topic_id"] for r in svc.list_self_pick_candidates(STUDENT)}
    assert topic.id not in after  # уже открыта daily:new: сегодня — второй раз не предложим


def test_list_self_pick_candidates_respects_prerequisites(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    base = _open_topic_with_tasks(svc, seeded_session, "DQ self база", ["1"], order=930)
    dependent = _open_topic_with_tasks(svc, seeded_session, "DQ self зависимая", ["2"], order=931)
    monkeypatch.setattr(use_cases, "PREREQUISITES", {"DQ self зависимая": ("DQ self база",)})

    rows = svc.list_self_pick_candidates(STUDENT)
    ids = {r["topic_id"] for r in rows}
    assert base.id in ids
    assert dependent.id not in ids  # база ещё не решена

    base_task = seeded_session.scalar(select(TaskORM).where(TaskORM.topic_id == base.id))
    mission = svc.create_mission(
        {
            "student_id": STUDENT,
            "subject": Subject.MATH_PROFILE,
            "title": "разогрев базы",
            "instructions": "",
            "status": MissionStatus.ACTIVE,
            "ai_policy": AiPolicy.ATTEMPT_FIRST,
            "threshold_percent": 80.0,
            "topic_id": base.id,
            "task_id": base_task.id,
            "due_date": FIXED_TODAY,
            "source_ref": "daily:manual:warmup",
        }
    )
    _submit(svc, mission["id"], base_task.expected_answer)

    rows2 = svc.list_self_pick_candidates(STUDENT)
    assert dependent.id in {r["topic_id"] for r in rows2}  # база решена → доступна


def test_self_add_topic_mission_creates_daily_self_mission(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ self добавление", ["1", "2"])

    result = svc.self_add_topic_mission(STUDENT, topic.id)

    mission = result["mission"]
    assert mission["source_ref"] == f"daily:self:{topic.id}"
    assert mission["why"] == "выбрана самой ученицей из списка тем трека"
    assert mission["title"] in [d["title"] for d in svc.list_daily_drill(STUDENT)]


def test_self_add_topic_mission_reports_shortage_without_creating_mission(
    seeded_session, monkeypatch
):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ self shortage", ["9"])
    task = seeded_session.scalar(select(TaskORM).where(TaskORM.topic_id == topic.id))
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
    seeded_session.commit()

    result = svc.self_add_topic_mission(STUDENT, topic.id)

    assert result["shortage"]["topic_id"] == topic.id
    assert seeded_session.scalar(
        select(MissionORM).where(MissionORM.source_ref == f"daily:self:{topic.id}")
    ) is None


def test_self_add_topic_mission_rejects_topic_outside_candidates(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)

    try:
        svc.self_add_topic_mission(STUDENT, uuid4())
        raise AssertionError("expected ValueError for an unknown topic")
    except ValueError:
        pass


def test_serve_more_from_topic_serves_fresh_and_logs_signal(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ ещё", ["1", "2"])

    result = svc.serve_more_from_topic(STUDENT, topic.id)

    assert result["mission"]["source_ref"] == f"daily:self:{topic.id}"
    assert result["mission"]["title"] in [d["title"] for d in svc.list_daily_drill(STUDENT)]
    demand = svc.demand_by_topic(30)
    row = next(r for r in demand if r["topic_id"] == topic.id)
    assert row["served"] == 1 and row["shortage"] == 0


def test_serve_more_from_topic_works_even_when_topic_already_open_today(
    seeded_session, monkeypatch
):
    # ключевое отличие от self-pick: тема активно дриллится (уже открыта сегодня) —
    # serve_more не должен отсекать её гейтом open-today
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ ещё открыта", ["1", "2", "3"])
    svc.set_topic_theory_ready(topic.id, True)
    svc.build_daily_queue(STUDENT, limit=5)  # открывает daily:new: по теме
    assert topic.id not in {c["topic_id"] for c in svc.list_self_pick_candidates(STUDENT)}

    result = svc.serve_more_from_topic(STUDENT, topic.id)  # но «ещё» всё равно работает
    assert "mission" in result


def test_serve_more_from_topic_reports_shortage_and_logs_signal(seeded_session, monkeypatch):
    svc = service(seeded_session, monkeypatch)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ ещё пусто", ["9"])
    task = seeded_session.scalar(select(TaskORM).where(TaskORM.topic_id == topic.id))
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
    seeded_session.commit()

    result = svc.serve_more_from_topic(STUDENT, topic.id)

    assert result["shortage"]["topic_id"] == topic.id
    row = next(r for r in svc.demand_by_topic(30) if r["topic_id"] == topic.id)
    assert row["shortage"] == 1 and row["served"] == 0


def test_serve_more_from_topic_rejects_manual_review_topic(seeded_session, monkeypatch):
    svc = service(seeded_session)
    monkeypatch.setattr(svc, "_today", lambda: date(2026, 7, 7))
    # part-2/manual тема из july_aug_foundation (Стереометрия №14) — serve_more не должен её пускать
    manual = seeded_session.scalar(
        select(TopicORM).where(TopicORM.title == "Стереометрия (№14): объёмы и углы")
    )
    assert manual is not None

    try:
        svc.serve_more_from_topic(STUDENT, manual.id)
        raise AssertionError("expected ValueError for a manual-review topic")
    except ValueError:
        pass


def test_days_since_last_diagnostic_none_when_no_slice(session_factory):
    with session_factory() as raw_session:
        svc = service(raw_session)
        assert svc.days_since_last_diagnostic(uuid4()) is None


def test_days_since_last_diagnostic_counts_from_most_recent(session_factory, monkeypatch):
    student = uuid4()
    with session_factory() as raw_session:
        svc = service(raw_session, monkeypatch)
        raw_session.add_all(
            [
                StudyLogEntryORM(
                    id=uuid4(),
                    student_id=student,
                    subject=Subject.MATH_PROFILE,
                    occurred_on=FIXED_TODAY - timedelta(days=6),
                    topic_title="старый срез",
                    tasks_total=5,
                    tasks_correct=4,
                    percent_correct=80.0,
                ),
                StudyLogEntryORM(
                    id=uuid4(),
                    student_id=student,
                    subject=Subject.MATH_PROFILE,
                    occurred_on=FIXED_TODAY - timedelta(days=2),
                    topic_title="свежий срез",
                    tasks_total=5,
                    tasks_correct=5,
                    percent_correct=100.0,
                ),
            ]
        )
        raw_session.commit()

        assert svc.days_since_last_diagnostic(student) == 2


def test_daily_activity_summary_reflects_attempts_and_open_drill(seeded_session):
    # без monkeypatch _today — created_at попытки пишется реальным временем, должно совпасть
    svc = service(seeded_session)
    topic = _open_topic_with_tasks(svc, seeded_session, "DQ activity", ["1", "2"])
    task = seeded_session.scalar(select(TaskORM).where(TaskORM.topic_id == topic.id))
    mission = svc.create_mission(
        {
            "student_id": STUDENT,
            "subject": Subject.MATH_PROFILE,
            "title": "Дрилл: DQ activity",
            "instructions": "",
            "status": MissionStatus.ACTIVE,
            "ai_policy": AiPolicy.ATTEMPT_FIRST,
            "threshold_percent": 80.0,
            "topic_id": topic.id,
            "task_id": task.id,
            "due_date": date.today(),
            "source_ref": "daily:manual:activity",
        }
    )

    before = svc.daily_activity_summary(STUDENT)
    assert before["attempted_today"] is False
    assert before["drill_open"] == 1

    _submit(svc, mission["id"], task.expected_answer)

    after = svc.daily_activity_summary(STUDENT)
    assert after["attempted_today"] is True
    assert after["drill_open"] == 0  # миссия закрыта (DONE)
