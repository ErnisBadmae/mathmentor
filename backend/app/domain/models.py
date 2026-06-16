from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.domain.enums import (
    AiPolicy,
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    MissionStatus,
    ReviewStatus,
    Subject,
)


@dataclass(frozen=True)
class StudentProfile:
    id: UUID
    display_name: str
    exam_year: int


@dataclass(frozen=True)
class SubjectTrack:
    id: UUID
    student_id: UUID
    subject: Subject
    current_score: int
    target_score: int
    phase: str


@dataclass(frozen=True)
class Topic:
    id: UUID
    subject: Subject
    title: str
    spec_year: int
    task_number: str | None = None


@dataclass(frozen=True)
class Mission:
    id: UUID
    student_id: UUID
    subject: Subject
    title: str
    topic_id: UUID | None
    status: MissionStatus
    ai_policy: AiPolicy
    threshold_percent: float
    due_date: date | None = None
    timebox_minutes: int | None = None


@dataclass(frozen=True)
class Attempt:
    id: UUID
    mission_id: UUID
    student_id: UUID
    kind: AttemptKind
    mode: AttemptMode
    submitted_at: datetime
    answer_text: str | None = None
    code_text: str | None = None
    time_spent_minutes: int | None = None


@dataclass(frozen=True)
class Evidence:
    id: UUID
    attempt_id: UUID
    mission_id: UUID
    status: EvidenceStatus
    score_percent: float
    error_category: ErrorCategory
    feedback: str
    next_action: str
    model_id: str
    prompt_version: str
    rubric_version: str
    created_at: datetime


@dataclass(frozen=True)
class ReviewItem:
    id: UUID
    student_id: UUID
    topic_id: UUID
    due_date: date
    status: ReviewStatus
    source_evidence_id: UUID
