from datetime import UTC, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.application.ports import AttemptForReview, EvidenceDraft, EvidenceReviewer, UnitOfWork
from app.domain.enums import (
    AiPolicy,
    ErrorCategory,
    EvidenceStatus,
    MissionStatus,
    ReviewStatus,
    TaskStatus,
    TopicState,
)
from app.domain.policies import evidence_status, review_due_dates, review_result_to_status
from app.domain.program import PHASES, current_phase_key


class LearningService:
    def __init__(
        self, uow: UnitOfWork, reviewer: EvidenceReviewer, local_timezone: str = "Europe/Moscow"
    ) -> None:
        self._uow = uow
        self._reviewer = reviewer
        self._local_timezone = local_timezone

    def _today(self):
        return datetime.now(ZoneInfo(self._local_timezone)).date()

    def _add_error_event(
        self,
        mission: object,
        attempt_id: UUID,
        evidence: object,
        detail: str,
        category: ErrorCategory,
    ) -> None:
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

    def _apply_progression(
        self, mission: object, evidence: object, category: ErrorCategory, feedback: str
    ) -> None:
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
        return [
            self._mission_payload(mission) for mission in self._uow.missions.list_today(student_id)
        ]

    def _mission_payload(self, mission: object) -> dict[str, object]:
        task = getattr(mission, "task", None)
        statement = task.statement if task is not None else None
        return {
            "id": mission.id,
            "subject": mission.subject,
            "title": mission.title,
            "instructions": mission.instructions,
            "statement": statement,
            "threshold_percent": mission.threshold_percent,
            "due_date": mission.due_date,
            "timebox_minutes": mission.timebox_minutes,
        }

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

    def list_topic_lifecycle(self, student_id: UUID) -> list[dict[str, object]]:
        return self._uow.topics.list_topic_lifecycle(student_id)

    def list_program_progress(self, student_id: UUID) -> list[dict[str, object]]:
        rows = self._uow.topics.list_program(student_id)
        by_phase: dict[str, list[dict[str, object]]] = {}
        for row in rows:
            by_phase.setdefault(row["phase"], []).append(row)
        current = current_phase_key(self._today())
        in_progress_states = (
            TopicState.IN_WORK,
            TopicState.UNDER_REVIEW,
            TopicState.BACK_TO_WORK,
        )
        phases_out: list[dict[str, object]] = []
        for phase in PHASES:
            topics = sorted(
                by_phase.get(phase.key, []),
                key=lambda r: (r["program_order"] or 0, r["topic_title"]),
            )
            phases_out.append(
                {
                    "key": phase.key,
                    "label": phase.label,
                    "start_date": phase.start,
                    "end_date": phase.end,
                    "is_current": phase.key == current,
                    "coverage": {
                        "confirmed": sum(1 for t in topics if t["state"] == TopicState.CONFIRMED),
                        "in_progress": sum(1 for t in topics if t["state"] in in_progress_states),
                        "open": sum(1 for t in topics if t["state"] == TopicState.OPEN),
                        "total": len(topics),
                    },
                    "topics": topics,
                }
            )
        return phases_out

    def create_mission(self, values: dict[str, object]) -> object:
        mission = self._uow.missions.create({**self._prepare_task_link(values), "id": uuid4()})
        self._uow.commit()
        return self._mission_payload(mission)

    def update_mission(self, mission_id: UUID, values: dict[str, object]) -> object:
        existing = self._uow.missions.get_for_attempt(mission_id)
        values = self._prepare_task_link(values, existing)
        mission = self._uow.missions.update(mission_id, values)
        self._uow.commit()
        return self._mission_payload(mission)

    def _prepare_task_link(
        self,
        values: dict[str, object],
        existing_mission: object | None = None,
    ) -> dict[str, object]:
        task_id = values.get("task_id")
        if task_id is None:
            return values
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        task = self._uow.tasks.get(task_id)
        if task.status != TaskStatus.APPROVED:
            raise ValueError("Mission can only reference an approved task.")
        subject = values.get("subject") or getattr(existing_mission, "subject", None)
        if subject is not None and subject != task.subject:
            raise ValueError("Mission subject must match the task subject.")
        topic_id = values.get("topic_id") or getattr(existing_mission, "topic_id", None)
        if task.topic_id is not None:
            if topic_id is not None and topic_id != task.topic_id:
                raise ValueError("Mission topic must match the task topic.")
            values["topic_id"] = task.topic_id
        return values

    def record_score_event(self, values: dict[str, object]) -> object:
        event = self._uow.scores.add_event(
            {**values, "id": uuid4(), "occurred_on": values.get("occurred_on") or self._today()}
        )
        self._uow.commit()
        return event

    def record_review_result(self, review_id: UUID, passed: bool) -> object:
        item = self._uow.reviews.mark_result(review_id, review_result_to_status(passed))
        if not passed:
            self._create_back_to_work_mission(item)
        self._uow.commit()
        return item

    def _create_back_to_work_mission(self, review_item: object) -> None:
        """A failed review is not terminal (§8): open a fresh ACTIVE mission for the same
        topic with default fields, preserving history instead of reopening a DONE mission.
        Defaults stay valid even when the review came from import with no prior mission."""
        topic = self._uow.topics.get(review_item.topic_id)
        latest = self._uow.missions.latest_for_topic(review_item.topic_id)
        topic_title = getattr(topic, "title", None)
        self._uow.missions.create(
            {
                "id": uuid4(),
                "student_id": review_item.student_id,
                "subject": topic.subject if topic is not None else latest.subject,
                "topic_id": review_item.topic_id,
                "title": f"Повтор: {topic_title}" if topic_title else "Повтор темы",
                "instructions": (
                    "2-3 холодные задачи по теме без ИИ и шпаргалки. Причина: провален возврат."
                ),
                "status": MissionStatus.ACTIVE,
                "ai_policy": latest.ai_policy if latest is not None else AiPolicy.ATTEMPT_FIRST,
                "threshold_percent": latest.threshold_percent if latest is not None else 80.0,
                "due_date": self._today(),
            }
        )

    async def submit_attempt(self, values: dict[str, object]) -> dict[str, object]:
        mission_id = values["mission_id"]
        if not isinstance(mission_id, UUID):
            raise TypeError("mission_id must be a UUID")

        mission = self._uow.missions.get_for_attempt(mission_id)
        task = self._uow.tasks.get(mission.task_id) if mission.task_id is not None else None
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
                expected_answer=task.expected_answer
                if task is not None
                else mission.expected_answer,
                threshold_percent=mission.threshold_percent,
                instructions=self._review_instructions(mission, task),
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

    def _review_instructions(self, mission: object, task: object | None) -> str:
        if task is None:
            return mission.instructions
        return f"Task:\n{task.statement}\n\nInstructions:\n{mission.instructions}"

    def apply_manual_decision(
        self, evidence_id: UUID, values: dict[str, object]
    ) -> dict[str, object]:
        source = self._uow.evidence.get(evidence_id)
        mission = self._uow.missions.get_for_attempt(source.mission_id)
        status = values["status"]
        if status == EvidenceStatus.NEEDS_MANUAL_REVIEW:
            raise ValueError("manual decision must be passed or failed")
        created_at = datetime.now(UTC)
        score_percent = values.get("score_percent")
        if score_percent is None:
            score_percent = 100.0 if status == EvidenceStatus.PASSED else 0.0
        category = values.get("error_category") or (
            ErrorCategory.NONE if status == EvidenceStatus.PASSED else ErrorCategory.OTHER
        )
        feedback = values.get("feedback") or "Manual guardian review applied."
        next_action = values.get("next_action") or (
            "Topic accepted." if status == EvidenceStatus.PASSED else "Repeat this mission."
        )
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
            next_action = (
                "Do three short equations focused only on moving terms across the equality sign."
            )
        elif "одз" in text and "не учитываю" in text:
            category = ErrorCategory.ODZ_LOGIC
            status = EvidenceStatus.FAILED
            score = 50.0
            feedback = (
                "The domain restriction was applied too broadly. "
                "Check each candidate root separately."
            )
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
