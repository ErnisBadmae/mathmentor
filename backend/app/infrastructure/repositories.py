from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import AttemptKind, AttemptMode, ErrorCategory, MissionStatus, ReviewStatus
from app.infrastructure.models import AttemptORM, ErrorEventORM, EvidenceORM, MissionORM, ReviewItemORM, SubjectTrackORM


class SqlAlchemyUnitOfWork:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.missions = MissionSqlRepository(session)
        self.attempts = AttemptSqlRepository(session)
        self.evidence = EvidenceSqlRepository(session)
        self.dashboard = DashboardSqlRepository(session)

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

    def mark_done(self, mission_id: UUID) -> None:
        self.get_for_attempt(mission_id).status = MissionStatus.DONE

    def mark_repeat(self, mission_id: UUID) -> None:
        self.get_for_attempt(mission_id).status = MissionStatus.REPEAT


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

    def add_error_event(self, values: dict[str, object]) -> None:
        self.session.add(ErrorEventORM(**values))

    def schedule_reviews(self, values: list[dict[str, object]]) -> None:
        self.session.add_all([ReviewItemORM(**item) for item in values])


class DashboardSqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_dashboard(self, student_id: UUID) -> dict[str, object]:
        tracks = list(self.session.scalars(select(SubjectTrackORM).where(SubjectTrackORM.student_id == student_id)).all())
        top_errors = list(
            self.session.execute(
                select(ErrorEventORM.category, func.count(ErrorEventORM.id))
                .where(ErrorEventORM.student_id == student_id)
                .group_by(ErrorEventORM.category)
                .order_by(func.count(ErrorEventORM.id).desc())
                .limit(3)
            ).all()
        )
        total_code = self.session.scalar(
            select(func.count(AttemptORM.id)).where(AttemptORM.student_id == student_id).where(AttemptORM.kind == AttemptKind.CODE)
        ) or 0
        clean_code = self.session.scalar(
            select(func.count(AttemptORM.id))
            .join(EvidenceORM, EvidenceORM.attempt_id == AttemptORM.id)
            .where(AttemptORM.student_id == student_id)
            .where(AttemptORM.kind == AttemptKind.CODE)
            .where(AttemptORM.mode == AttemptMode.CLEAN_SHEET)
            .where(EvidenceORM.error_category == ErrorCategory.NONE)
        ) or 0
        due_reviews = self.session.scalar(
            select(func.count(ReviewItemORM.id))
            .where(ReviewItemORM.student_id == student_id)
            .where(ReviewItemORM.status == ReviewStatus.DUE)
            .where(ReviewItemORM.due_date <= date.today())
        ) or 0
        return {
            "tracks": [
                {"subject": track.subject, "current_score": track.current_score, "target_score": track.target_score, "score_gap": track.target_score - track.current_score, "phase": track.phase}
                for track in tracks
            ],
            "clean_sheet_ratio": 0.0 if total_code == 0 else clean_code / total_code,
            "top_errors": [{"category": category, "count": count} for category, count in top_errors],
            "due_reviews": due_reviews,
        }
