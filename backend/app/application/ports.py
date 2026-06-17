from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from app.domain.enums import (
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    ReviewStatus,
    Subject,
)


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
    instructions: str | None = None


@dataclass(frozen=True)
class EvidenceDraft:
    score_percent: float
    error_category: ErrorCategory
    feedback: str
    next_action: str
    model_id: str
    prompt_version: str
    rubric_version: str
    status: EvidenceStatus | None = None


class EvidenceReviewer(Protocol):
    async def review_attempt(self, attempt: AttemptForReview) -> EvidenceDraft: ...


class UnitOfWork(Protocol):
    students: "StudentRepository"
    missions: "MissionRepository"
    attempts: "AttemptRepository"
    evidence: "EvidenceRepository"
    dashboard: "DashboardRepository"
    errors: "ErrorRepository"
    reviews: "ReviewRepository"
    scores: "ScoreRepository"
    topics: "TopicRepository"
    tasks: "TaskRepository"

    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class StudentRepository(Protocol):
    def get_current(self) -> object: ...


class MissionRepository(Protocol):
    def get_for_attempt(self, mission_id: UUID) -> object: ...
    def list_today(self, student_id: UUID) -> list[object]: ...
    def create(self, values: dict[str, object]) -> object: ...
    def latest_for_topic(self, topic_id: UUID) -> object | None: ...
    def update(self, mission_id: UUID, values: dict[str, object]) -> object: ...
    def mark_done(self, mission_id: UUID) -> None: ...
    def mark_repeat(self, mission_id: UUID) -> None: ...


class AttemptRepository(Protocol):
    def add(self, values: dict[str, object]) -> object: ...


class EvidenceRepository(Protocol):
    def add(self, values: dict[str, object]) -> object: ...
    def get(self, evidence_id: UUID) -> object: ...
    def list_manual_reviews(self, student_id: UUID) -> list[dict[str, object]]: ...
    def add_error_event(self, values: dict[str, object]) -> None: ...
    def schedule_reviews(self, values: list[dict[str, object]]) -> None: ...


class DashboardRepository(Protocol):
    def get_dashboard(self, student_id: UUID) -> dict[str, object]: ...
    def list_diagnostics(self, student_id: UUID) -> list[dict[str, object]]: ...


class ErrorRepository(Protocol):
    def list_errors(
        self,
        student_id: UUID,
        subject: Subject | None = None,
        category: ErrorCategory | None = None,
    ) -> list[dict[str, object]]: ...


class ReviewRepository(Protocol):
    def list_reviews(
        self,
        student_id: UUID,
        status: ReviewStatus | None = None,
        due_on_or_before: date | None = None,
    ) -> list[dict[str, object]]: ...

    def mark_result(self, review_id: UUID, status: ReviewStatus) -> object: ...


class ScoreRepository(Protocol):
    def add_event(self, values: dict[str, object]) -> object: ...


class TopicRepository(Protocol):
    def get(self, topic_id: UUID) -> object | None: ...
    def list_topic_lifecycle(self, student_id: UUID) -> list[dict[str, object]]: ...
    def list_program(self, student_id: UUID) -> list[dict[str, object]]: ...


class TaskRepository(Protocol):
    def get(self, task_id: UUID) -> object: ...
    def add(self, values: dict[str, object]) -> object: ...
