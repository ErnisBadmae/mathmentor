# Architecture

EGE Mentor is a modular monolith with clear boundaries.

## Layers

- `domain`: typed concepts and deterministic policies. No FastAPI, SQLAlchemy, Telegram, or LLM imports.
- `application`: use cases and ports. This layer decides how a submitted attempt changes product state.
- `infrastructure`: database repositories, LLM clients, importers, and file storage.
- `adapters`: HTTP API and Telegram delivery.

## Product state

PostgreSQL owns canonical state: student profiles, access, subject tracks, topics, missions, attempts, evidence, error events, spaced reviews, and weekly audits.

Derived summaries can be cached later, but no derived store may be required to choose the next mission.

## LLM boundary

The LLM is a bounded evaluator, not the product brain. It may classify a solution and explain mistakes, but domain/application code owns thresholds, clean-sheet metrics, review scheduling, and next mission selection.

Every LLM result must include `model_id`, `prompt_version`, and `rubric_version`. If structured validation fails, save the attempt and mark evidence as needing manual review.

## What is intentionally absent

- LangGraph or autonomous agent routing
- Qdrant, Neo4j, CDC, queues
- voice/STT/TTS
- public registration and payments
- shared libraries before both projects prove stable common code
