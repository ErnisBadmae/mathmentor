from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import AiPolicy, AttemptKind, AttemptMode, ErrorCategory, EvidenceStatus, MissionStatus, ReviewStatus, Subject


class StudentOut(BaseModel):
    id: UUID
    display_name: str
    exam_year: int
    model_config = {"from_attributes": True}


class TrackOut(BaseModel):
    subject: Subject
    current_score: int
    target_score: int
    score_gap: int
    phase: str


class TopErrorOut(BaseModel):
    category: ErrorCategory
    count: int


class DashboardOut(BaseModel):
    tracks: list[TrackOut]
    clean_sheet_ratio: float
    top_errors: list[TopErrorOut]
    due_reviews: int


class MissionOut(BaseModel):
    id: UUID
    subject: Subject
    title: str
    instructions: str
    threshold_percent: float
    due_date: date | None = None
    timebox_minutes: int | None = None
    model_config = {"from_attributes": True}


class MissionCreateIn(BaseModel):
    student_id: UUID
    subject: Subject
    title: str = Field(min_length=1, max_length=240)
    instructions: str = ""
    expected_answer: str | None = None
    status: MissionStatus = MissionStatus.ACTIVE
    ai_policy: AiPolicy = AiPolicy.ATTEMPT_FIRST
    threshold_percent: float = Field(default=80.0, ge=0, le=100)
    topic_id: UUID | None = None
    due_date: date | None = None
    timebox_minutes: int | None = Field(default=None, ge=0, le=600)
    source_ref: str | None = None


class MissionUpdateIn(BaseModel):
    subject: Subject | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    instructions: str | None = None
    expected_answer: str | None = None
    status: MissionStatus | None = None
    ai_policy: AiPolicy | None = None
    threshold_percent: float | None = Field(default=None, ge=0, le=100)
    topic_id: UUID | None = None
    due_date: date | None = None
    timebox_minutes: int | None = Field(default=None, ge=0, le=600)
    source_ref: str | None = None


class SubmitAttemptIn(BaseModel):
    mission_id: UUID
    kind: AttemptKind
    mode: AttemptMode
    answer_text: str | None = Field(default=None, max_length=20000)
    code_text: str | None = Field(default=None, max_length=20000)
    time_spent_minutes: int | None = Field(default=None, ge=0, le=600)


class SubmitAttemptOut(BaseModel):
    attempt_id: UUID
    evidence_id: UUID
    status: EvidenceStatus
    score_percent: float
    error_category: ErrorCategory
    feedback: str
    next_action: str


class ErrorEventOut(BaseModel):
    id: UUID
    subject: Subject
    topic_id: UUID | None = None
    topic_title: str | None = None
    mission_id: UUID | None = None
    attempt_id: UUID | None = None
    evidence_id: UUID | None = None
    category: ErrorCategory
    detail: str
    created_at: datetime
    source_ref: str | None = None


class ReviewItemOut(BaseModel):
    id: UUID
    student_id: UUID
    topic_id: UUID
    topic_title: str
    subject: Subject
    due_date: date
    status: ReviewStatus
    source_evidence_id: UUID | None = None
    source_ref: str | None = None


class ReviewResultIn(BaseModel):
    passed: bool


class ScoreEventIn(BaseModel):
    subject: Subject
    score: int = Field(ge=0, le=100)
    kind: str = Field(default="weekly_variant", max_length=80)
    occurred_on: date | None = None
    note: str | None = None


class ScoreEventOut(BaseModel):
    id: UUID
    student_id: UUID
    subject: Subject
    score: int
    kind: str
    occurred_on: date
    note: str | None = None
    model_config = {"from_attributes": True}


class ManualReviewOut(BaseModel):
    id: UUID
    attempt_id: UUID
    mission_id: UUID
    mission_title: str
    topic_id: UUID | None = None
    topic_title: str | None = None
    status: EvidenceStatus
    score_percent: float
    error_category: ErrorCategory
    feedback: str
    next_action: str
    model_id: str
    prompt_version: str
    rubric_version: str
    created_at: datetime


class ManualDecisionIn(BaseModel):
    status: EvidenceStatus
    score_percent: float | None = Field(default=None, ge=0, le=100)
    error_category: ErrorCategory | None = None
    feedback: str | None = None
    next_action: str | None = None
