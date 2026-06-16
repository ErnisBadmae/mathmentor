from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.enums import AttemptKind, AttemptMode, ErrorCategory, Subject


@dataclass(frozen=True)
class AttemptForReview:
    subject: Subject
    mission_title: str
    topic_title: str | None
    kind: AttemptKind
    mode: AttemptMode
    answer_text: str | None
    code_text: str | None
    expected_answer: str | None
    threshold_percent: float


@dataclass(frozen=True)
class EvidenceDraft:
    score_percent: float
    error_category: ErrorCategory
    feedback: str
    next_action: str
    model_id: str
    prompt_version: str
    rubric_version: str


class EvidenceReviewer(Protocol):
    async def review_attempt(self, attempt: AttemptForReview) -> EvidenceDraft: ...


class UnitOfWork(Protocol):
    missions: "MissionRepository"
    attempts: "AttemptRepository"
    evidence: "EvidenceRepository"
    dashboard: "DashboardRepository"

    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class MissionRepository(Protocol):
    def get_for_attempt(self, mission_id: UUID) -> object: ...
    def list_today(self, student_id: UUID) -> list[object]: ...
    def mark_done(self, mission_id: UUID) -> None: ...
    def mark_repeat(self, mission_id: UUID) -> None: ...


class AttemptRepository(Protocol):
    def add(self, values: dict[str, object]) -> object: ...


class EvidenceRepository(Protocol):
    def add(self, values: dict[str, object]) -> object: ...
    def add_error_event(self, values: dict[str, object]) -> None: ...
    def schedule_reviews(self, values: list[dict[str, object]]) -> None: ...


class DashboardRepository(Protocol):
    def get_dashboard(self, student_id: UUID) -> dict[str, object]: ...
