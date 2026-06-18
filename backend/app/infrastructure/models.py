from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import (
    AiPolicy,
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    MissionStatus,
    ReviewStatus,
    Role,
    Subject,
    TaskStatus,
)
from app.infrastructure.db import Base

PG_UUID = Uuid


class UserORM(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InviteCodeORM(Base):
    __tablename__ = "invite_codes"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False))
    used_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StudentProfileORM(Base):
    __tablename__ = "student_profiles"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    exam_year: Mapped[int] = mapped_column(Integer)
    display_name: Mapped[str] = mapped_column(String(120))


class SubjectTrackORM(Base):
    __tablename__ = "subject_tracks"
    __table_args__ = (UniqueConstraint("student_id", "subject", name="uq_subject_track"),)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_profiles.id")
    )
    subject: Mapped[Subject] = mapped_column(Enum(Subject, native_enum=False))
    current_score: Mapped[int] = mapped_column(Integer, default=0)
    target_score: Mapped[int] = mapped_column(Integer, default=85)
    phase: Mapped[str] = mapped_column(String(80), default="foundation")


class TopicORM(Base):
    __tablename__ = "topics"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    subject: Mapped[Subject] = mapped_column(Enum(Subject, native_enum=False), index=True)
    title: Mapped[str] = mapped_column(String(240))
    spec_year: Mapped[int] = mapped_column(Integer, default=2026)
    task_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Привязка к фазе учебной программы (app/domain/program.py). None — тема вне программы.
    phase: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    program_order: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TaskORM(Base):
    __tablename__ = "tasks"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    subject: Mapped[Subject] = mapped_column(Enum(Subject, native_enum=False), index=True)
    topic_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True, index=True
    )
    task_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    statement: Mapped[str] = mapped_column(Text)
    expected_answer: Mapped[str] = mapped_column(Text)
    solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_category: Mapped[ErrorCategory | None] = mapped_column(
        Enum(ErrorCategory, native_enum=False), nullable=True, index=True
    )
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, native_enum=False), index=True)
    source: Mapped[str] = mapped_column(String(80))
    source_url: Mapped[str | None] = mapped_column(String(700), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(
        String(700), nullable=True, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    topic: Mapped[TopicORM | None] = relationship()


class MissionORM(Base):
    __tablename__ = "missions"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_profiles.id")
    )
    subject: Mapped[Subject] = mapped_column(Enum(Subject, native_enum=False), index=True)
    topic_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True
    )
    task_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(240))
    instructions: Mapped[str] = mapped_column(Text, default="")
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MissionStatus] = mapped_column(
        Enum(MissionStatus, native_enum=False), index=True
    )
    ai_policy: Mapped[AiPolicy] = mapped_column(Enum(AiPolicy, native_enum=False))
    threshold_percent: Mapped[float] = mapped_column(Float, default=80.0)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    timebox_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    topic: Mapped[TopicORM | None] = relationship()
    task: Mapped[TaskORM | None] = relationship()


class AttemptORM(Base):
    __tablename__ = "attempts"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    mission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("missions.id"), index=True
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_profiles.id"), index=True
    )
    kind: Mapped[AttemptKind] = mapped_column(Enum(AttemptKind, native_enum=False))
    mode: Mapped[AttemptMode] = mapped_column(Enum(AttemptMode, native_enum=False))
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_spent_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class EvidenceORM(Base):
    __tablename__ = "evidence"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    attempt_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("attempts.id"), index=True
    )
    mission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("missions.id"), index=True
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_profiles.id"), index=True
    )
    topic_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True, index=True
    )
    status: Mapped[EvidenceStatus] = mapped_column(Enum(EvidenceStatus, native_enum=False))
    score_percent: Mapped[float] = mapped_column(Float)
    error_category: Mapped[ErrorCategory] = mapped_column(
        Enum(ErrorCategory, native_enum=False), index=True
    )
    feedback: Mapped[str] = mapped_column(Text)
    next_action: Mapped[str] = mapped_column(Text)
    model_id: Mapped[str] = mapped_column(String(160))
    prompt_version: Mapped[str] = mapped_column(String(80))
    rubric_version: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ErrorEventORM(Base):
    __tablename__ = "error_events"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_profiles.id"), index=True
    )
    subject: Mapped[Subject] = mapped_column(Enum(Subject, native_enum=False), index=True)
    topic_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True
    )
    mission_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True
    )
    attempt_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("attempts.id"), nullable=True
    )
    evidence_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=True
    )
    category: Mapped[ErrorCategory] = mapped_column(
        Enum(ErrorCategory, native_enum=False), index=True
    )
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_sheet: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[str | None] = mapped_column(
        String(700), nullable=True, unique=True, index=True
    )


class ReviewItemORM(Base):
    __tablename__ = "review_items"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_profiles.id"), index=True
    )
    topic_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("topics.id"), index=True
    )
    due_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus, native_enum=False), index=True)
    source_evidence_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=True
    )
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_sheet: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[str | None] = mapped_column(
        String(700), nullable=True, unique=True, index=True
    )


class ScoreEventORM(Base):
    __tablename__ = "score_events"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_profiles.id"), index=True
    )
    subject: Mapped[Subject] = mapped_column(Enum(Subject, native_enum=False), index=True)
    score: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(80), default="weekly_variant")
    occurred_on: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_sheet: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[str | None] = mapped_column(
        String(700), nullable=True, unique=True, index=True
    )


class CleanSheetEventORM(Base):
    __tablename__ = "clean_sheet_events"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_profiles.id"), index=True
    )
    occurred_on: Mapped[date] = mapped_column(Date, index=True)
    tasks_total: Mapped[int] = mapped_column(Integer)
    clean_sheet_count: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_sheet: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[str | None] = mapped_column(
        String(700), nullable=True, unique=True, index=True
    )


class StudyLogEntryORM(Base):
    __tablename__ = "study_log_entries"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_profiles.id"), index=True
    )
    subject: Mapped[Subject] = mapped_column(Enum(Subject, native_enum=False), index=True)
    occurred_on: Mapped[date] = mapped_column(Date, index=True)
    topic_title: Mapped[str] = mapped_column(String(240))
    tasks_total: Mapped[int] = mapped_column(Integer)
    tasks_correct: Mapped[int] = mapped_column(Integer)
    percent_correct: Mapped[float] = mapped_column(Float)
    status_note: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_sheet: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[str | None] = mapped_column(
        String(700), nullable=True, unique=True, index=True
    )


class MentorNoteORM(Base):
    """Student-facing feedback from the senior mentor (the agent). Published straight to
    the dashboard feed — transparent process, no answer keys. Append-only."""

    __tablename__ = "mentor_notes"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_profiles.id"), index=True
    )
    topic_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True, index=True
    )
    body: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    topic: Mapped[TopicORM | None] = relationship()


class AuditSetORM(Base):
    __tablename__ = "audit_sets"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_profiles.id"), index=True
    )
    week_label: Mapped[str] = mapped_column(String(80))
    prompt: Mapped[str] = mapped_column(Text)
    answer_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
