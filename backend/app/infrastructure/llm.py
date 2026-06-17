import json
import re

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.application.ports import AttemptForReview, EvidenceDraft
from app.config import LlmConnection
from app.domain.enums import ErrorCategory, EvidenceStatus

# JSON schema sent to the model so the server constrains decoding to our taxonomy
# (the enum is generated from ErrorCategory, the single source of truth). The model
# physically cannot emit a category outside the list and picks OTHER when nothing fits.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "score_percent": {"type": "number", "minimum": 0, "maximum": 100},
        "error_category": {"type": "string", "enum": [c.value for c in ErrorCategory]},
        "feedback": {"type": "string", "minLength": 1},
        "next_action": {"type": "string", "minLength": 1},
    },
    "required": ["score_percent", "error_category", "feedback", "next_action"],
    "additionalProperties": False,
}

PHONE_NOTATION_HINT = (
    "Ученики могут писать с телефона. Перед оценкой учитывай такие сокращения:\n"
    "- >_ и >= означают >= (больше или равно).\n"
    "- <_ и <= означают <= (меньше или равно).\n"
    "- кириллическая х/Х может означать латинскую x.\n"
    "- Не снижай балл только за формат записи, если математический смысл ясен.\n"
    "- Но неправильное включение границы всё равно является ошибкой: "
    "для (x-1)/(x+2) >= 0 ответ x >= 1 или x <= -2 неверен, "
    "потому что x = -2 запрещён знаменателем; слева должно быть x < -2.\n"
)


def normalize_student_notation(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = text.replace("х", "x").replace("Х", "X")
    normalized = re.sub(r">\s*_", ">=", normalized)
    normalized = re.sub(r"<\s*_", "<=", normalized)
    return normalized


class LlmEvidencePayload(BaseModel):
    score_percent: float = Field(ge=0, le=100)
    error_category: ErrorCategory
    feedback: str = Field(min_length=1)
    next_action: str = Field(min_length=1)

    @field_validator("error_category", mode="before")
    @classmethod
    def _absorb_unknown_category(cls, value: object) -> object:
        # Floor for servers that ignore the schema: any free-form label the model
        # invents becomes OTHER instead of crashing the whole review. We never try to
        # guess what an arbitrary string "really meant" — that would be the crutch.
        try:
            return ErrorCategory(value)
        except ValueError:
            return ErrorCategory.OTHER


# Rubric so the model can tell the categories apart instead of reaching for a vague
# bucket. The rule "pick the most specific category" is what keeps it off
# algorithm_logic/other unless nothing concrete fits.
CATEGORY_RUBRIC = (
    "Выбирай САМУЮ КОНКРЕТНУЮ категорию ошибки:\n"
    "- arithmetic: вычислительная ошибка (напр. из 2x-1=9 получили 2x=8 вместо 2x=10).\n"
    "- sign_transfer: перенос слагаемого через знак равенства без смены знака.\n"
    "- odz_logic: ошибка в области допустимых значений (лишние/потерянные корни, "
    "игнор ограничения знаменателя).\n"
    "- condition_reading: решение верное, но в ответ записано не то, что просили в условии.\n"
    "- probability_double_count: в теории вероятностей дважды учтено пересечение событий.\n"
    "- code_syntax: синтаксическая или рантайм-ошибка в коде.\n"
    "- code_algorithm: логическая ошибка в алгоритме кода (неверный цикл/условие/агрегация).\n"
    "- unknown_method: ученик не владеет методом или решение не предоставлено.\n"
    "- time_management: не успел по времени.\n"
    "- none: ошибок нет.\n"
    "- algorithm_logic / other: ТОЛЬКО если ни одна конкретная категория выше не подходит.\n"
)


class OpenAICompatibleReviewer:
    prompt_version = "attempt-review-v3"
    rubric_version = "ege-mentor-v1"

    def __init__(self, connection: LlmConnection) -> None:
        self._conn = connection

    async def review_attempt(self, attempt: AttemptForReview) -> EvidenceDraft:
        system = (
            "Ты проверяешь попытку ученика по подготовке к ЕГЭ. "
            "РЕШЕНИЕ УЧЕНИКА — в полях answer_text и code_text. Если хотя бы одно из них "
            "непустое, это и есть решение: оцени его по существу. НИКОГДА не пиши «решение не "
            "предоставлено» и не ставь unknown_method, если в answer_text или code_text есть текст/код. "
            "Для задач с кодом (kind=code) оценивай корректность кода по условию (instructions); "
            "единого expected_answer может не быть — это нормально. "
            "Условие задачи дано в instructions; не выдавай готовое решение, только оцени попытку. "
            "Верни строгий JSON с ключами: score_percent, error_category, feedback, next_action. "
            "feedback и next_action пиши на русском языке.\n"
            + PHONE_NOTATION_HINT
            + CATEGORY_RUBRIC
        )
        normalized_answer_text = normalize_student_notation(attempt.answer_text)
        user = {
            "subject": attempt.subject,
            "mission_title": attempt.mission_title,
            "topic_title": attempt.topic_title,
            "instructions": attempt.instructions,
            "kind": attempt.kind,
            "mode": attempt.mode,
            "answer_text": attempt.answer_text,
            "answer_text_normalized": normalized_answer_text,
            "code_text": attempt.code_text,
            "expected_answer": attempt.expected_answer,
            "threshold_percent": attempt.threshold_percent,
        }
        try:
            async with httpx.AsyncClient(timeout=self._conn.timeout) as client:
                response = await client.post(
                    f"{self._conn.base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self._conn.api_key}"},
                    json={
                        "model": self._conn.model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
                        ],
                        "temperature": 0,
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "evidence",
                                "strict": True,
                                "schema": RESPONSE_SCHEMA,
                            },
                        },
                    },
                )
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            return EvidenceDraft(
                score_percent=0.0,
                error_category=ErrorCategory.OTHER,
                feedback=f"LLM feedback failed and needs manual review: {exc}",
                next_action="Manual review is required before changing the learning plan.",
                model_id=self._conn.model,
                prompt_version=self.prompt_version,
                rubric_version=self.rubric_version,
                status=EvidenceStatus.NEEDS_MANUAL_REVIEW,
            )
        try:
            payload = LlmEvidencePayload.model_validate_json(content)
        except ValidationError as exc:
            return EvidenceDraft(
                score_percent=0.0,
                error_category=ErrorCategory.OTHER,
                feedback=f"LLM feedback failed schema validation: {exc}",
                next_action="Manual review is required before changing the learning plan.",
                model_id=self._conn.model,
                prompt_version=self.prompt_version,
                rubric_version=self.rubric_version,
                status=EvidenceStatus.NEEDS_MANUAL_REVIEW,
            )
        return EvidenceDraft(
            score_percent=payload.score_percent,
            error_category=payload.error_category,
            feedback=payload.feedback,
            next_action=payload.next_action,
            model_id=self._conn.model,
            prompt_version=self.prompt_version,
            rubric_version=self.rubric_version,
        )
