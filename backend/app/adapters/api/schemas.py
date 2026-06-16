from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import AttemptKind, AttemptMode, ErrorCategory, EvidenceStatus, Subject


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
