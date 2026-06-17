"""E2E coverage for the local-model (llama.cpp / vllm) LLM reviewer.

The real GPU box is not reachable from CI, so the OpenAI-compatible HTTP call is
faked at the httpx boundary. These tests prove the wiring the student depends on:
the configured local provider is reached with the right URL/model/timeout/auth,
a valid model response becomes PASSED evidence end-to-end, and any failure mode
fails closed to manual review instead of inventing a score.
"""

import asyncio
import json

import httpx
import pytest
from sqlalchemy import select

from app.application.ports import AttemptForReview
from app.application.use_cases import LearningService
from app.config import LlmConnection, Settings
from app.domain.enums import (
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    MissionStatus,
    Subject,
)
from app.infrastructure.llm import OpenAICompatibleReviewer
from app.infrastructure.models import EvidenceORM, MissionORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork

LLAMA_CONN = LlmConnection(
    base_url="http://192.168.0.18:8000/v1",
    api_key="token-abc123",
    model="Qwen3.6-35B-A3B-Q5-256K",
    timeout=120,
)


@pytest.fixture()
def llm_http(monkeypatch):
    """Fake the local model's /chat/completions endpoint at the httpx layer."""
    state: dict = {"calls": {}, "content": None, "error": None}

    class FakeResponse:
        def raise_for_status(self) -> None:
            if state["error"] is not None:
                raise state["error"]

        def json(self) -> dict:
            return {"choices": [{"message": {"content": state["content"]}}]}

    class FakeAsyncClient:
        def __init__(self, timeout=None) -> None:
            state["calls"]["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        async def post(self, url, headers=None, json=None):
            state["calls"].update(url=url, headers=headers, json=json)
            return FakeResponse()

    monkeypatch.setattr("app.infrastructure.llm.httpx.AsyncClient", FakeAsyncClient)
    return state


def _attempt() -> AttemptForReview:
    return AttemptForReview(
        subject=Subject.MATH_PROFILE,
        mission_title="Решить уравнение с учётом ОДЗ",
        topic_title="Уравнения и неравенства с ОДЗ",
        kind=AttemptKind.TEXT,
        mode=AttemptMode.CLEAN_SHEET,
        answer_text="x=4",
        code_text=None,
        expected_answer="4",
        threshold_percent=80,
        instructions="Реши уравнение, отдельно проверь каждый корень на ОДЗ.",
    )


def _model_reply(score: float = 90, category: str = "none") -> str:
    return json.dumps(
        {
            "score_percent": score,
            "error_category": category,
            "feedback": "ok",
            "next_action": "next",
        }
    )


def test_reviewer_calls_local_provider_with_resolved_connection(llm_http):
    llm_http["content"] = _model_reply()

    draft = asyncio.run(OpenAICompatibleReviewer(LLAMA_CONN).review_attempt(_attempt()))

    assert draft.status is None
    assert draft.score_percent == 90
    assert draft.error_category == ErrorCategory.NONE
    assert draft.model_id == "Qwen3.6-35B-A3B-Q5-256K"
    calls = llm_http["calls"]
    assert calls["url"] == "http://192.168.0.18:8000/v1/chat/completions"
    assert calls["headers"]["Authorization"] == "Bearer token-abc123"
    assert calls["json"]["model"] == "Qwen3.6-35B-A3B-Q5-256K"
    assert calls["timeout"] == 120
    # Decoding is constrained to our taxonomy via a json schema built from the enum.
    response_format = calls["json"]["response_format"]
    assert response_format["type"] == "json_schema"
    enum = response_format["json_schema"]["schema"]["properties"]["error_category"]["enum"]
    assert "arithmetic" in enum and "other" in enum
    # The mission's full task text reaches the model, not just the title.
    user_payload = calls["json"]["messages"][1]["content"]
    assert "проверь каждый корень на ОДЗ" in user_payload


def test_unknown_category_is_absorbed_as_other_not_manual_review(llm_http):
    # A server that ignores the schema may still return a free-form label; absorb it
    # as OTHER and keep a valid review instead of falling back to manual review.
    llm_http["content"] = json.dumps(
        {
            "score_percent": 50,
            "error_category": "incorrect_answer",
            "feedback": "Ответ не совпал с ожидаемым.",
            "next_action": "Повтори тему.",
        }
    )

    draft = asyncio.run(OpenAICompatibleReviewer(LLAMA_CONN).review_attempt(_attempt()))

    assert draft.status is None
    assert draft.error_category == ErrorCategory.OTHER
    assert draft.score_percent == 50


def test_http_error_fails_closed_to_manual_review(llm_http):
    llm_http["error"] = httpx.HTTPError("connection refused")

    draft = asyncio.run(OpenAICompatibleReviewer(LLAMA_CONN).review_attempt(_attempt()))

    assert draft.status == EvidenceStatus.NEEDS_MANUAL_REVIEW


def test_invalid_schema_fails_closed_to_manual_review(llm_http):
    llm_http["content"] = '{"score_percent": 200}'  # out of range, missing fields

    draft = asyncio.run(OpenAICompatibleReviewer(LLAMA_CONN).review_attempt(_attempt()))

    assert draft.status == EvidenceStatus.NEEDS_MANUAL_REVIEW


def test_local_model_review_closes_mission_end_to_end(seeded_session, llm_http):
    llm_http["content"] = _model_reply(score=90)
    mission = seeded_session.scalar(select(MissionORM).order_by(MissionORM.id))
    service = LearningService(
        SqlAlchemyUnitOfWork(seeded_session), OpenAICompatibleReviewer(LLAMA_CONN)
    )

    result = asyncio.run(
        service.submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "x=4",
            }
        )
    )

    assert result["status"] == EvidenceStatus.PASSED
    assert seeded_session.get(MissionORM, mission.id).status == MissionStatus.DONE
    evidence = seeded_session.get(EvidenceORM, result["evidence_id"])
    assert evidence.model_id == "Qwen3.6-35B-A3B-Q5-256K"
    assert evidence.prompt_version == "attempt-review-v3"


def test_failed_local_review_marks_repeat_end_to_end(seeded_session, llm_http):
    llm_http["content"] = _model_reply(score=50, category="sign_transfer")
    mission = seeded_session.scalar(select(MissionORM).order_by(MissionORM.id))
    service = LearningService(
        SqlAlchemyUnitOfWork(seeded_session), OpenAICompatibleReviewer(LLAMA_CONN)
    )

    result = asyncio.run(
        service.submit_attempt(
            {
                "mission_id": mission.id,
                "kind": AttemptKind.TEXT,
                "mode": AttemptMode.CLEAN_SHEET,
                "answer_text": "wrong",
            }
        )
    )

    assert result["status"] == EvidenceStatus.FAILED
    assert seeded_session.get(MissionORM, mission.id).status == MissionStatus.REPEAT


def test_llm_connection_resolves_active_provider():
    llama = Settings(llm_provider="llama_cpp").llm_connection()
    assert llama is not None
    assert llama.base_url == "http://192.168.0.18:8000/v1"
    assert llama.model == "Qwen3.6-35B-A3B-Q5-256K"
    assert llama.timeout == 120

    vllm = Settings(llm_provider="vllm", vllm_model="qwen-local", vllm_timeout=99).llm_connection()
    assert vllm is not None
    assert vllm.model == "qwen-local"
    assert vllm.timeout == 99


def test_disabled_provider_has_no_connection():
    assert Settings(llm_provider="disabled").llm_connection() is None
