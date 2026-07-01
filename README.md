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

cd C:\Users\badmaev_es\egeMentor\backend
.\.venv312\Scripts\python.exe -m app.adapters.telegram.bot

Что я сделал:

- Пересобрал и перезапустил bot:

  docker compose up -d --build bot
  Compose также пересоздал api, потому что образ backend общий.

- Прогнал миграции:

  docker compose exec -T api alembic upgrade head

- Проверил контейнеры:
  - api running, restart=0
  - bot running, restart=0
  - web running, restart=0
  - postgres healthy

- Проверил Telegram getMe из контейнера через proxy: OK, бот @egemathandinformbot.
- Прогнал release smoke из контейнера бота:

  docker compose exec -T -e PUBLIC_API_BASE_URL=http://api:8001 bot python scripts/release_smoke.py
  Результат: GREEN
  - API health OK
  - migrations at head
  - bot getMe OK
  - live Qwen judge OK

Команды на будущее:

docker compose up -d --build api bot
docker compose exec -T api alembic upgrade head
docker compose ps
docker compose logs bot --tail=80
docker compose exec -T -e PUBLIC_API_BASE_URL=http://api:8001 bot python scripts/release_smoke.py
