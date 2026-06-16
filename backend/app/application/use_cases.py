from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from app.application.ports import AttemptForReview, EvidenceDraft, EvidenceReviewer, UnitOfWork
from app.domain.enums import ErrorCategory, EvidenceStatus, ReviewStatus
from app.domain.policies import evidence_status, review_due_dates


class LearningService:
    def __init__(self, uow: UnitOfWork, reviewer: EvidenceReviewer) -> None:
        self._uow = uow
        self._reviewer = reviewer

    def get_dashboard(self, student_id: UUID) -> dict[str, object]:
        return self._uow.dashboard.get_dashboard(student_id)

    def list_today(self, student_id: UUID) -> list[object]:
        return self._uow.missions.list_today(student_id)

    async def submit_attempt(self, values: dict[str, object]) -> dict[str, object]:
        mission_id = values["mission_id"]
        if not isinstance(mission_id, UUID):
            raise TypeError("mission_id must be a UUID")

        mission = self._uow.missions.get_for_attempt(mission_id)
        attempt_id = uuid4()
        submitted_at = datetime.now(UTC)
        attempt = self._uow.attempts.add(
            {
                "id": attempt_id,
                "mission_id": mission.id,
                "student_id": mission.student_id,
                "kind": values["kind"],
                "mode": values["mode"],
                "answer_text": values.get("answer_text"),
                "code_text": values.get("code_text"),
                "time_spent_minutes": values.get("time_spent_minutes"),
                "submitted_at": submitted_at,
            }
        )

        draft = await self._reviewer.review_attempt(
            AttemptForReview(
                subject=mission.subject,
                mission_title=mission.title,
                topic_title=getattr(mission.topic, "title", None),
                kind=attempt.kind,
                mode=attempt.mode,
                answer_text=attempt.answer_text,
                code_text=attempt.code_text,
                expected_answer=mission.expected_answer,
                threshold_percent=mission.threshold_percent,
            )
        )
        status = evidence_status(draft.score_percent, mission.threshold_percent)
        evidence = self._uow.evidence.add(
            {
                "id": uuid4(),
                "attempt_id": attempt.id,
                "mission_id": mission.id,
                "student_id": mission.student_id,
                "status": status,
                "score_percent": draft.score_percent,
                "error_category": draft.error_category,
                "feedback": draft.feedback,
                "next_action": draft.next_action,
                "model_id": draft.model_id,
                "prompt_version": draft.prompt_version,
                "rubric_version": draft.rubric_version,
                "created_at": submitted_at,
            }
        )
        if draft.error_category != ErrorCategory.NONE:
            self._uow.evidence.add_error_event(
                {
                    "id": uuid4(),
                    "student_id": mission.student_id,
                    "subject": mission.subject,
                    "topic_id": mission.topic_id,
                    "mission_id": mission.id,
                    "attempt_id": attempt.id,
                    "evidence_id": evidence.id,
                    "category": draft.error_category,
                    "detail": draft.feedback,
                    "created_at": submitted_at,
                }
            )
        if status == EvidenceStatus.PASSED:
            self._uow.missions.mark_done(mission.id)
            if mission.topic_id is not None:
                plus_7, plus_30 = review_due_dates(date.today())
                self._uow.evidence.schedule_reviews(
                    [
                        {"id": uuid4(), "student_id": mission.student_id, "topic_id": mission.topic_id, "due_date": plus_7, "status": ReviewStatus.DUE, "source_evidence_id": evidence.id},
                        {"id": uuid4(), "student_id": mission.student_id, "topic_id": mission.topic_id, "due_date": plus_30, "status": ReviewStatus.DUE, "source_evidence_id": evidence.id},
                    ]
                )
        else:
            self._uow.missions.mark_repeat(mission.id)

        self._uow.commit()
        return {
            "attempt_id": attempt.id,
            "evidence_id": evidence.id,
            "status": status,
            "score_percent": draft.score_percent,
            "error_category": draft.error_category,
            "feedback": draft.feedback,
            "next_action": draft.next_action,
        }


class RuleBasedReviewer:
    model_id = "rule-based-local"
    prompt_version = "none"
    rubric_version = "ege-mentor-v1"

    async def review_attempt(self, attempt: AttemptForReview) -> EvidenceDraft:
        text = " ".join([attempt.answer_text or "", attempt.code_text or ""]).lower()
        category = ErrorCategory.NONE
        score = 100.0
        feedback = "Attempt recorded. Manual review can refine this feedback."
        next_action = "Keep the topic in normal rotation."
        if "не знаю" in text or not text.strip():
            category = ErrorCategory.UNKNOWN_METHOD
            score = 0.0
            feedback = "No independent solution was provided."
            next_action = "Repeat the topic with one worked example, then submit a clean attempt."
        elif "-1-3" in text or "2х=8" in text or "2x=8" in text:
            category = ErrorCategory.SIGN_TRANSFER
            score = 50.0
            feedback = "The method is close, but signs or term transfer changed the answer."
            next_action = "Do three short equations focused only on moving terms across the equality sign."
        elif "одз" in text and "не учитываю" in text:
            category = ErrorCategory.ODZ_LOGIC
            score = 50.0
            feedback = "The domain restriction was applied too broadly. Check each candidate root separately."
            next_action = "Practice two examples where ODZ removes one root but keeps the other."
        return EvidenceDraft(score, category, feedback, next_action, self.model_id, self.prompt_version, self.rubric_version)
