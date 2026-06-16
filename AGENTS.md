# AGENTS.md

Compact bootstrap memory for Codex and other terminal agents working inside `egeMentor`.

## Project Summary

EGE Mentor is a family-pilot preparation system for Russian EGE profile mathematics and informatics.

The product is **not** a generic AI tutor and not a toolbox. It is a guided preparation loop:

```text
plan -> mission -> independent attempt -> evidence -> review -> next mission
```

The first user is a real child preparing for EGE 2027. Existing preparation materials live outside the repo at:

```text
C:\Users\badmaev_es\Desktop\ЕГЭ
```

Important current observed baseline from the tracker:

- Goal: profile mathematics >= 85, informatics >= 85.
- Current rough baseline: profile mathematics 65, informatics 50.
- Programming clean-sheet ratio: 0.4.
- Current leading errors: arithmetic/sign transfer, ODZ logic, condition reading, probability double count.

## Why This Exists

The useful part of the current EngFriend project is the product discipline, not the codebase:

- backend-owned truth state
- mission progression
- structured evidence ledger
- model-agnostic LLM port
- replay/eval mindset

Do **not** import EngFriend runtime complexity. EGE Mentor is a separate sibling project because the domain, user journey, and risks are different.

## Architecture Defaults

- `backend/` is a FastAPI modular monolith.
- `frontend/` is a Vite React SPA.
- PostgreSQL is canonical for product/session/evidence state.
- The frontend renders backend truth-state and must not invent parallel coaching logic.
- Telegram is a delivery adapter only, not a planning engine.
- LLMs are bounded evaluators/classifiers, not the product brain.
- Every AI-produced evidence record must carry `model_id`, `prompt_version`, and `rubric_version`.

Layering:

```text
backend/app/domain          pure models, enums, deterministic policies
backend/app/application     use cases and ports
backend/app/infrastructure  DB repositories, LLM client, importers, storage
backend/app/adapters        FastAPI and Telegram delivery
```

Domain/application code must not depend on FastAPI, SQLAlchemy, Telegram, or concrete LLM providers.

## Product Rules

- Attempt first, AI second.
- For code: the learner writes in Thonny/local environment first, then submits code/answer for feedback.
- For math: the learner submits answer and reasoning/photo/text before any AI explanation.
- A topic closes by evidence crossing a threshold, not by time spent.
- Closed topics schedule spaced review at +7 and +30 days.
- Hinted code attempts must not improve the clean-sheet metric.
- Weekly audits should catch ?familiar task illusion?: cold tasks, timed, no AI/internet/phone.

## Current Repo State

Initial scaffold exists and is committed.

Working pieces:

- FastAPI app and health route.
- Alembic migrations and LAN-prod Docker Compose path.
- SQLAlchemy ORM models for users, invite codes, student profiles, subject tracks, topics, missions, attempts, evidence, error events, reviews, audits.
- `LearningService.submit_attempt` use case.
- append-only manual review path for LLM-disabled/failed checks.
- OpenAI-compatible LLM reviewer port with fail-closed manual review behavior.
- Excel preview/importer for the current tracker, preserving source provenance.
- React dashboard shell, daily attempt flow, error journal, review queue, manual review queue.
- Telegram parent digest helper stub.
- Domain and v1 regression tests.

Verified commands at scaffold time:

```powershell
cd C:\Users\badmaev_es\egeMentor\backend
.venv312\Scripts\python.exe -m pytest tests -q

cd C:\Users\badmaev_es\egeMentor\frontend
npm.cmd run build

cd C:\Users\badmaev_es\egeMentor
backend\.venv312\Scripts\python.exe scripts\preview_tracker.py
```

Known dev URLs when servers are running:

```text
Backend:  http://127.0.0.1:8001/api/health
Frontend: http://127.0.0.1:5174
```

## Global Plan

1. **Foundation**: keep the modular monolith clean, with PostgreSQL as truth and no hidden platform complexity.
2. **Real data import**: convert the existing Excel/Markdown preparation materials into canonical DB records.
3. **First useful product loop**: dashboard -> today?s missions -> submit attempt -> evidence -> repeat/close topic -> review queue.
4. **Parent control loop**: daily digest and weekly audit generation.
5. **LLM quality loop**: structured evaluator prompts, provenance, replayable attempts, regression tests for observed mistake types.
6. **Pilot hardening**: invite-code access, multiple family users, stable local deployment, backups.

Explicit non-goals for now:

- no public SaaS onboarding
- no payments
- no Qdrant/Neo4j/CDC
- no voice
- no LangGraph/autonomous routing
- no shared/open-source libraries until common code proves stable across projects

## Local Next Plan

The first DB-backed LAN v1 slice is implemented. Next work should harden pilot usage rather than add infrastructure.

### Step 1: Real LAN Smoke

- Copy `.env.example` to `.env`, set `API_SHARED_TOKEN`, and point `OPENAI_COMPAT_*` at the real reviewer.
- Run `.\scripts\prod_up.ps1`.
- Open the printed LAN URL from the parent machine and the child's phone.
- Submit one math attempt and one informatics code attempt, including a manual-review path.

### Step 2: Operator UX

- Add a small frontend mission-create/edit screen over the existing mission API.
- Add a score-event form for weekly variants/slices.
- Keep `current_score` tied only to score events, not daily attempts.

### Step 3: Pilot Hardening

- Schedule `.\scripts\backup_postgres.ps1` in Windows Task Scheduler.
- Add restore instructions from a `pg_dump`.
- Add regression fixtures for observed mistake types: sign transfer, ODZ over-filtering, condition reading, probability double count.

## Engineering Rules

- Always follow `.claude/rules/simplicity.md`: every change must keep complexity flat or reduce it; added complexity needs explicit product justification.
- Read only files needed for the current task.
- Prefer targeted search with `rg`.
- Keep domain logic in `domain` or `application`, not in API routes or React.
- Keep LLM calls behind ports.
- Do not add infrastructure because it is available; add it only when the product loop needs it.
- Use small, focused commits.
- Run backend tests and frontend build before reporting done.

## Useful References

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/PRODUCT_DECISIONS.md`
- `backend/app/domain/policies.py`
- `backend/app/application/use_cases.py`
- `scripts/preview_tracker.py`
