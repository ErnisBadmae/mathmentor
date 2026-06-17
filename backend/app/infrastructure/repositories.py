from datetime import date, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.enums import (
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    MissionStatus,
    ReviewStatus,
    Subject,
    TopicState,
)
from app.domain.policies import compute_topic_state
from app.infrastructure.models import (
    AttemptORM,
    CleanSheetEventORM,
    ErrorEventORM,
    EvidenceORM,
    MissionORM,
    ReviewItemORM,
    ScoreEventORM,
    StudentProfileORM,
    SubjectTrackORM,
    TaskORM,
    TopicORM,
)


def _local_today() -> date:
    return datetime.now(ZoneInfo(get_settings().local_timezone)).date()


def _max_dt(current: datetime | None, candidate: datetime | None) -> datetime | None:
    if current is None:
        return candidate
    if candidate is None:
        return current
    return max(current, candidate)


class SqlAlchemyUnitOfWork:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.students = StudentSqlRepository(session)
        self.missions = MissionSqlRepository(session)
        self.attempts = AttemptSqlRepository(session)
        self.evidence = EvidenceSqlRepository(session)
        self.dashboard = DashboardSqlRepository(session)
        self.errors = ErrorSqlRepository(session)
        self.reviews = ReviewSqlRepository(session)
        self.scores = ScoreSqlRepository(session)
        self.topics = TopicSqlRepository(session)
        self.tasks = TaskSqlRepository(session)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


class MissionSqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_for_attempt(self, mission_id: UUID) -> MissionORM:
        mission = self.session.get(MissionORM, mission_id)
        if mission is None:
            raise LookupError(f"Mission not found: {mission_id}")
        return mission

    def list_today(self, student_id: UUID) -> list[MissionORM]:
        stmt = (
            select(MissionORM)
            .where(MissionORM.student_id == student_id)
            .where(MissionORM.status.in_([MissionStatus.ACTIVE, MissionStatus.REPEAT]))
            .order_by(MissionORM.due_date.asc().nulls_last(), MissionORM.subject.asc())
        )
        return list(self.session.scalars(stmt).all())

    def create(self, values: dict[str, object]) -> MissionORM:
        mission = MissionORM(**values)
        self.session.add(mission)
        self.session.flush()
        return mission

    def latest_for_topic(self, topic_id: UUID) -> MissionORM | None:
        return self.session.scalar(
            select(MissionORM)
            .where(MissionORM.topic_id == topic_id)
            .order_by(MissionORM.due_date.desc().nulls_last(), MissionORM.id.desc())
            .limit(1)
        )

    def update(self, mission_id: UUID, values: dict[str, object]) -> MissionORM:
        mission = self.get_for_attempt(mission_id)
        for key, value in values.items():
            if value is not None:
                setattr(mission, key, value)
        self.session.flush()
        return mission

    def mark_done(self, mission_id: UUID) -> None:
        self.get_for_attempt(mission_id).status = MissionStatus.DONE

    def mark_repeat(self, mission_id: UUID) -> None:
        self.get_for_attempt(mission_id).status = MissionStatus.REPEAT


class TaskSqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, task_id: UUID) -> TaskORM:
        task = self.session.get(TaskORM, task_id)
        if task is None:
            raise LookupError(f"Task not found: {task_id}")
        return task

    def add(self, values: dict[str, object]) -> TaskORM:
        source_ref = values.get("source_ref")
        if source_ref:
            existing = self.session.scalar(select(TaskORM).where(TaskORM.source_ref == source_ref))
            if existing is not None:
                return existing
        task = TaskORM(**values)
        self.session.add(task)
        self.session.flush()
        return task


class AttemptSqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, values: dict[str, object]) -> AttemptORM:
        attempt = AttemptORM(**values)
        self.session.add(attempt)
        self.session.flush()
        return attempt


class EvidenceSqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, values: dict[str, object]) -> EvidenceORM:
        evidence = EvidenceORM(**values)
        self.session.add(evidence)
        self.session.flush()
        return evidence

    def get(self, evidence_id: UUID) -> EvidenceORM:
        evidence = self.session.get(EvidenceORM, evidence_id)
        if evidence is None:
            raise LookupError(f"Evidence not found: {evidence_id}")
        return evidence

    def list_manual_reviews(self, student_id: UUID) -> list[dict[str, object]]:
        rows = self.session.execute(
            select(EvidenceORM, MissionORM.title, TopicORM.title)
            .join(MissionORM, MissionORM.id == EvidenceORM.mission_id)
            .outerjoin(TopicORM, TopicORM.id == EvidenceORM.topic_id)
            .where(EvidenceORM.student_id == student_id)
            .where(EvidenceORM.status == EvidenceStatus.NEEDS_MANUAL_REVIEW)
            .order_by(EvidenceORM.created_at.desc())
        ).all()
        return [
            {
                "id": evidence.id,
                "attempt_id": evidence.attempt_id,
                "mission_id": evidence.mission_id,
                "mission_title": mission_title,
                "topic_id": evidence.topic_id,
                "topic_title": topic_title,
                "status": evidence.status,
                "score_percent": evidence.score_percent,
                "error_category": evidence.error_category,
                "feedback": evidence.feedback,
                "next_action": evidence.next_action,
                "model_id": evidence.model_id,
                "prompt_version": evidence.prompt_version,
                "rubric_version": evidence.rubric_version,
                "created_at": evidence.created_at,
            }
            for evidence, mission_title, topic_title in rows
        ]

    def add_error_event(self, values: dict[str, object]) -> None:
        self.session.add(ErrorEventORM(**values))

    def schedule_reviews(self, values: list[dict[str, object]]) -> None:
        self.session.add_all([ReviewItemORM(**item) for item in values])


class DashboardSqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_dashboard(self, student_id: UUID) -> dict[str, object]:
        tracks = list(
            self.session.scalars(
                select(SubjectTrackORM).where(SubjectTrackORM.student_id == student_id)
            ).all()
        )
        top_errors = list(
            self.session.execute(
                select(ErrorEventORM.category, func.count(ErrorEventORM.id))
                .where(ErrorEventORM.student_id == student_id)
                .group_by(ErrorEventORM.category)
                .order_by(func.count(ErrorEventORM.id).desc())
                .limit(3)
            ).all()
        )
        imported_code_total = (
            self.session.scalar(
                select(func.coalesce(func.sum(CleanSheetEventORM.tasks_total), 0)).where(
                    CleanSheetEventORM.student_id == student_id
                )
            )
            or 0
        )
        imported_clean_code = (
            self.session.scalar(
                select(func.coalesce(func.sum(CleanSheetEventORM.clean_sheet_count), 0)).where(
                    CleanSheetEventORM.student_id == student_id
                )
            )
            or 0
        )
        code_attempts_total = (
            self.session.scalar(
                select(func.count(AttemptORM.id))
                .where(AttemptORM.student_id == student_id)
                .where(AttemptORM.kind == AttemptKind.CODE)
            )
            or 0
        )
        latest_evidence = (
            select(EvidenceORM.attempt_id, func.max(EvidenceORM.created_at).label("created_at"))
            .group_by(EvidenceORM.attempt_id)
            .subquery()
        )
        clean_attempts_passed = (
            self.session.scalar(
                select(func.count(AttemptORM.id))
                .join(EvidenceORM, EvidenceORM.attempt_id == AttemptORM.id)
                .join(
                    latest_evidence,
                    (latest_evidence.c.attempt_id == EvidenceORM.attempt_id)
                    & (latest_evidence.c.created_at == EvidenceORM.created_at),
                )
                .where(AttemptORM.student_id == student_id)
                .where(AttemptORM.kind == AttemptKind.CODE)
                .where(AttemptORM.mode == AttemptMode.CLEAN_SHEET)
                .where(EvidenceORM.status == EvidenceStatus.PASSED)
            )
            or 0
        )
        due_reviews = (
            self.session.scalar(
                select(func.count(ReviewItemORM.id))
                .where(ReviewItemORM.student_id == student_id)
                .where(ReviewItemORM.status == ReviewStatus.DUE)
                .where(ReviewItemORM.due_date <= _local_today())
            )
            or 0
        )
        total_code = imported_code_total + code_attempts_total
        clean_code = imported_clean_code + clean_attempts_passed
        return {
            "tracks": [
                {
                    "subject": track.subject,
                    "current_score": track.current_score,
                    "target_score": track.target_score,
                    "score_gap": track.target_score - track.current_score,
                    "phase": track.phase,
                }
                for track in tracks
            ],
            "clean_sheet_ratio": 0.0 if total_code == 0 else clean_code / total_code,
            "top_errors": [
                {"category": category, "count": count} for category, count in top_errors
            ],
            "due_reviews": due_reviews,
        }


class StudentSqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_current(self) -> StudentProfileORM:
        student = self.session.scalar(
            select(StudentProfileORM).order_by(StudentProfileORM.id).limit(1)
        )
        if student is None:
            raise LookupError("No student profile exists. Run seed/import first.")
        return student


class ErrorSqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_errors(
        self,
        student_id: UUID,
        subject: Subject | None = None,
        category: ErrorCategory | None = None,
    ) -> list[dict[str, object]]:
        stmt = (
            select(ErrorEventORM, TopicORM.title)
            .outerjoin(TopicORM, TopicORM.id == ErrorEventORM.topic_id)
            .where(ErrorEventORM.student_id == student_id)
            .order_by(ErrorEventORM.created_at.desc())
        )
        if subject is not None:
            stmt = stmt.where(ErrorEventORM.subject == subject)
        if category is not None:
            stmt = stmt.where(ErrorEventORM.category == category)
        rows = self.session.execute(stmt).all()
        return [
            {
                "id": event.id,
                "subject": event.subject,
                "topic_id": event.topic_id,
                "topic_title": topic_title,
                "mission_id": event.mission_id,
                "attempt_id": event.attempt_id,
                "evidence_id": event.evidence_id,
                "category": event.category,
                "detail": event.detail,
                "created_at": event.created_at,
                "source_ref": event.source_ref,
            }
            for event, topic_title in rows
        ]


class ReviewSqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_reviews(
        self,
        student_id: UUID,
        status: ReviewStatus | None = None,
        due_on_or_before: date | None = None,
    ) -> list[dict[str, object]]:
        stmt = (
            select(ReviewItemORM, TopicORM.title, TopicORM.subject)
            .join(TopicORM, TopicORM.id == ReviewItemORM.topic_id)
            .where(ReviewItemORM.student_id == student_id)
            .order_by(ReviewItemORM.due_date.asc())
        )
        if status is not None:
            stmt = stmt.where(ReviewItemORM.status == status)
        if due_on_or_before is not None:
            stmt = stmt.where(ReviewItemORM.due_date <= due_on_or_before)
        rows = self.session.execute(stmt).all()
        return [
            {
                "id": item.id,
                "student_id": item.student_id,
                "topic_id": item.topic_id,
                "topic_title": topic_title,
                "subject": subject,
                "due_date": item.due_date,
                "status": item.status,
                "source_evidence_id": item.source_evidence_id,
                "source_ref": item.source_ref,
            }
            for item, topic_title, subject in rows
        ]

    def mark_result(self, review_id: UUID, status: ReviewStatus) -> ReviewItemORM:
        item = self.session.get(ReviewItemORM, review_id)
        if item is None:
            raise LookupError(f"Review item not found: {review_id}")
        item.status = status
        self.session.flush()
        return item


class ScoreSqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_event(self, values: dict[str, object]) -> ScoreEventORM:
        source_ref = values.get("source_ref")
        if source_ref:
            existing = self.session.scalar(
                select(ScoreEventORM).where(ScoreEventORM.source_ref == source_ref)
            )
            if existing is not None:
                return existing
        event = ScoreEventORM(**values)
        self.session.add(event)
        track = self.session.scalar(
            select(SubjectTrackORM)
            .where(SubjectTrackORM.student_id == event.student_id)
            .where(SubjectTrackORM.subject == event.subject)
        )
        if track is None:
            track = SubjectTrackORM(
                id=uuid4(),
                student_id=event.student_id,
                subject=event.subject,
                current_score=event.score,
                target_score=85,
                phase="foundation",
            )
            self.session.add(track)
        else:
            track.current_score = event.score
        self.session.flush()
        return event


class TopicSqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, topic_id: UUID) -> TopicORM | None:
        return self.session.get(TopicORM, topic_id)

    def list_topic_lifecycle(self, student_id: UUID) -> list[dict[str, object]]:
        """Per-topic computed lifecycle (REQUIREMENTS §9). A topic is listed if it has
        any mission/evidence/review/error for the student. State is derived, not stored."""
        today = _local_today()
        facts: dict[UUID, dict[str, object]] = {}

        def slot(topic_id: UUID) -> dict[str, object]:
            return facts.setdefault(
                topic_id,
                {
                    "active_missions": 0,
                    "passed": False,
                    "reviews_due": 0,
                    "reviews_due_today": 0,
                    "reviews_done": 0,
                    "back_to_work_reviews": 0,
                    "error_count": 0,
                    "last_activity_at": None,
                    "errors_by_category": {},
                },
            )

        # Missions (any status registers the topic; ACTIVE/REPEAT feed the state machine).
        mission_rows = self.session.execute(
            select(MissionORM.topic_id, MissionORM.status, func.count(MissionORM.id))
            .where(MissionORM.student_id == student_id)
            .where(MissionORM.topic_id.is_not(None))
            .group_by(MissionORM.topic_id, MissionORM.status)
        ).all()
        for topic_id, status, count in mission_rows:
            s = slot(topic_id)
            if status in (MissionStatus.ACTIVE, MissionStatus.REPEAT):
                s["active_missions"] += count

        # Evidence: latest activity + whether the topic was ever passed.
        evidence_rows = self.session.execute(
            select(EvidenceORM.topic_id, func.max(EvidenceORM.created_at))
            .where(EvidenceORM.student_id == student_id)
            .where(EvidenceORM.topic_id.is_not(None))
            .group_by(EvidenceORM.topic_id)
        ).all()
        for topic_id, last_created in evidence_rows:
            s = slot(topic_id)
            s["last_activity_at"] = _max_dt(s["last_activity_at"], last_created)
        passed_topics = set(
            self.session.scalars(
                select(EvidenceORM.topic_id)
                .where(EvidenceORM.student_id == student_id)
                .where(EvidenceORM.status == EvidenceStatus.PASSED)
                .where(EvidenceORM.topic_id.is_not(None))
                .distinct()
            ).all()
        )
        for topic_id in passed_topics:
            slot(topic_id)["passed"] = True

        # Reviews by status, plus overdue-today as a separate UI signal.
        review_rows = self.session.execute(
            select(ReviewItemORM.topic_id, ReviewItemORM.status, func.count(ReviewItemORM.id))
            .where(ReviewItemORM.student_id == student_id)
            .group_by(ReviewItemORM.topic_id, ReviewItemORM.status)
        ).all()
        for topic_id, status, count in review_rows:
            s = slot(topic_id)
            if status == ReviewStatus.DUE:
                s["reviews_due"] += count
            elif status == ReviewStatus.DONE:
                s["reviews_done"] += count
            elif status == ReviewStatus.BACK_TO_WORK:
                s["back_to_work_reviews"] += count
        due_today_rows = self.session.execute(
            select(ReviewItemORM.topic_id, func.count(ReviewItemORM.id))
            .where(ReviewItemORM.student_id == student_id)
            .where(ReviewItemORM.status == ReviewStatus.DUE)
            .where(ReviewItemORM.due_date <= today)
            .group_by(ReviewItemORM.topic_id)
        ).all()
        for topic_id, count in due_today_rows:
            slot(topic_id)["reviews_due_today"] = count

        # Errors: total + per-category counts (for the dominant weak signal).
        error_rows = self.session.execute(
            select(
                ErrorEventORM.topic_id,
                ErrorEventORM.category,
                func.count(ErrorEventORM.id),
                func.max(ErrorEventORM.created_at),
            )
            .where(ErrorEventORM.student_id == student_id)
            .where(ErrorEventORM.topic_id.is_not(None))
            .group_by(ErrorEventORM.topic_id, ErrorEventORM.category)
        ).all()
        for topic_id, category, count, last_created in error_rows:
            s = slot(topic_id)
            s["error_count"] += count
            s["errors_by_category"][category] = count
            s["last_activity_at"] = _max_dt(s["last_activity_at"], last_created)

        if not facts:
            return []
        topics = {
            topic.id: topic
            for topic in self.session.scalars(
                select(TopicORM).where(TopicORM.id.in_(facts.keys()))
            ).all()
        }

        result: list[dict[str, object]] = []
        for topic_id, s in facts.items():
            topic = topics.get(topic_id)
            if topic is None:
                continue
            errors_by_category: dict[ErrorCategory, int] = s["errors_by_category"]
            top_error_category = None
            if errors_by_category:
                # deterministic tie-break: count desc, then category asc
                top_error_category = sorted(
                    errors_by_category.items(), key=lambda kv: (-kv[1], kv[0])
                )[0][0]
            result.append(
                {
                    "topic_id": topic_id,
                    "topic_title": topic.title,
                    "subject": topic.subject,
                    "task_number": topic.task_number,
                    "state": compute_topic_state(
                        active_missions=s["active_missions"],
                        has_passed_evidence=s["passed"],
                        reviews_due=s["reviews_due"],
                        reviews_done=s["reviews_done"],
                        reviews_back_to_work=s["back_to_work_reviews"],
                    ),
                    "active_missions": s["active_missions"],
                    "passed": s["passed"],
                    "reviews_due": s["reviews_due"],
                    "reviews_due_today": s["reviews_due_today"],
                    "reviews_done": s["reviews_done"],
                    "back_to_work_reviews": s["back_to_work_reviews"],
                    "error_count": s["error_count"],
                    "top_error_category": top_error_category,
                    "last_activity_at": s["last_activity_at"],
                }
            )
        result.sort(key=lambda r: r["topic_title"])
        return result

    def list_program(self, student_id: UUID) -> list[dict[str, object]]:
        """Program topics (phase is not None) with their computed lifecycle state.
        Reuses ``list_topic_lifecycle``; untouched program topics default to OPEN."""
        lifecycle = {row["topic_id"]: row for row in self.list_topic_lifecycle(student_id)}
        topics = self.session.scalars(
            select(TopicORM).where(TopicORM.phase.is_not(None))
        ).all()
        rows: list[dict[str, object]] = []
        for topic in topics:
            life = lifecycle.get(topic.id)
            rows.append(
                {
                    "phase": topic.phase,
                    "program_order": topic.program_order,
                    "topic_id": topic.id,
                    "topic_title": topic.title,
                    "subject": topic.subject,
                    "task_number": topic.task_number,
                    "state": life["state"] if life else TopicState.OPEN,
                    "error_count": life["error_count"] if life else 0,
                    "reviews_due_today": life["reviews_due_today"] if life else 0,
                }
            )
        return rows
