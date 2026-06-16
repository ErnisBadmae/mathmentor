# EGE Mentor

Family pilot for EGE preparation in profile mathematics and informatics.

The product is intentionally not a generic AI tutor. It is a guided preparation loop:

```text
plan -> mission -> independent attempt -> evidence -> review -> next mission
```

## Architecture stance

- PostgreSQL is the product source of truth.
- The backend owns learning state and progression decisions.
- The frontend renders backend state and does not duplicate coaching logic.
- LLMs are replaceable infrastructure ports used for bounded tasks: feedback, error classification, and audit generation.
- Every AI-produced evidence record must carry `model_id`, `prompt_version`, and `rubric_version`.
- No vector DB, graph DB, voice layer, queue, or public SaaS features in v1.

## Local layout

```text
backend/   FastAPI application, domain, application services, DB adapters
frontend/  Vite React dashboard
scripts/   operator/import helpers
docs/      product and architecture notes
```

## Quick start

1. Copy `.env.example` to `.env` and adjust values.
2. Start Postgres:

```powershell
docker compose up -d postgres
```

3. Install backend dependencies in a virtual environment:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\uvicorn app.main:app --reload --port 8001
```

4. Start frontend:

```powershell
cd frontend
npm install
npm run dev
```

The first production-grade slice is dashboard + mission list + attempt submission + evidence/review updates.
