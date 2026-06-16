# EGE Mentor

Family LAN pilot for EGE preparation in profile mathematics and informatics.

The product is intentionally not a generic AI tutor. It is a guided preparation loop:

```text
plan -> mission -> independent attempt -> evidence -> review -> next mission
```

## V1 Rules

- PostgreSQL is the source of truth.
- The backend owns learning state and progression decisions.
- The frontend renders backend state and does not duplicate coaching logic.
- Attempts never move `subject_tracks.current_score`; only score events from slices/weekly variants do.
- LLM review is the production path. If the LLM fails or is disabled, evidence is saved as `needs_manual_review`.
- Hinted code attempts do not improve the clean-sheet ratio.

## Local Dev

1. Copy `.env.example` to `.env` and set `API_SHARED_TOKEN`.
2. Start Postgres:

```powershell
docker compose up -d postgres
```

3. Run migrations, seed, and import tracker data:

```powershell
cd backend
.\.venv312\Scripts\alembic.exe upgrade head
.\.venv312\Scripts\python.exe scripts\seed.py
cd ..
backend\.venv312\Scripts\python.exe scripts\preview_tracker.py --write
```

4. Start backend and frontend:

```powershell
cd backend
.\.venv312\Scripts\uvicorn.exe app.main:app --reload --port 8001

cd ..\frontend
npm.cmd run dev
```

Open `http://127.0.0.1:5174` and enter `API_SHARED_TOKEN`.

## LAN Prod

From the repo root:

```powershell
.\scripts\prod_up.ps1
```

This builds containers, starts Postgres/API/nginx, runs Alembic, runs seed, imports the Excel tracker from `C:\Users\badmaev_es\Desktop\ЕГЭ`, and prints the LAN URL.

Backup:

```powershell
.\scripts\backup_postgres.ps1
```

Add that command to Windows Task Scheduler for daily backups.

## Verification

```powershell
cd backend
.\.venv312\Scripts\python.exe -m pytest tests -q

cd ..\frontend
npm.cmd run build
```
