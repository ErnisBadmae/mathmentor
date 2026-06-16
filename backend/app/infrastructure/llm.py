import json

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.application.ports import AttemptForReview, EvidenceDraft
from app.config import Settings
from app.domain.enums import ErrorCategory, EvidenceStatus


class LlmEvidencePayload(BaseModel):
    score_percent: float = Field(ge=0, le=100)
    error_category: ErrorCategory
    feedback: str = Field(min_length=1)
    next_action: str = Field(min_length=1)


class OpenAICompatibleReviewer:
    prompt_version = "attempt-review-v1"
    rubric_version = "ege-mentor-v1"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def review_attempt(self, attempt: AttemptForReview) -> EvidenceDraft:
        system = (
            "You review EGE preparation attempts. Return strict JSON with keys: "
            "score_percent, error_category, feedback, next_action. Do not solve before an attempt."
        )
        user = {
            "subject": attempt.subject,
            "mission_title": attempt.mission_title,
            "topic_title": attempt.topic_title,
            "kind": attempt.kind,
            "mode": attempt.mode,
            "answer_text": attempt.answer_text,
            "code_text": attempt.code_text,
            "expected_answer": attempt.expected_answer,
            "threshold_percent": attempt.threshold_percent,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self._settings.openai_compat_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self._settings.openai_compat_api_key}"},
                    json={
                        "model": self._settings.openai_compat_model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
                        ],
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
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
                model_id=self._settings.openai_compat_model,
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
                model_id=self._settings.openai_compat_model,
                prompt_version=self.prompt_version,
                rubric_version=self.rubric_version,
                status=EvidenceStatus.NEEDS_MANUAL_REVIEW,
            )
        return EvidenceDraft(
            score_percent=payload.score_percent,
            error_category=payload.error_category,
            feedback=payload.feedback,
            next_action=payload.next_action,
            model_id=self._settings.openai_compat_model,
            prompt_version=self.prompt_version,
            rubric_version=self.rubric_version,
        )
