import random
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from app.application.ports import (
    AiAssessment,
    AttemptForReview,
    EvidenceDraft,
    EvidenceReviewer,
    ShortAnswerJudge,
    UnitOfWork,
)
from app.config import get_settings
from app.domain.enums import (
    AiPolicy,
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    MissionStatus,
    ReviewStatus,
    Subject,
    TaskStatus,
    TopicState,
)
from app.domain.figures import parse_interval_answer, parse_interval_answer_from_text
from app.domain.policies import (
    answer_is_correct,
    describe_pick,
    evidence_status,
    extract_declared_answer,
    normalize_answer,
    numeric_mismatch,
    review_due_dates,
    review_result_to_status,
    select_daily_queue,
)
from app.domain.prerequisites import PREREQUISITES, prerequisites_met
from app.domain.probability_visual import parse_probability_visual_spec
from app.domain.program import PHASES, PHASES_BY_KEY, current_phase_key


@dataclass
class VisualAid:
    """A post-attempt visual aid delivered to the learner."""
    kind: str           # e.g. "number_line"
    png: bytes          # raw PNG bytes
    caption: str        # displayed caption (e.g. "Решение vs Ваш ответ")


SLICE_SUBJECT_LABEL = {
    Subject.MATH_PROFILE: "Профматематика",
    Subject.INFORMATICS: "Информатика",
}


@dataclass(frozen=True)
class AnswerJudgment:
    """Итог оценки короткого ответа после применения политики (exact-авторитет + ИИ)."""

    correct: bool
    feedback: str
    grading_method: str  # exact | explicit_exact | exact_fallback | llm_equivalent | llm_rejected
    model_id: str | None = None
    prompt_version: str | None = None
    rubric_version: str | None = None


class ExactOnlyJudge:
    """Судья без ИИ: всегда None → сервис применяет только точное сравнение (детерминизм)."""

    async def assess(
        self, statement: str, correct_answer: str, student_answer: str | None
    ) -> AiAssessment | None:
        return None


class LearningService:
    def __init__(
        self,
        uow: UnitOfWork,
        reviewer: EvidenceReviewer,
        local_timezone: str = "Europe/Moscow",
        judge: ShortAnswerJudge | None = None,
    ) -> None:
        self._uow = uow
        self._reviewer = reviewer
        self._local_timezone = local_timezone
        self._judge: ShortAnswerJudge = judge or ExactOnlyJudge()

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

    @staticmethod
    def _review_card_id(mission: object) -> UUID | None:
        """ID карточки повтора из source_ref ``daily:review:<uuid>`` (иначе None)."""
        ref = getattr(mission, "source_ref", None) or ""
        prefix = "daily:review:"
        if ref.startswith(prefix):
            try:
                return UUID(ref[len(prefix) :])
            except ValueError:
                return None
        return None

    def _apply_review_drill_progression(
        self,
        mission: object,
        evidence: object,
        category: ErrorCategory,
        feedback: str,
        review_id: UUID,
    ) -> None:
        """Дрилл-повтор (origin ``daily:review``): закрываем ИСХОДНУЮ карточку, без новых
        +7/+30. PASS → карточка DONE; FAIL → BACK_TO_WORK (сборщик передриллит свежей
        задачей). Карточку трогаем только пока её статус DUE/BACK_TO_WORK — повторные/
        устаревшие сабмиты последствий не плодят (шов №6)."""
        self._uow.missions.mark_done(mission.id)
        if evidence.status == EvidenceStatus.FAILED and category != ErrorCategory.NONE:
            self._add_error_event(mission, evidence.attempt_id, evidence, feedback, category)
        card = self._uow.reviews.get(review_id)
        if card is None or card.status not in (ReviewStatus.DUE, ReviewStatus.BACK_TO_WORK):
            return
        new_status = (
            ReviewStatus.DONE
            if evidence.status == EvidenceStatus.PASSED
            else ReviewStatus.BACK_TO_WORK
        )
        self._uow.reviews.mark_result(review_id, new_status)

    def _apply_progression(
        self, mission: object, evidence: object, category: ErrorCategory, feedback: str
    ) -> None:
        review_id = self._review_card_id(mission)
        if review_id is not None:
            self._apply_review_drill_progression(mission, evidence, category, feedback, review_id)
            return
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
        data["retention"] = self._retention_summary(student_id)
        return data

    def _retention_summary(
        self, student_id: UUID, today: date | None = None
    ) -> dict[str, object]:
        settings = get_settings()
        local_tz = ZoneInfo(settings.local_timezone)
        local_today = today or datetime.now(local_tz).date()
        week_start = local_today - timedelta(days=local_today.weekday())
        target_active_days = 3

        def _aware(value: object) -> datetime | None:
            if not isinstance(value, datetime):
                return None
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value

        active_dates: set[date] = set()
        for row in self.list_attempt_history(student_id, limit=500):
            created_at = _aware(row.get("created_at"))
            if created_at is None:
                continue
            local_day = created_at.astimezone(local_tz).date()
            if week_start <= local_day <= local_today:
                active_dates.add(local_day)

        for row in self.list_diagnostics(student_id):
            occurred_on = row.get("occurred_on")
            if isinstance(occurred_on, date) and week_start <= occurred_on <= local_today:
                active_dates.add(occurred_on)

        for row in self.list_score_events(student_id, limit=200):
            occurred_on = row.get("occurred_on")
            if isinstance(occurred_on, date) and week_start <= occurred_on <= local_today:
                active_dates.add(occurred_on)

        active_days = len(active_dates)
        at_risk = local_today.weekday() >= 2 and active_days < target_active_days
        message = (
            f"Retention risk: {active_days}/{target_active_days} active days by Wednesday."
            if at_risk
            else f"Retention rhythm: {active_days}/{target_active_days} active days this week."
        )
        return {
            "week_start": week_start,
            "today": local_today,
            "active_days": active_days,
            "target_active_days": target_active_days,
            "at_risk": at_risk,
            "message": message,
            "daily_task_target": settings.daily_drill_size,
        }

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

    def list_undelivered_notes(self, student_id: UUID) -> list[dict[str, object]]:
        """Наставнические заметки, ещё не доставленные ученику в Telegram (старые вперёд)."""
        return self._uow.mentor_notes.list_undelivered(student_id)

    def mark_notes_delivered(self, note_ids: list[UUID]) -> None:
        self._uow.mentor_notes.mark_delivered(note_ids)
        self._uow.commit()

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

    @staticmethod
    def _phase_started(phase_key: object, today: date) -> bool:
        phase = PHASES_BY_KEY.get(str(phase_key))
        return phase is not None and phase.start <= today

    @staticmethod
    def _requires_manual_review_path(topic: dict[str, object]) -> bool:
        title = str(topic.get("topic_title") or "").lower()
        markers = (
            "задача 13",
            "№14",
            "№16",
            "№17",
            "№18",
            "экономическая задача",
            "стереометрия",
            "планиметрия",
            "параметр",
        )
        return any(marker in title for marker in markers)

    def _mission_payload(self, mission: object) -> dict[str, object]:
        task = getattr(mission, "task", None)
        topic = getattr(mission, "topic", None)
        statement = task.statement if task is not None else None
        topic_id = getattr(mission, "topic_id", None)
        task_number = task.task_number if task is not None else getattr(topic, "task_number", None)
        return {
            "id": mission.id,
            "subject": mission.subject,
            "topic_id": topic_id,
            "title": mission.title,
            "instructions": mission.instructions,
            "statement": statement,
            "ai_policy": mission.ai_policy,
            "task_number": task_number,
            "threshold_percent": mission.threshold_percent,
            "due_date": mission.due_date,
            "timebox_minutes": mission.timebox_minutes,
            "source_ref": mission.source_ref,
            "visual_ready": bool(
                topic_id is not None and self._uow.theory_cards.has_concept_for_topic(topic_id)
            ),
        }

    def list_topic_theory(self, topic_id: UUID) -> list[dict[str, object]]:
        return self._uow.theory_cards.list_approved_for_topic(topic_id)

    def list_daily_drill(self, student_id: UUID) -> list[dict[str, object]]:
        """Очередь Telegram-дрилла: только открытые daily:-миссии со связанной задачей.
        Отдельная поверхность — чтобы в чат не попали части 2 / операторские миссии."""
        return [
            self._mission_payload(mission)
            for mission in self._uow.missions.list_today(student_id)
            if self._is_drill(mission) and getattr(mission, "task", None) is not None
        ]

    def build_daily_queue(self, student_id: UUID, limit: int = 5) -> dict[str, object]:
        """Авто-сборщик дня: до ``limit`` дрилл-миссий, повторы вперёд, новые темы в остаток.

        Уже открытые daily-миссии (carry-over) считаются в лимит первыми. Под каждый выбор
        берётся СВЕЖАЯ (не назначавшаяся) задача темы; если её нет — тема идёт в ``shortage``,
        а не пропускается тихо. Идемпотентно за день: уже открытый daily:-source_ref не дублим."""
        today = self._today()
        open_daily = [
            m for m in self._uow.missions.list_today(student_id) if self._is_drill(m)
        ]
        open_refs = {m.source_ref for m in open_daily}

        def _review_refs(rows: list[dict[str, object]], kind: str) -> list[dict[str, object]]:
            refs = []
            for row in rows:
                source_ref = f"daily:review:{row['id']}"
                if source_ref not in open_refs:
                    refs.append(
                        {
                            "topic_id": row["topic_id"],
                            "title": row["topic_title"],
                            "source_ref": source_ref,
                            "reason": {"kind": kind},
                        }
                    )
            return refs

        due_refs = _review_refs(
            self._uow.reviews.list_reviews(
                student_id, status=ReviewStatus.DUE, due_on_or_before=today
            ),
            "due_review",
        )
        back_to_work_refs = _review_refs(
            self._uow.reviews.list_reviews(student_id, status=ReviewStatus.BACK_TO_WORK),
            "back_to_work",
        )
        phase = current_phase_key(today)
        review_topic_ids = {ref["topic_id"] for ref in (*due_refs, *back_to_work_refs)}
        program_rows = sorted(
            self._uow.topics.list_program(student_id),
            key=lambda t: (t["program_order"] or 0, t["topic_title"]),
        )
        # Режим /ready: если ученик отметил хоть одну тему «теорию изучила», новые дриллы
        # идут ТОЛЬКО по отмеченным темам любой уже начавшейся фазы; неотмеченные темы
        # текущей фазы придерживаются. Без отметок — прежнее поведение (темы текущей фазы).
        ready_mode = any(t.get("theory_ready") for t in program_rows)
        # Пререквизит-ворота: тему не даём, пока её базовые темы не закрыты хоть раз
        # (есть PASSED-evidence → solved_count > 0). program_order задаёт порядок,
        # эти ворота — жёсткая зависимость поверх него.
        passed_titles = {t["topic_title"] for t in program_rows if t["solved_count"] > 0}
        new_refs = []
        for topic in program_rows:
            source_ref = f"daily:new:{topic['topic_id']}"
            if ready_mode:
                phase_ok = bool(topic.get("theory_ready")) and self._phase_started(
                    topic["phase"], today
                )
            else:
                phase_ok = topic["phase"] == phase
            if (
                phase_ok
                and topic["state"] == TopicState.OPEN
                and topic["tasks_in_bank"] > 0
                and not self._requires_manual_review_path(topic)
                and prerequisites_met(topic["topic_title"], passed_titles, PREREQUISITES)
                and source_ref not in open_refs
                and topic["topic_id"] not in review_topic_ids
            ):
                new_refs.append(
                    {
                        "topic_id": topic["topic_id"],
                        "title": topic["topic_title"],
                        "source_ref": source_ref,
                        "reason": {
                            "kind": "new_topic",
                            "prerequisites": list(PREREQUISITES.get(topic["topic_title"], ())),
                            "phase": topic["phase"],
                            "error_count": topic["error_count"],
                        },
                    }
                )

        picks = select_daily_queue(len(open_daily), due_refs, back_to_work_refs, new_refs, limit)
        filled: list[dict[str, object]] = []
        shortage: list[dict[str, object]] = []
        for ref in picks:
            pool = self._uow.tasks.list_approved_for_topic(
                ref["topic_id"], exclude_assigned_to=student_id
            )
            if not pool:
                shortage.append(
                    {"topic_id": ref["topic_id"], "title": ref["title"], "reason": "no_fresh_task"}
                )
                continue
            task = pool[0]
            mission = self.create_mission(
                {
                    "student_id": student_id,
                    "subject": task.subject,
                    "title": f"Дрилл: {ref['title']}",
                    "instructions": "Реши, кратко распиши ход решения и в конце укажи ответ.",
                    "status": MissionStatus.ACTIVE,
                    "ai_policy": AiPolicy.ATTEMPT_FIRST,
                    "threshold_percent": 80.0,
                    "topic_id": ref["topic_id"],
                    "task_id": task.id,
                    "due_date": today,
                    "source_ref": ref["source_ref"],
                }
            )
            mission["reason"] = ref["reason"]
            mission["why"] = describe_pick(ref["reason"])
            filled.append(mission)
        return {"filled": filled, "shortage": shortage}

    def list_theory_ready_candidates(self, student_id: UUID) -> list[dict[str, object]]:
        """Темы для отметки /ready: открытые, с задачами в банке, из уже начавшихся фаз.
        Отмеченные тоже возвращаются (чтобы отметку можно было снять)."""
        today = self._today()
        rows: list[dict[str, object]] = []
        for topic in sorted(
            self._uow.topics.list_program(student_id),
            key=lambda t: (t["program_order"] or 0, t["topic_title"]),
        ):
            if (
                topic["state"] == TopicState.OPEN
                and topic["tasks_in_bank"] > 0
                and not self._requires_manual_review_path(topic)
                and self._phase_started(topic["phase"], today)
            ):
                rows.append(
                    {
                        "topic_id": topic["topic_id"],
                        "title": topic["topic_title"],
                        "subject": topic["subject"],
                        "theory_ready": bool(topic.get("theory_ready")),
                    }
                )
        return rows

    def set_topic_theory_ready(self, topic_id: UUID, ready: bool) -> dict[str, object]:
        """Отметка «теорию изучила» — сигнал приоритета для сборщика дня, не evidence."""
        topic = self._uow.topics.set_theory_ready(topic_id, ready)
        if topic is None:
            raise ValueError(f"topic {topic_id} not found")
        self._uow.commit()
        return {
            "topic_id": topic.id,
            "title": topic.title,
            "theory_ready": topic.theory_ready_at is not None,
        }

    def list_self_pick_candidates(self, student_id: UUID) -> list[dict[str, object]]:
        """Темы части 1 трека, которые ученица может сама добавить в «Сегодня».

        Тот же набор условий, что у `/ready` (`list_theory_ready_candidates`), плюс
        пререквизит-ворота (как у авто-пика новой темы) и минус темы, уже открытые
        сегодня daily-миссией (auto- или self-pick — неважно каким source_ref)."""
        today = self._today()
        open_topic_ids = {
            m.topic_id
            for m in self._uow.missions.list_today(student_id)
            if self._is_drill(m) and m.topic_id is not None
        }
        program_rows = sorted(
            self._uow.topics.list_program(student_id),
            key=lambda t: (t["program_order"] or 0, t["topic_title"]),
        )
        passed_titles = {t["topic_title"] for t in program_rows if t["solved_count"] > 0}
        rows: list[dict[str, object]] = []
        for topic in program_rows:
            if (
                topic["state"] == TopicState.OPEN
                and topic["tasks_in_bank"] > 0
                and not self._requires_manual_review_path(topic)
                and self._phase_started(topic["phase"], today)
                and prerequisites_met(topic["topic_title"], passed_titles, PREREQUISITES)
                and topic["topic_id"] not in open_topic_ids
            ):
                rows.append(
                    {
                        "topic_id": topic["topic_id"],
                        "title": topic["topic_title"],
                        "subject": topic["subject"],
                    }
                )
        return rows

    def _topic_drill_from_pool(
        self, student_id: UUID, topic_id: UUID, title: str
    ) -> dict[str, object]:
        """Общее ядро self-pick и «ещё по теме»: взять свежую (не назначавшуюся) задачу и
        создать ACTIVE daily-миссию. Свежих нет → ``{"shortage": {...}}``."""
        pool = self._uow.tasks.list_approved_for_topic(topic_id, exclude_assigned_to=student_id)
        if not pool:
            return {"shortage": {"topic_id": topic_id, "title": title}}
        task = pool[0]
        mission = self.create_mission(
            {
                "student_id": student_id,
                "subject": task.subject,
                "title": f"Дрилл: {title}",
                "instructions": "Реши, кратко распиши ход решения и в конце укажи ответ.",
                "status": MissionStatus.ACTIVE,
                "ai_policy": AiPolicy.ATTEMPT_FIRST,
                "threshold_percent": 80.0,
                "topic_id": topic_id,
                "task_id": task.id,
                "due_date": self._today(),
                "source_ref": f"daily:self:{topic_id}",
            }
        )
        mission["why"] = describe_pick({"kind": "self_pick"})
        return {"mission": mission}

    def self_add_topic_mission(self, student_id: UUID, topic_id: UUID) -> dict[str, object]:
        """Ученица сама добавляет тему в «Сегодня» — вне бюджета `build_daily_queue`
        (тот пересчитает лимит на завтра сам, увидев эту миссию как carry-over).

        Возвращает ``{"mission": {...}}`` или ``{"shortage": {...}}``, если по теме
        сейчас нет свежей (не назначавшейся) задачи."""
        candidates = self.list_self_pick_candidates(student_id)
        match = next((c for c in candidates if c["topic_id"] == topic_id), None)
        if match is None:
            raise ValueError(f"topic {topic_id} is not a valid self-pick candidate")
        return self._topic_drill_from_pool(student_id, topic_id, str(match["title"]))

    def serve_more_from_topic(self, student_id: UUID, topic_id: UUID) -> dict[str, object]:
        """«Ещё по этой теме» после дрилла: следующая свежая задача той же темы, вне гейта
        open-today (тема сейчас активно дриллится, отсекать её как «уже открытую» нельзя) и
        без требования state==OPEN. Каждый вызов логируется как сигнал спроса (served/
        shortage) — питает генератор. Возвращает ``{"mission": ...}`` | ``{"shortage": ...}``."""
        row = next(
            (t for t in self._uow.topics.list_program(student_id) if t["topic_id"] == topic_id),
            None,
        )
        if (
            row is None
            or self._requires_manual_review_path(row)
            or not self._phase_started(row["phase"], self._today())
        ):
            raise ValueError(f"topic {topic_id} is not a valid drill topic")
        result = self._topic_drill_from_pool(student_id, topic_id, str(row["topic_title"]))
        self._uow.topic_requests.add(
            student_id, topic_id, "shortage" if "shortage" in result else "served"
        )
        self._uow.commit()
        return result

    def demand_by_topic(self, days: int = 30) -> list[dict[str, object]]:
        """Сигнал спроса по темам (served/shortage) за N дней — для генератора и оператора."""
        return self._uow.topic_requests.demand_by_topic(days)

    def operator_close_daily_missions(
        self, student_id: UUID, reason: str | None = None
    ) -> dict[str, object]:
        """Operator recovery for trusted completed daily drills.

        This records explicit recovery evidence instead of mutating mission status
        directly, so the normal progression path still closes missions and handles
        review cards.
        """
        reason_text = (reason or "").strip() or (
            "Guardian accepted these daily missions as completed."
        )
        now = datetime.now(UTC)
        closed: list[dict[str, object]] = []
        for mission in list(self._uow.missions.list_today(student_id)):
            if not self._is_drill(mission):
                continue
            attempt = self._uow.attempts.add(
                {
                    "id": uuid4(),
                    "mission_id": mission.id,
                    "student_id": mission.student_id,
                    "kind": AttemptKind.TEXT,
                    "mode": AttemptMode.UNKNOWN,
                    "answer_text": reason_text,
                    "code_text": None,
                    "time_spent_minutes": None,
                    "submitted_at": now,
                }
            )
            evidence = self._uow.evidence.add(
                {
                    "id": uuid4(),
                    "attempt_id": attempt.id,
                    "mission_id": mission.id,
                    "student_id": mission.student_id,
                    "topic_id": mission.topic_id,
                    "status": EvidenceStatus.PASSED,
                    "score_percent": 100.0,
                    "tasks_total": None,
                    "tasks_correct": None,
                    "error_category": ErrorCategory.NONE,
                    "feedback": f"Operator recovery: {reason_text}",
                    "next_action": "Mission accepted; continue with the next queue.",
                    "model_id": "operator-recovery",
                    "prompt_version": "daily-mission-recovery-v1",
                    "rubric_version": "ege-mentor-v1",
                    "created_at": now,
                }
            )
            self._apply_progression(
                mission,
                evidence,
                ErrorCategory.NONE,
                f"Operator recovery: {reason_text}",
            )
            closed.append(
                {
                    "mission_id": mission.id,
                    "attempt_id": attempt.id,
                    "evidence_id": evidence.id,
                    "topic_id": mission.topic_id,
                    "title": mission.title,
                    "source_ref": mission.source_ref,
                    "status": EvidenceStatus.PASSED,
                }
            )
        self._uow.commit()
        return {"closed_count": len(closed), "closed": closed}

    def operator_skip_daily_missions(
        self, mission_ids: list[UUID], reason: str | None = None
    ) -> dict[str, object]:
        """Retire mistakenly created daily missions without marking learning evidence."""
        reason_text = (reason or "").strip() or "Operator retired this daily mission."
        skipped: list[dict[str, object]] = []
        for mission_id in mission_ids:
            mission = self._uow.missions.get_for_attempt(mission_id)
            if not self._is_drill(mission):
                raise ValueError("Only daily missions can be skipped by this operator tool.")
            instructions = (mission.instructions or "").rstrip()
            if instructions:
                instructions = f"{instructions}\n\nOperator note: {reason_text}"
            else:
                instructions = f"Operator note: {reason_text}"
            self._uow.missions.update(
                mission.id,
                {"status": MissionStatus.SKIPPED, "instructions": instructions},
            )
            skipped.append(
                {
                    "mission_id": mission.id,
                    "title": mission.title,
                    "topic_id": mission.topic_id,
                    "source_ref": mission.source_ref,
                    "status": MissionStatus.SKIPPED,
                }
            )
        self._uow.commit()
        return {"skipped_count": len(skipped), "skipped": skipped}

    async def _grade_answer(
        self, statement: str, correct_answer: str, student_answer: str | None
    ) -> AnswerJudgment:
        """Политика оценки короткого ответа (application-слой). Exact-match авторитетен (эталон
        верифицирован); ИИ может только вытащить эквивалентную форму на промахе exact; сбой/None ИИ
        → детерминированный exact (fail-open). Провенанс ИИ-решения сохраняется."""
        exact = answer_is_correct(student_answer, correct_answer)
        # Один явный "Ответ ..." в многострочном решении — детерминированная альтернатива
        # к целостроковому exact (не заменяет его; не сканирует произвольные числа в решении).
        declared = extract_declared_answer(student_answer)
        declared_exact = bool(declared) and not exact and answer_is_correct(declared, correct_answer)
        declared_mismatch = (
            bool(declared)
            and not exact
            and not declared_exact
            and numeric_mismatch(declared, correct_answer)
        )
        assessment = await self._judge.assess(statement, correct_answer, student_answer)
        if assessment is None:
            correct = exact or declared_exact
            method = "explicit_exact" if declared_exact else "exact"
            return AnswerJudgment(
                correct=correct,
                feedback="Верно." if correct else "Неверно.",
                grading_method=method,
            )
        provenance = (assessment.model_id, assessment.prompt_version, assessment.rubric_version)
        # Заземление: exact на сыром ответе ИЛИ на финальном ответе, извлечённом ИИ из решения
        # («покажи ход» — сырой текст обычно не совпадёт целиком, поэтому сверяем извлечённый).
        extracted = assessment.extracted_answer
        extracted_ok = bool(extracted) and answer_is_correct(extracted, correct_answer)
        # Приоритет: raw exact → явный "Ответ" заземление → явный "Ответ" числовое несовпадение
        # (стоп, ИИ не переопределяет) → raw числовое несовпадение (стоп) → извлечённое ИИ
        # заземление → извлечённое числовое несовпадение (стоп) → мнение ИИ. Доказуемое число
        # авторитетнее ИИ; сырое число важнее извлечения (иначе ИИ «извлекает» эталон из
        # неверного 0,667 → ложно).
        if exact:
            correct = True
        elif declared_exact:
            correct = True
        elif declared_mismatch:
            correct = False
        elif numeric_mismatch(student_answer, correct_answer):
            correct = False
        elif extracted_ok:
            correct = True
        elif numeric_mismatch(extracted, correct_answer):  # extracted=None → mismatch False
            correct = False
        else:
            correct = assessment.equivalent
        if correct and not assessment.equivalent:
            # вердикт по заземлению авторитетен; противоречащий ИИ-текст заменяем безопасным.
            feedback = "Верно."
        else:
            feedback = self._mask_answer(assessment.feedback, correct_answer, correct)
        if not feedback:
            feedback = "Верно." if correct else "Неверно."
        # "exact" только для raw exact; явный "Ответ" заземление → explicit_exact; извлечённо-
        # заземлённый ИИ → llm_equivalent (так record_slice доверяет верному «покажи ход»-ответу,
        # у которого сырой текст ≠ ключу).
        if exact:
            method = "exact"
        elif declared_exact:
            method = "explicit_exact"
        else:
            method = "llm_equivalent" if correct else "llm_rejected"
        return AnswerJudgment(correct, feedback, method, *provenance)

    @staticmethod
    def _mask_answer(feedback: str, correct_answer: str, correct: bool) -> str:
        """Сохраняем разбор ИИ, маскируя сам эталон (`…`). Голая строка — лишь когда маскировка
        не очистила текст (формат не совпал), чтобы никогда не отдать эталон дословно."""
        key = normalize_answer(correct_answer)
        if len(key) < 2 or key not in normalize_answer(feedback):
            return feedback
        raw = correct_answer.strip()
        masked = feedback
        for form in {raw, raw.replace(",", "."), raw.replace(".", ",")}:
            if form:
                masked = masked.replace(form, "…")
        if key in normalize_answer(masked):
            return "Верно." if correct else "Близко — проверь ещё раз."
        return masked

    @staticmethod
    def _drill_draft(judgment: AnswerJudgment, task: object) -> EvidenceDraft:
        """EvidenceDraft дрилла из вердикта политики (PASSED/FAILED + провенанс)."""
        passed = judgment.correct
        category = ErrorCategory.NONE if passed else (task.error_category or ErrorCategory.OTHER)
        return EvidenceDraft(
            score_percent=100.0 if passed else 0.0,
            error_category=category,
            feedback=judgment.feedback,
            next_action="Тема засчитана." if passed else "Повтори задачу и реши заново.",
            model_id=judgment.model_id or "exact-answer",
            prompt_version=judgment.prompt_version or "none",
            rubric_version=judgment.rubric_version or "ege-mentor-v1",
            status=EvidenceStatus.PASSED if passed else EvidenceStatus.FAILED,
        )

    def list_errors(
        self,
        student_id: UUID,
        subject: object | None = None,
        category: ErrorCategory | None = None,
    ) -> list[dict[str, object]]:
        return self._uow.errors.list_errors(student_id, subject, category)

    def confirm_error_category(
        self, error_id: UUID, category: ErrorCategory
    ) -> dict[str, object]:
        """Manual mentor confirmation of one actionable category for an existing
        answer-only error. The raw category is never changed here."""
        if category in (ErrorCategory.NONE, ErrorCategory.OTHER):
            raise ValueError("Cannot confirm category as NONE or OTHER")
        student_id = self._uow.errors.confirm_category(error_id, category, datetime.now(UTC))
        self._uow.commit()
        for row in self._uow.errors.list_errors(student_id):
            if row["id"] == error_id:
                return row
        raise LookupError(f"Error event {error_id} not found after confirmation")

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
                        "under_review": sum(
                            1 for t in topics if t["state"] == TopicState.UNDER_REVIEW
                        ),
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

    def days_since_last_diagnostic(self, student_id: UUID) -> int | None:
        """Дней с последнего среза (любая тема); None — среза ещё не было."""
        occurred = [
            row["occurred_on"]
            for row in self.list_diagnostics(student_id)
            if isinstance(row.get("occurred_on"), date)
        ]
        if not occurred:
            return None
        return (self._today() - max(occurred)).days

    def daily_activity_summary(self, student_id: UUID) -> dict[str, object]:
        """Компактный статус дня для родительского пуша и повторных напоминаний ученику:
        начинала ли сегодня, сколько дневных миссий закрыто, давно ли был срез."""
        today = self._today()
        local_tz = ZoneInfo(self._local_timezone)

        def _local_day(value: object) -> date | None:
            if not isinstance(value, datetime):
                return None
            aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
            return aware.astimezone(local_tz).date()

        attempted_today = any(
            _local_day(row.get("created_at")) == today
            for row in self.list_attempt_history(student_id, limit=200)
        )
        drill = self.list_daily_drill(student_id)
        return {
            "attempted_today": attempted_today,
            "drill_open": len(drill),
            "days_since_slice": self.days_since_last_diagnostic(student_id),
        }

    def weekly_digest(self, student_id: UUID, days: int = 7) -> dict[str, object]:
        """Read-only pilot analytics from existing attempts, slices, errors, and reviews."""
        days = max(1, min(int(days), 90))
        now = datetime.now(UTC)
        since = now - timedelta(days=days)
        since_date = since.date()

        def _aware(value: object) -> datetime | None:
            if not isinstance(value, datetime):
                return None
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value

        def _enum_value(value: object) -> str:
            return getattr(value, "value", str(value))

        attempts = [
            row
            for row in self.list_attempt_history(student_id, limit=500)
            if (created_at := _aware(row.get("created_at"))) is not None and created_at >= since
        ]
        passed_attempts = sum(1 for row in attempts if row.get("status") == EvidenceStatus.PASSED)
        topics_touched = sorted(
            {
                str(row.get("topic_title") or row.get("topic_id"))
                for row in attempts
                if row.get("topic_title") or row.get("topic_id")
            }
        )

        diagnostics = [
            row
            for row in self.list_diagnostics(student_id)
            if row.get("occurred_on") is not None and row["occurred_on"] >= since_date
        ]
        captured_diagnostics = sum(1 for row in diagnostics if row.get("captured"))

        recent_score_events = [
            row
            for row in self.list_score_events(student_id, limit=50)
            if row.get("occurred_on") is not None and row["occurred_on"] >= since_date
        ]

        errors = [
            row
            for row in self.list_errors(student_id)
            if (created_at := _aware(row.get("created_at"))) is not None and created_at >= since
        ]
        error_counts: dict[str, int] = {}
        for row in errors:
            category = _enum_value(row.get("category"))
            error_counts[category] = error_counts.get(category, 0) + 1

        review_counts: dict[str, int] = {}
        for row in self.list_reviews(student_id):
            status = _enum_value(row.get("status"))
            review_counts[status] = review_counts.get(status, 0) + 1

        return {
            "period": {"days": days, "since": since_date, "until": now.date()},
            "engagement": {
                "attempts": len(attempts),
                "active_days": len(
                    {
                        created_at.date()
                        for row in attempts
                        if (created_at := _aware(row.get("created_at"))) is not None
                    }
                ),
            },
            "learning": {
                "passed_attempts": passed_attempts,
                "pass_rate": round(passed_attempts / len(attempts), 2) if attempts else None,
                "topics_touched": topics_touched,
            },
            "diagnostics": {
                "count": len(diagnostics),
                "captured": captured_diagnostics,
                "score_only": len(diagnostics) - captured_diagnostics,
                "recent": diagnostics[:5],
            },
            "scores": {
                "recent": recent_score_events[:5],
                "latest_by_subject": {
                    _enum_value(track["subject"]): {
                        "current_score": track["current_score"],
                        "target_score": track["target_score"],
                        "score_gap": track["score_gap"],
                    }
                    for track in self.get_dashboard(student_id)["tracks"]
                },
            },
            "errors": {
                "count": len(errors),
                "by_category": [
                    {"category": category, "count": count}
                    for category, count in sorted(error_counts.items())
                ],
                "recent": errors[:5],
            },
            "reviews": review_counts,
            "manual_reviews_pending": len(self.list_manual_reviews(student_id)),
        }

    def mentor_brief(self, student_id: UUID, days: int = 14) -> dict[str, object]:
        """Compact first-read context for a senior mentor agent.

        Raw attempts, full program state, and error details remain available through
        drill-down MCP tools. This brief intentionally avoids full answer/code text.
        """
        days = max(1, min(int(days), 30))
        dashboard = self.get_dashboard(student_id)
        digest = self.weekly_digest(student_id, days)
        phases = self.list_program_progress(student_id)

        def _enum_value(value: object) -> str:
            return getattr(value, "value", str(value))

        def _short(value: object, limit: int = 180) -> str | None:
            if value is None:
                return None
            text = str(value).strip()
            return text if len(text) <= limit else f"{text[: limit - 1]}…"

        current_phase = next((phase for phase in phases if phase["is_current"]), None)
        if current_phase is None and phases:
            current_phase = phases[0]

        topics_to_watch: list[dict[str, object]] = []
        if current_phase is not None:
            topic_rows = [
                topic
                for topic in current_phase["topics"]
                if _enum_value(topic.get("state")) != TopicState.OPEN.value
                or topic.get("error_count")
                or topic.get("reviews_due_today")
                or topic.get("theory_ready")
                or topic.get("visual_ready")
            ]

            def _topic_priority(topic: dict[str, object]) -> tuple[int, int, str]:
                state = _enum_value(topic.get("state"))
                state_priority = {
                    TopicState.BACK_TO_WORK.value: 0,
                    TopicState.UNDER_REVIEW.value: 1,
                    TopicState.IN_WORK.value: 2,
                    TopicState.CONFIRMED.value: 3,
                    TopicState.OPEN.value: 4,
                }.get(state, 5)
                errors = int(topic.get("error_count") or 0)
                return (state_priority, -errors, str(topic.get("topic_title") or ""))

            topics_to_watch = [
                {
                    "topic_id": topic["topic_id"],
                    "title": topic["topic_title"],
                    "subject": topic["subject"],
                    "state": _enum_value(topic["state"]),
                    "attempts_count": topic["attempts_count"],
                    "solved_count": topic["solved_count"],
                    "tasks_in_bank": topic["tasks_in_bank"],
                    "error_count": topic["error_count"],
                    "reviews_due_today": topic["reviews_due_today"],
                    "theory_ready": topic.get("theory_ready", False),
                    "visual_ready": topic.get("visual_ready", False),
                    "percent": topic.get("percent"),
                }
                for topic in sorted(topic_rows, key=_topic_priority)[:10]
            ]

        recent_errors = [
            {
                "topic_title": row.get("topic_title"),
                "category": _enum_value(row.get("category")),
                "detail": _short(row.get("detail")),
                "created_at": row.get("created_at"),
            }
            for row in digest["errors"]["recent"][:5]
        ]
        recent_attempts = [
            {
                "topic_title": row.get("topic_title"),
                "status": _enum_value(row.get("status")),
                "score_percent": row.get("score_percent"),
                "error_category": _enum_value(row.get("error_category")),
                "feedback": _short(row.get("feedback")),
                "next_action": _short(row.get("next_action")),
                "created_at": row.get("created_at"),
            }
            for row in self.list_attempt_history(student_id, limit=5)
        ]
        due_review_statuses = {ReviewStatus.DUE.value, ReviewStatus.BACK_TO_WORK.value}
        due_reviews = [
            {
                "review_id": row["id"],
                "topic_id": row["topic_id"],
                "topic_title": row["topic_title"],
                "status": _enum_value(row["status"]),
                "due_date": row["due_date"],
            }
            for row in self.list_reviews(student_id, due_only=True)
            if _enum_value(row.get("status")) in due_review_statuses
        ][:5]
        manual_reviews = [
            {
                "evidence_id": row["id"],
                "topic_title": row.get("topic_title"),
                "mission_title": row.get("mission_title"),
                "created_at": row.get("created_at"),
            }
            for row in self.list_manual_reviews(student_id)[:5]
        ]

        next_actions: list[str] = []
        if manual_reviews:
            next_actions.append(f"Resolve {len(manual_reviews)} pending manual review item(s).")
        if due_reviews:
            next_actions.append(f"Run or mark {len(due_reviews)} due spaced review item(s).")
        if topics_to_watch:
            titles = ", ".join(str(row["title"]) for row in topics_to_watch[:3])
            next_actions.append(f"Focus current-phase work on: {titles}.")
        if digest["errors"]["by_category"]:
            top_error = digest["errors"]["by_category"][0]
            next_actions.append(
                f"Inspect repeated error category: {top_error['category']} "
                f"({top_error['count']} recent)."
            )
        if not next_actions:
            next_actions.append("Continue current daily loop; no urgent mentor intervention.")

        return {
            "contract": {
                "purpose": "compact first-read context",
                "raw_history_retained_in": "Postgres",
                "drill_down_tools": [
                    "program_progress",
                    "attempt_history",
                    "error_journal",
                    "reviews",
                    "manual_reviews",
                    "topic_theory",
                ],
            },
            "period": digest["period"],
            "scores": digest["scores"]["latest_by_subject"],
            "retention": dashboard["retention"],
            "engagement": digest["engagement"],
            "current_phase": (
                {
                    "key": current_phase["key"],
                    "label": current_phase["label"],
                    "coverage": current_phase["coverage"],
                    "topics_to_watch": topics_to_watch,
                }
                if current_phase is not None
                else None
            ),
            "recent_learning": {
                "passed_attempts": digest["learning"]["passed_attempts"],
                "pass_rate": digest["learning"]["pass_rate"],
                "topics_touched": digest["learning"]["topics_touched"][:10],
                "diagnostics": {
                    "count": digest["diagnostics"]["count"],
                    "captured": digest["diagnostics"]["captured"],
                    "recent": digest["diagnostics"]["recent"][:3],
                },
                "attempts": recent_attempts,
            },
            "error_focus": {
                "count": digest["errors"]["count"],
                "by_category": digest["errors"]["by_category"][:5],
                "recent": recent_errors,
            },
            "queues": {
                "reviews_due": due_reviews,
                "review_status_counts": digest["reviews"],
                "manual_reviews": manual_reviews,
                "manual_reviews_pending": digest["manual_reviews_pending"],
            },
            "next_actions": next_actions,
        }

    def list_tasks(self, status: TaskStatus | None = None) -> list[dict[str, object]]:
        return self._uow.tasks.list_tasks(status)

    def task_bank_stats(self) -> list[dict[str, object]]:
        """Approved task counts by subject/source — content provenance for the operator view."""
        return self._uow.tasks.bank_stats()

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

    def drill_solution_visual(
        self, mission_id: UUID, student_answer: str | None = None
    ) -> VisualAid | None:
        """Post-attempt visual aid: a number-line PNG comparing the correct
        solution (blue) with the student's answer (orange) when both are
        parseable intervals. If only the expected answer is parseable, render
        only the correct solution. Returns None for scalar answers or when
        the task has no expected_answer.

        Called only after the attempt is recorded so the solution set is the
        разбор, not a pre-attempt leak. Renderer lives in infrastructure."""
        mission = self._uow.missions.get_for_attempt(mission_id)
        task = self._uow.tasks.get(mission.task_id) if mission.task_id is not None else None
        if task is None:
            return None

        expected_answer = getattr(task, "expected_answer", None)
        expected_intervals = parse_interval_answer(expected_answer)
        if expected_intervals is None:
            spec = parse_probability_visual_spec(
                task.statement, task.expected_answer, task.source_ref
            )
            if spec is None:
                return None
            from app.infrastructure.figures_render import render_probability_visual

            png = render_probability_visual(spec)
            return VisualAid(
                kind="probability",
                png=png,
                caption=self._probability_visual_caption(spec),
            )

        from app.infrastructure.figures_render import render_number_line

        student_intervals = parse_interval_answer_from_text(student_answer) if student_answer else None

        if student_intervals is not None:
            png = render_number_line(
                expected_intervals,
                label="Решение",
                student_intervals=student_intervals,
                student_label="Ответ",
            )
            caption = "Синее — решение, оранжевое — твой ответ"
        else:
            png = render_number_line(expected_intervals, label="Решение")
            if student_answer:
                caption = "Решение на числовой прямой; твой ответ не удалось распознать как интервал"
            else:
                caption = "Решение на числовой прямой"

        return VisualAid(kind="number_line", png=png, caption=caption)

    @staticmethod
    def _probability_visual_caption(spec: object) -> str:
        if getattr(spec, "chart_type", None) == "bar_chart":
            return "Столбцы: складываем подходящие группы"
        if getattr(spec, "highlight_cell", None) == "neither":
            return "Таблица 2x2: выделено «ни одного события»"
        if getattr(spec, "highlight_cell", None) == "only_a":
            return "Таблица 2x2: выделено «только первое событие»"
        return "Схема к задаче на вероятность"

    def drill_solution_figure(self, mission_id: UUID) -> bytes | None:
        """Backward-compatible wrapper: renders the correct solution only (no
        student answer overlay). Kept for tests and any caller that does not
        have a student_answer to pass."""
        visual = self.drill_solution_visual(mission_id)
        return visual.png if visual is not None else None

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

    def list_score_events(self, student_id: UUID, limit: int = 20) -> list[dict[str, object]]:
        return self._uow.scores.list_events(student_id, limit)

    def draw_slice(
        self, subject: Subject, size: int, topic_id: UUID | None = None
    ) -> list[dict[str, object]]:
        """Draw a knowledge slice: a random sample of approved, exact-answer tasks.
        ``topic_id`` scopes the срез to one topic. Returns statements only — the answer key
        never leaves the backend (§5)."""
        pool = self._uow.tasks.list_gradable(subject, topic_id)
        chosen = random.sample(pool, min(size, len(pool)))
        return [
            {
                "task_id": task.id,
                "topic_id": task.topic_id,
                "task_number": task.task_number,
                "statement": task.statement,
                "visual_ready": bool(
                    task.topic_id is not None
                    and self._uow.theory_cards.has_concept_for_topic(task.topic_id)
                ),
            }
            for task in chosen
        ]

    def list_slice_topics(self, student_id: UUID) -> list[dict[str, object]]:
        """Темы с задачами в банке — для выбора темы среза (TG/сайт)."""
        rows = self._uow.topics.list_program(student_id)
        topics = [
            {
                "topic_id": row["topic_id"],
                "title": row["topic_title"],
                "subject": row["subject"],
                "tasks_in_bank": row["tasks_in_bank"],
            }
            for row in rows
            if row["tasks_in_bank"] > 0
        ]
        topics.sort(key=lambda t: (t["subject"], t["title"]))
        return topics

    async def judge_task_answer(
        self, task_id: UUID, answer_text: str | None
    ) -> dict[str, object]:
        """Единая точка оценки одного ответа по задаче банка (ключ на сервере). Возвращает вердикт
        + фидбек + grading_method + провенанс, без ключа. Используют срез (сайт+TG) и дрилл."""
        if not isinstance(task_id, UUID):
            task_id = UUID(str(task_id))
        task = self._uow.tasks.get(task_id)
        if task.status != TaskStatus.APPROVED:
            raise ValueError("Slice task must be approved.")
        judgment = await self._grade_answer(task.statement, task.expected_answer, answer_text)
        return {
            "task_id": task.id,
            "answer_text": answer_text,
            "correct": judgment.correct,
            "feedback": judgment.feedback,
            "grading_method": judgment.grading_method,
            "model_id": judgment.model_id,
            "prompt_version": judgment.prompt_version,
            "rubric_version": judgment.rubric_version,
        }

    def record_slice(
        self, student_id: UUID, subject: Subject, judged: list[dict[str, object]]
    ) -> dict[str, object]:
        """Единственная точка персистентности среза. Повторно грузит задачи и пересчитывает
        детерминированный exact заново; доверяет только server-produced флагам ``llm_equivalent``
        и ``explicit_exact`` (без повторного ИИ). Пишет агрегатную диагностику + error-event на
        промах + JSON-детали для аудита. Срез — topic_check: текущий балл/lifecycle не двигает."""
        now = datetime.now(UTC)
        results: list[dict[str, object]] = []
        details: list[dict[str, object]] = []
        topic_ids: set[UUID] = set()
        correct = 0
        for item in judged:
            task_id = item["task_id"]
            if not isinstance(task_id, UUID):
                task_id = UUID(str(task_id))
            task = self._uow.tasks.get(task_id)
            if task.status != TaskStatus.APPROVED or task.subject != subject:
                raise ValueError("Slice item must reference an approved task of the subject.")
            if task.topic_id is not None:
                topic_ids.add(task.topic_id)
            answer_text = item.get("answer_text")
            exact = answer_is_correct(answer_text, task.expected_answer)
            is_correct = exact or item.get("grading_method") in ("llm_equivalent", "explicit_exact")
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
            details.append(
                {
                    "task_id": str(task.id),
                    "answer": answer_text,
                    "correct": is_correct,
                    "grading_method": item.get("grading_method"),
                    "feedback": item.get("feedback"),
                    "model_id": item.get("model_id"),
                    "prompt_version": item.get("prompt_version"),
                    "rubric_version": item.get("rubric_version"),
                }
            )
        total = len(judged)
        fraction = correct / total if total else 0.0
        label = SLICE_SUBJECT_LABEL.get(subject, subject.value)
        if len(topic_ids) == 1:  # срез по одной теме — подписываем диагностику темой
            topic = self._uow.topics.get(next(iter(topic_ids)))
            if topic is not None:
                label = topic.title
        self._uow.dashboard.add_diagnostic(
            {
                "id": uuid4(),
                "student_id": student_id,
                "subject": subject,
                "occurred_on": self._today(),
                "topic_title": f"Срез — {label}",
                "tasks_total": total,
                "tasks_correct": correct,
                "percent_correct": fraction,
                "note": None,
                "details_json": details,
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

    async def grade_slice(
        self, student_id: UUID, subject: Subject, items: list[dict[str, object]]
    ) -> dict[str, object]:
        """Батч-оценка среза (сайт): оценить каждый пункт через единый грейдер, затем persist.
        На API-поверхности judge = ExactOnlyJudge → детерминированно по ключу (веб не меняем)."""
        judged = [
            await self.judge_task_answer(item["task_id"], item.get("answer_text")) for item in items
        ]
        result = self.record_slice(student_id, subject, judged)
        feedback_by_id = {str(item["task_id"]): item["feedback"] for item in judged}
        for row in result["items"]:
            row["feedback"] = feedback_by_id.get(str(row["task_id"]), "")
        return result

    def record_review_result(self, review_id: UUID, passed: bool) -> object:
        existing = self._uow.reviews.get(review_id)
        previous_status = getattr(existing, "status", None)
        item = self._uow.reviews.mark_result(review_id, review_result_to_status(passed))
        if not passed and previous_status != ReviewStatus.BACK_TO_WORK:
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
            # Часть-1 дрилл: общий грейдер (exact-авторитет + ИИ-эквивалентность по политике).
            judgment = await self._grade_answer(
                task.statement, task.expected_answer, attempt.answer_text
            )
            draft = self._drill_draft(judgment, task)
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
        if mission.ai_policy == AiPolicy.MANUAL_GATE:
            draft = replace(
                draft,
                score_percent=0.0,
                status=EvidenceStatus.NEEDS_MANUAL_REVIEW,
                next_action="Senior mentor must review this part-2 solution before progression.",
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
            "topic_id": mission.topic_id,
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
