# Release Checklist — EGE Mentor

## Pre-flight

- [ ] `.env` настроен: `API_SHARED_TOKEN`, `LLM_PROVIDER`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_STUDENT_CHAT_ID`
- [ ] `backend\.venv312\Scripts\python.exe -m pytest backend\tests -q` → **зелёный**
- [ ] `cd frontend` → `npm.cmd run build` → **зелёный**

## Deploy

- [ ] `.\scripts\prod_up.ps1` (или `docker compose up -d --build api bot`)

**Что пересобирать/перезапускать:**

- `api` — бэкенд FastAPI (use cases, domain, infrastructure)
- `bot` — Telegram-бот (входит в образ `backend`, extra `[bot]`, matplotlib)

**НЕ требуется перезапускать (если нет отдельной причины):**

- `web` — фронтенд. Не менялся для visual overlay (числевая прямая рендерится в боте).

> `api` и `bot` — отдельные services в docker-compose, оба билдятся из `./backend`.
> `web` билдится из `./frontend`.

## Post-deploy smoke

- [ ] `backend\.venv312\Scripts\python.exe backend\scripts\release_smoke.py` → **GREEN**
  - API health: `http://127.0.0.1:8001/api/health` → `{"status":"healthy"}`
  - Миграции на head
  - Бот getMe: токен валиден
  - Живой judge: модель доступна и возвращает `equivalent`

- [ ] Отправить drill-задачу через Telegram → получить ответ → проверить визуализацию:
  - Если `expected_answer` — интервал (неравенство/ОДЗ):
    - Картинка пришла
    - Caption без overlay: **«Решение на числовой прямой»**
  - Если `student_answer` тоже распознан как интервал:
    - Синяя линия — решение, оранжевая — ответ ученика
    - Caption с overlay: **«Синее — решение, оранжевое — твой ответ»**

- [ ] `docker compose ps` → все сервисы `UP`, bot RestartCount не растёт

## Rollback

Перед деплоем зафиксировать текущий commit: `git rev-parse HEAD`.

- [ ] `git checkout <предыдущий_коммит>` (запомнить до деплоя)
- [ ] `docker compose up -d --build api bot`
- [ ] **Не трогать** postgres volume — данные учеников должны сохраниться
- [ ] `release_smoke.py` → GREEN
- [ ] Если smoke failed: оставить как есть, не дергать `docker compose down`
