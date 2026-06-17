from datetime import UTC, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.application.ports import AttemptForReview, EvidenceDraft, EvidenceReviewer, UnitOfWork
from app.domain.enums import ErrorCategory, EvidenceStatus, ReviewStatus
from app.domain.policies import evidence_status, review_due_dates, review_result_to_status


class LearningService:
    def __init__(self, uow: UnitOfWork, reviewer: EvidenceReviewer, local_timezone: str = "Europe/Moscow") -> None:
        self._uow = uow
        self._reviewer = reviewer
        self._local_timezone = local_timezone

    def _today(self):
        return datetime.now(ZoneInfo(self._local_timezone)).date()

    def _add_error_event(self, mission: object, attempt_id: UUID, evidence: object, detail: str, category: ErrorCategory) -> None:
        self._uow.evidence.add_error_event(
            {
                "id": uuid4(),
                "student_id": mission.student_id,
                "subject": mission.subject,
                "topic_id": mission.topic_id,
                "mission_id": mission.id,
                "attempt_id": attempt_id,
                "evidence_id": evidence.id,
                "category": category,
                "detail": detail,
                "created_at": evidence.created_at,
            }
        )

    def _apply_progression(self, mission: object, evidence: object, category: ErrorCategory, feedback: str) -> None:
        if evidence.status == EvidenceStatus.PASSED:
            self._uow.missions.mark_done(mission.id)
            if mission.topic_id is not None:
                plus_7, plus_30 = review_due_dates(self._today())
                self._uow.evidence.schedule_reviews(
                    [
                        {
                            "id": uuid4(),
                            "student_id": mission.student_id,
                            "topic_id": mission.topic_id,
                            "due_date": plus_7,
                            "status": ReviewStatus.DUE,
                            "source_evidence_id": evidence.id,
                        },
                        {
                            "id": uuid4(),
                            "student_id": mission.student_id,
                            "topic_id": mission.topic_id,
                            "due_date": plus_30,
                            "status": ReviewStatus.DUE,
                            "source_evidence_id": evidence.id,
                        },
                    ]
                )
        elif evidence.status == EvidenceStatus.FAILED:
            if category != ErrorCategory.NONE:
                self._add_error_event(mission, evidence.attempt_id, evidence, feedback, category)
            self._uow.missions.mark_repeat(mission.id)

    def get_dashboard(self, student_id: UUID) -> dict[str, object]:
        return self._uow.dashboard.get_dashboard(student_id)

    def get_current_student(self) -> object:
        return self._uow.students.get_current()

    def list_today(self, student_id: UUID) -> list[object]:
        return self._uow.missions.list_today(student_id)

    def list_errors(
        self,
        student_id: UUID,
        subject: object | None = None,
        category: ErrorCategory | None = None,
    ) -> list[dict[str, object]]:
        return self._uow.errors.list_errors(student_id, subject, category)

    def list_reviews(
        self,
        student_id: UUID,
        status: ReviewStatus | None = None,
        due_only: bool = False,
    ) -> list[dict[str, object]]:
        return self._uow.reviews.list_reviews(
            student_id,
            status=status,
            due_on_or_before=self._today() if due_only else None,
        )

    def list_manual_reviews(self, student_id: UUID) -> list[dict[str, object]]:
        return self._uow.evidence.list_manual_reviews(student_id)

    def create_mission(self, values: dict[str, object]) -> object:
        mission = self._uow.missions.create({**values, "id": uuid4()})
        self._uow.commit()
        return mission

    def update_mission(self, mission_id: UUID, values: dict[str, object]) -> object:
        mission = self._uow.missions.update(mission_id, values)
        self._uow.commit()
        return mission

    def record_score_event(self, values: dict[str, object]) -> object:
        event = self._uow.scores.add_event({**values, "id": uuid4(), "occurred_on": values.get("occurred_on") or self._today()})
        self._uow.commit()
        return event

    def record_review_result(self, review_id: UUID, passed: bool) -> object:
        item = self._uow.reviews.mark_result(review_id, review_result_to_status(passed))
        self._uow.commit()
        return item

    async def submit_attempt(self, values: dict[str, object]) -> dict[str, object]:
        mission_id = values["mission_id"]
        if not isinstance(mission_id, UUID):
            raise TypeError("mission_id must be a UUID")

        mission = self._uow.missions.get_for_attempt(mission_id)
        submitted_at = datetime.now(UTC)
        attempt = self._uow.attempts.add(
            {
                "id": uuid4(),
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
                instructions=mission.instructions,
            )
        )
        status = draft.status or evidence_status(draft.score_percent, mission.threshold_percent)
        evidence = self._uow.evidence.add(
            {
                "id": uuid4(),
                "attempt_id": attempt.id,
                "mission_id": mission.id,
                "student_id": mission.student_id,
                "topic_id": mission.topic_id,
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
        self._apply_progression(mission, evidence, draft.error_category, draft.feedback)

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

    def apply_manual_decision(self, evidence_id: UUID, values: dict[str, object]) -> dict[str, object]:
        source = self._uow.evidence.get(evidence_id)
        mission = self._uow.missions.get_for_attempt(source.mission_id)
        status = values["status"]
        if status == EvidenceStatus.NEEDS_MANUAL_REVIEW:
            raise ValueError("manual decision must be passed or failed")
        created_at = datetime.now(UTC)
        score_percent = values.get("score_percent")
        if score_percent is None:
            score_percent = 100.0 if status == EvidenceStatus.PASSED else 0.0
        category = values.get("error_category") or (ErrorCategory.NONE if status == EvidenceStatus.PASSED else ErrorCategory.OTHER)
        feedback = values.get("feedback") or "Manual guardian review applied."
        next_action = values.get("next_action") or ("Topic accepted." if status == EvidenceStatus.PASSED else "Repeat this mission.")
        evidence = self._uow.evidence.add(
            {
                "id": uuid4(),
                "attempt_id": source.attempt_id,
                "mission_id": source.mission_id,
                "student_id": source.student_id,
                "topic_id": source.topic_id,
                "status": status,
                "score_percent": score_percent,
                "error_category": category,
                "feedback": feedback,
                "next_action": next_action,
                "model_id": "manual-review",
                "prompt_version": "manual",
                "rubric_version": source.rubric_version,
                "created_at": created_at,
            }
        )
        self._apply_progression(mission, evidence, category, feedback)
        self._uow.commit()
        return {
            "attempt_id": evidence.attempt_id,
            "evidence_id": evidence.id,
            "status": evidence.status,
            "score_percent": evidence.score_percent,
            "error_category": evidence.error_category,
            "feedback": evidence.feedback,
            "next_action": evidence.next_action,
        }


class RuleBasedReviewer:
    model_id = "rule-based-local"
    prompt_version = "none"
    rubric_version = "ege-mentor-v1"

    async def review_attempt(self, attempt: AttemptForReview) -> EvidenceDraft:
        text = " ".join([attempt.answer_text or "", attempt.code_text or ""]).lower()
        category = ErrorCategory.NONE
        score = 0.0
        status = EvidenceStatus.NEEDS_MANUAL_REVIEW
        feedback = "Attempt recorded. Manual review is required because LLM review is disabled."
        next_action = "Guardian should mark this attempt passed or failed before changing the plan."
        if "не знаю" in text or not text.strip():
            category = ErrorCategory.UNKNOWN_METHOD
            status = EvidenceStatus.FAILED
            feedback = "No independent solution was provided."
            next_action = "Repeat the topic with one worked example, then submit a clean attempt."
        elif "-1-3" in text or "2x=8" in text:
            category = ErrorCategory.SIGN_TRANSFER
            status = EvidenceStatus.FAILED
            score = 50.0
            feedback = "The method is close, but signs or term transfer changed the answer."
            next_action = "Do three short equations focused only on moving terms across the equality sign."
        elif "одз" in text and "не учитываю" in text:
            category = ErrorCategory.ODZ_LOGIC
            status = EvidenceStatus.FAILED
            score = 50.0
            feedback = "The domain restriction was applied too broadly. Check each candidate root separately."
            next_action = "Practice two examples where ODZ removes one root but keeps the other."
        return EvidenceDraft(
            score,
            category,
            feedback,
            next_action,
            self.model_id,
            self.prompt_version,
            self.rubric_version,
            status,
        )
