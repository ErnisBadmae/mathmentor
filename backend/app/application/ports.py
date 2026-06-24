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


@dataclass(frozen=True)
class AiAssessment:
    """Сырой вывод ИИ-судьи. Без бизнес-политики (exact-авторитет, fallback, sanitize) — её
    применяет ``LearningService``; здесь только мнение модели + провенанс.

    ``extracted_answer`` — финальный ответ, который ИИ вытащил из решения ученика (формат
    «покажи ход»): по нему сервис детерминированно заземляет вердикт. ``feedback`` уже
    учитывает метод (если ответ верный, но ход неверный — ИИ это отмечает)."""

    equivalent: bool
    extracted_answer: str | None
    feedback: str
    model_id: str
    prompt_version: str
    rubric_version: str


class ShortAnswerJudge(Protocol):
    async def assess(
        self, statement: str, correct_answer: str, student_answer: str | None
    ) -> AiAssessment | None: ...


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
    mentor_notes: "MentorNoteRepository"

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
    def list_attempt_history(
        self, student_id: UUID, topic_id: UUID | None = None, limit: int = 50
    ) -> list[dict[str, object]]: ...


class DashboardRepository(Protocol):
    def get_dashboard(self, student_id: UUID) -> dict[str, object]: ...
    def list_diagnostics(self, student_id: UUID) -> list[dict[str, object]]: ...
    def add_diagnostic(self, values: dict[str, object]) -> object: ...


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

    def get(self, review_id: UUID) -> object | None: ...

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
    def approve(self, task_id: UUID) -> object: ...
    def list_tasks(self, status: object | None = None) -> list[dict[str, object]]: ...
    def list_gradable(self, subject: Subject, topic_id: UUID | None = None) -> list[object]: ...
    def list_approved_for_topic(
        self, topic_id: UUID, exclude_assigned_to: UUID | None = None
    ) -> list[object]: ...


class MentorNoteRepository(Protocol):
    def add(self, values: dict[str, object]) -> object: ...
    def list_recent(self, student_id: UUID, limit: int = 20) -> list[dict[str, object]]: ...
    def list_undelivered(self, student_id: UUID) -> list[dict[str, object]]: ...
    def mark_delivered(self, note_ids: list[UUID]) -> None: ...
