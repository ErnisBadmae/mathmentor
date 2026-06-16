"""Bootstrap demo data for local development.

Creates one guardian user, one student profile (using the all-zero UUID the
frontend defaults to via VITE_STUDENT_ID), two subject tracks matching the
baseline from AGENTS.md, and a handful of active missions so the dashboard
and daily-work screens have something to show. Safe to re-run: it skips
records that already exist instead of duplicating them.
"""

from datetime import UTC, date, datetime
from uuid import UUID

from app.domain.enums import AiPolicy, MissionStatus, Role, Subject
from app.infrastructure.db import SessionLocal
from app.infrastructure.models import MissionORM, StudentProfileORM, SubjectTrackORM, TopicORM, UserORM

DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DEMO_STUDENT_ID = UUID("00000000-0000-0000-0000-000000000000")

TOPICS = [
    (Subject.MATH_PROFILE, "Уравнения и неравенства с ОДЗ", "15"),
    (Subject.MATH_PROFILE, "Текстовые задачи на проценты", "11"),
    (Subject.INFORMATICS, "Анализ алгоритмов и сложность", "16"),
    (Subject.INFORMATICS, "Работа со строками", "6"),
]

MISSIONS = [
    (Subject.MATH_PROFILE, 0, "Решить уравнение с учётом ОДЗ", "Реши уравнение, отдельно проверь каждый корень на соответствие ОДЗ.", 80.0),
    (Subject.MATH_PROFILE, 1, "Задача на проценты", "Составь уравнение для текстовой задачи и доведи решение до числового ответа.", 80.0),
    (Subject.INFORMATICS, 2, "Оценить сложность алгоритма", "Определи асимптотическую сложность алгоритма и обоснуй ответ.", 80.0),
    (Subject.INFORMATICS, 3, "Разбор строки по условию", "Напиши программу, которая обрабатывает строку по заданному условию.", 80.0),
]


def seed() -> None:
    session = SessionLocal()
    try:
        if session.get(UserORM, DEMO_USER_ID) is None:
            session.add(UserORM(id=DEMO_USER_ID, display_name="Family operator", role=Role.GUARDIAN, created_at=datetime.now(UTC)))

        if session.get(StudentProfileORM, DEMO_STUDENT_ID) is None:
            session.add(StudentProfileORM(id=DEMO_STUDENT_ID, user_id=DEMO_USER_ID, exam_year=2027, display_name="Demo student"))

        existing_tracks = {track.subject for track in session.query(SubjectTrackORM).filter_by(student_id=DEMO_STUDENT_ID)}
        for index, (subject, current_score) in enumerate([(Subject.MATH_PROFILE, 65), (Subject.INFORMATICS, 50)], start=1):
            if subject not in existing_tracks:
                session.add(SubjectTrackORM(id=UUID(int=index), student_id=DEMO_STUDENT_ID, subject=subject, current_score=current_score, target_score=85, phase="foundation"))

        topic_ids: dict[tuple[Subject, str], UUID] = {}
        existing_topics = {(topic.subject, topic.title): topic.id for topic in session.query(TopicORM)}
        for index, (subject, title, task_number) in enumerate(TOPICS, start=1):
            if (subject, title) in existing_topics:
                topic_ids[(subject, title)] = existing_topics[(subject, title)]
                continue
            topic_id = UUID(int=1000 + index)
            session.add(TopicORM(id=topic_id, subject=subject, title=title, spec_year=2026, task_number=task_number))
            topic_ids[(subject, title)] = topic_id

        existing_mission_titles = {mission.title for mission in session.query(MissionORM).filter_by(student_id=DEMO_STUDENT_ID)}
        for index, (subject, topic_index, title, instructions, threshold) in enumerate(MISSIONS, start=1):
            if title in existing_mission_titles:
                continue
            topic_id = topic_ids[TOPICS[topic_index][0], TOPICS[topic_index][1]]
            session.add(
                MissionORM(
                    id=UUID(int=2000 + index),
                    student_id=DEMO_STUDENT_ID,
                    subject=subject,
                    topic_id=topic_id,
                    title=title,
                    instructions=instructions,
                    status=MissionStatus.ACTIVE,
                    ai_policy=AiPolicy.ATTEMPT_FIRST,
                    threshold_percent=threshold,
                    due_date=date.today(),
                )
            )

        session.commit()
        print("Seed complete.")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
