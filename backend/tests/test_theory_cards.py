from sqlalchemy import select

from app.application.use_cases import LearningService, RuleBasedReviewer
from app.domain.enums import AiPolicy, MissionStatus, Subject
from app.infrastructure.models import TopicORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts import seed as seed_module

STUDENT = seed_module.DEMO_STUDENT_ID


def _service(session) -> LearningService:
    return LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer())


def _topic(session, title: str) -> TopicORM:
    topic = session.scalar(select(TopicORM).where(TopicORM.title == title))
    assert topic is not None
    return topic


def test_seed_creates_safe_visual_concept_cards(seeded_session):
    vectors = _topic(seeded_session, "Векторы")
    cards = _service(seeded_session).list_topic_theory(vectors.id)

    kinds = [card["visual"]["kind"] for card in cards]
    assert kinds == ["vector_dot_product", "vector_2d"]
    for card in cards:
        assert card["topic_id"] == vectors.id
        assert card["visual"]["mode"] == "concept"
        assert "params" in card["visual"]
        assert "expected_answer" not in card
        assert "solution" not in card


def test_program_visual_ready_is_separate_from_student_theory_ready(seeded_session):
    phases = _service(seeded_session).list_program_progress(STUDENT)
    june = next(phase for phase in phases if phase["key"] == "june_diagnostics")
    by_title = {topic["topic_title"]: topic for topic in june["topics"]}

    assert by_title["Векторы"]["visual_ready"] is True
    assert by_title["Векторы"]["theory_ready"] is False
    assert by_title["Производная: геометрический смысл"]["visual_ready"] is True
    assert by_title["Производная: геометрический смысл"]["theory_ready"] is False


def test_mission_payload_marks_visual_ready_without_answer_key(seeded_session):
    topic = _topic(seeded_session, "Векторы")
    mission = _service(seeded_session).create_mission(
        {
            "student_id": STUDENT,
            "subject": Subject.MATH_PROFILE,
            "topic_id": topic.id,
            "title": "Векторы: концепт перед практикой",
            "instructions": "Посмотри идею сложения векторов, затем реши задачу самостоятельно.",
            "status": MissionStatus.ACTIVE,
            "ai_policy": AiPolicy.ATTEMPT_FIRST,
            "threshold_percent": 80.0,
        }
    )

    assert mission["topic_id"] == topic.id
    assert mission["visual_ready"] is True
    assert mission["statement"] is None
    assert "expected_answer" not in mission


def test_slice_tasks_carry_visual_ready_for_visual_topics(seeded_session):
    service = _service(seeded_session)
    topic = _topic(seeded_session, "Векторы")
    task = service.add_task(
        {
            "subject": Subject.MATH_PROFILE,
            "topic_id": topic.id,
            "statement": "Даны векторы a(1; 2) и b(3; 4). Найдите координаты a+b.",
            "expected_answer": "(4; 6)",
            "solution": "Складываем координаты: (1+3; 2+4) = (4; 6).",
            "source": "test",
            "source_ref": "test:theory:vector-slice",
        }
    )
    service.approve_task(task.id)

    items = service.draw_slice(Subject.MATH_PROFILE, size=1, topic_id=topic.id)

    assert items == [
        {
            "task_id": task.id,
            "topic_id": topic.id,
            "task_number": None,
            "statement": "Даны векторы a(1; 2) и b(3; 4). Найдите координаты a+b.",
            "visual_ready": True,
        }
    ]
