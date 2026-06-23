import random
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
    Subject,
    TaskStatus,
    TopicState,
)
from app.domain.policies import (
    answer_is_correct,
    evidence_status,
    review_due_dates,
    review_result_to_status,
)
from app.domain.program import PHASES, current_phase_key

SLICE_SUBJECT_LABEL = {
    Subject.MATH_PROFILE: "Профматематика",
    Subject.INFORMATICS: "Информатика",
}


class LearningService:
    def __init__(
        self, uow: UnitOfWork, reviewer: EvidenceReviewer, local_timezone: str = "Europe/Moscow"
    ) -> None:
        self._uow = uow
        self._reviewer = reviewer
        self._local_timezone = local_timezone

    def _today(self):
        return datetime.now(ZoneInfo(self._local_timezone)).date()

    def _resolve_score(
        self,
        *,
        threshold_percent: float,
        reviewer_score_percent: float | None = None,
        explicit_score_percent: float | None = None,
        tasks_total: int | None = None,
        tasks_correct: int | None = None,
        explicit_status: EvidenceStatus | None = None,
    ) -> tuple[float, EvidenceStatus]:
        if (tasks_total is None) != (tasks_correct is None):
            raise ValueError("tasks_total and tasks_correct must be provided together")
        if tasks_total is not None and tasks_correct is not None:
            if tasks_correct > tasks_total:
                raise ValueError("tasks_correct cannot exceed tasks_total")
            score_percent = 0.0 if tasks_total == 0 else tasks_correct / tasks_total * 100
            return score_percent, evidence_status(score_percent, threshold_percent)
        if explicit_score_percent is not None:
            if explicit_status is not None:
                return explicit_score_percent, explicit_status
            return explicit_score_percent, evidence_status(explicit_score_percent, threshold_percent)
        if reviewer_score_percent is None:
            raise ValueError("score_percent is required when reviewer score is absent")
        return reviewer_score_percent, explicit_status or evidence_status(
            reviewer_score_percent, threshold_percent
        )

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
        data = self._uow.dashboard.get_dashboard(student_id)
        data["mentor_notes"] = self._uow.mentor_notes.list_recent(student_id)
        return data

    def publish_feedback(self, values: dict[str, object]) -> dict[str, object]:
        """Publish a student-facing mentor note straight to the dashboard feed."""
        note = self._uow.mentor_notes.add(
            {
                "id": uuid4(),
                "student_id": values["student_id"],
                "topic_id": values.get("topic_id"),
                "body": values["body"],
                "source_ref": values.get("source_ref"),
                "created_at": datetime.now(UTC),
            }
        )
        self._uow.commit()
        return {
            "id": note.id,
            "body": note.body,
            "topic_id": note.topic_id,
            "created_at": note.created_at,
        }

    def get_current_student(self) -> object:
        return self._uow.students.get_current()

    def list_today(self, student_id: UUID) -> list[object]:
        return [
            self._mission_payload(mission) for mission in self._uow.missions.list_today(student_id)
        ]

    @staticmethod
    def _is_drill(mission: object) -> bool:
        """Часть-1 дрилл (мгновенная точная проверка) помечается префиксом source_ref."""
        source_ref = getattr(mission, "source_ref", None)
        return bool(source_ref) and source_ref.startswith("daily:")

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

    def list_daily_drill(self, student_id: UUID) -> list[dict[str, object]]:
        """Очередь Telegram-дрилла: только открытые daily:-миссии со связанной задачей.
        Отдельная поверхность — чтобы в чат не попали части 2 / операторские миссии."""
        return [
            self._mission_payload(mission)
            for mission in self._uow.missions.list_today(student_id)
            if self._is_drill(mission) and getattr(mission, "task", None) is not None
        ]

    def _grade_exact_answer(self, answer_text: str | None, task: object) -> EvidenceDraft:
        """Вердикт дрилла: точное совпадение короткого ответа, мгновенно, без LLM."""
        if answer_is_correct(answer_text, task.expected_answer):
            return EvidenceDraft(
                score_percent=100.0,
                error_category=ErrorCategory.NONE,
                feedback="Верно.",
                next_action="Тема засчитана.",
                model_id="exact-answer",
                prompt_version="none",
                rubric_version="ege-mentor-v1",
                status=EvidenceStatus.PASSED,
            )
        return EvidenceDraft(
            score_percent=0.0,
            error_category=task.error_category or ErrorCategory.OTHER,
            feedback="Неверный ответ.",
            next_action="Повтори задачу и реши заново.",
            model_id="exact-answer",
            prompt_version="none",
            rubric_version="ege-mentor-v1",
            status=EvidenceStatus.FAILED,
        )

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
            for topic in topics:
                bank = topic["tasks_in_bank"]
                # progress by the task bank (user choice): solved / bank tasks, or None.
                topic["percent"] = round(topic["solved_count"] / bank * 100) if bank else None
            confirmed = sum(1 for t in topics if t["state"] == TopicState.CONFIRMED)
            total = len(topics)
            phases_out.append(
                {
                    "key": phase.key,
                    "label": phase.label,
                    "start_date": phase.start,
                    "end_date": phase.end,
                    "is_current": phase.key == current,
                    "percent": round(confirmed / total * 100) if total else 0,
                    "coverage": {
                        "confirmed": confirmed,
                        "in_progress": sum(1 for t in topics if t["state"] in in_progress_states),
                        "open": sum(1 for t in topics if t["state"] == TopicState.OPEN),
                        "total": total,
                    },
                    "topics": topics,
                }
            )
        return phases_out

    def list_diagnostics(self, student_id: UUID) -> list[dict[str, object]]:
        return self._uow.dashboard.list_diagnostics(student_id)

    def list_attempt_history(
        self, student_id: UUID, topic_id: UUID | None = None, limit: int = 50
    ) -> list[dict[str, object]]:
        return self._uow.evidence.list_attempt_history(student_id, topic_id, limit)

    def list_tasks(self, status: TaskStatus | None = None) -> list[dict[str, object]]:
        return self._uow.tasks.list_tasks(status)

    def add_task(self, values: dict[str, object]) -> object:
        """Add a task to the bank as DRAFT by default (senior model authors offline)."""
        payload = {
            "id": uuid4(),
            "subject": values["subject"],
            "topic_id": values.get("topic_id"),
            "task_number": values.get("task_number"),
            "statement": values["statement"],
            "expected_answer": values["expected_answer"],
            "solution": values.get("solution"),
            "error_category": values.get("error_category"),
            "status": values.get("status") or TaskStatus.DRAFT,
            "source": values.get("source") or "agent",
            "source_url": values.get("source_url"),
            "model_id": values.get("model_id"),
            "prompt_version": values.get("prompt_version"),
            "source_ref": values.get("source_ref"),
            "created_at": datetime.now(UTC),
        }
        task = self._uow.tasks.add(payload)
        self._uow.commit()
        return task

    def approve_task(self, task_id: UUID) -> object:
        task = self._uow.tasks.approve(task_id)
        self._uow.commit()
        return task

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

    def draw_slice(self, subject: Subject, size: int) -> list[dict[str, object]]:
        """Draw a knowledge slice: a random sample of approved, exact-answer tasks.
        Returns statements only — the answer key never leaves the backend (§5)."""
        pool = self._uow.tasks.list_gradable(subject)
        chosen = random.sample(pool, min(size, len(pool)))
        return [
            {"task_id": task.id, "task_number": task.task_number, "statement": task.statement}
            for task in chosen
        ]

    def grade_slice(
        self, student_id: UUID, subject: Subject, items: list[dict[str, object]]
    ) -> dict[str, object]:
        """Grade a slice deterministically by exact-answer match (no LLM). Records one
        aggregate study-log diagnostic (§17a) + an error event per miss (§13). A slice is a
        topic_check (§11): it does not create a score event, so current_score is untouched."""
        now = datetime.now(UTC)
        results: list[dict[str, object]] = []
        correct = 0
        for item in items:
            task_id = item["task_id"]
            if not isinstance(task_id, UUID):
                task_id = UUID(str(task_id))
            task = self._uow.tasks.get(task_id)
            if task.status != TaskStatus.APPROVED or task.subject != subject:
                raise ValueError("Slice item must reference an approved task of the subject.")
            is_correct = answer_is_correct(item.get("answer_text"), task.expected_answer)
            if is_correct:
                correct += 1
            else:
                self._uow.evidence.add_error_event(
                    {
                        "id": uuid4(),
                        "student_id": student_id,
                        "subject": subject,
                        "topic_id": task.topic_id,
                        "mission_id": None,
                        "attempt_id": None,
                        "evidence_id": None,
                        "category": task.error_category or ErrorCategory.OTHER,
                        "detail": f"Срез: неверный ответ. Задача {task.task_number or task.id}.",
                        "created_at": now,
                    }
                )
            results.append({"task_id": task.id, "correct": is_correct})
        total = len(items)
        fraction = correct / total if total else 0.0
        self._uow.dashboard.add_diagnostic(
            {
                "id": uuid4(),
                "student_id": student_id,
                "subject": subject,
                "occurred_on": self._today(),
                "topic_title": f"Срез — {SLICE_SUBJECT_LABEL.get(subject, subject.value)}",
                "tasks_total": total,
                "tasks_correct": correct,
                "percent_correct": fraction,
                "note": None,
            }
        )
        self._uow.commit()
        return {
            "tasks_total": total,
            "tasks_correct": correct,
            "percent": round(fraction * 100),
            "passed": fraction >= 0.8,
            "items": results,
        }

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

        if self._is_drill(mission) and task is not None and (task.expected_answer or "").strip():
            # Часть-1 дрилл: мгновенная точная проверка, без LLM.
            draft = self._grade_exact_answer(attempt.answer_text, task)
        else:
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
        score_percent, status = self._resolve_score(
            threshold_percent=mission.threshold_percent,
            reviewer_score_percent=draft.score_percent,
            tasks_total=values.get("tasks_total"),
            tasks_correct=values.get("tasks_correct"),
            explicit_status=draft.status,
        )
        evidence = self._uow.evidence.add(
            {
                "id": uuid4(),
                "attempt_id": attempt.id,
                "mission_id": mission.id,
                "student_id": mission.student_id,
                "topic_id": mission.topic_id,
                "status": status,
                "score_percent": score_percent,
                "tasks_total": values.get("tasks_total"),
                "tasks_correct": values.get("tasks_correct"),
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
            "score_percent": score_percent,
            "tasks_total": evidence.tasks_total,
            "tasks_correct": evidence.tasks_correct,
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
        tasks_total = values.get("tasks_total")
        tasks_correct = values.get("tasks_correct")
        default_score = 100.0 if status == EvidenceStatus.PASSED else 0.0
        score_percent, status = self._resolve_score(
            threshold_percent=mission.threshold_percent,
            explicit_score_percent=values.get("score_percent", default_score),
            tasks_total=tasks_total,
            tasks_correct=tasks_correct,
            explicit_status=status,
        )
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
                "tasks_total": tasks_total,
                "tasks_correct": tasks_correct,
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
            "tasks_total": evidence.tasks_total,
            "tasks_correct": evidence.tasks_correct,
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
