# Session Log Archive - 2026-W28

---

## 2026-07-10 - Deterministic learning planner MVP: prereq-gate + explanation

Status: реализовано и проверено локально (тесты + живое наблюдение на реальном seed); НЕ задеплоено.

- Оценка идеи Кодекса: Дейкстра — неверный инструмент (задача не shortest-path, а prerequisite-closure);
  weighted-frontier тоже преждевременен (= замороженная error-intervention логика, N=1, тюнить не на чем).
  Выбран lean-MVP: prereq-gate + объяснение; weighted отложен и подключится через `select_intervention_queue`.
- `domain/prerequisites.py` (новый): статичная `PREREQUISITES` (4 defensible-ребра Части 1 на реальных
  названиях тем) + чистый `prerequisites_met`. `domain/policies.py`: чистый презентер `describe_pick(reason)`.
- `build_daily_queue`: `passed_titles` (темы с `solved_count>0`), один gate-предикат в фильтр новых тем,
  структурный `reason` (данные) + строка `why` на каждый пик. `select_daily_queue` не тронут (reason едет
  сквозь как лишний ключ). Без миграций.
- «3 потребителя» = single-source structured `reason` + N тонких форматтеров на краю; в MVP один
  (оператор/агент). Детский/родительский тексты — позже, тем же dict, LLM ни в одном → честный след выбора.
- Инварианты целы (due→btw→new, open-count в лимит, идемпотентный source_ref, manual-review вне дрилла,
  phase/ready_mode, LLM не выбирает). Ворота работают и в ready-mode.
- Проверка: targeted pytest 17 passed (+4 новых), full backend 210 passed, ruff clean (--ignore E501),
  import-linter 2 kept/0 broken. Живьё: база «Вычисления: логарифмы…» закрыта → зависимая «Простейшие
  уравнения…» разблокирована, `why` называет пререквизит.

Open tail: решить про ADR (каталога `!DOC/adr/` нет — схему не заводил); прокинуть `why` в
`mentor_brief`/дашборд как первого видимого потребителя; детский/родительский форматтеры — когда фича
подтвердится.

---

## 2026-07-09 - MCP mentor brief и публикация сайта без домена

Status: реализовано и проверено локально; для доступности в агенте нужен reconnect MCP-клиента.

- Добавлен компактный MCP read-tool `mentor_brief(student_id, days=14)` поверх `LearningService`.
  Он отдаёт scores, retention, engagement, текущую фазу, темы для внимания, краткие попытки,
  ошибки, очереди ревью/manual review и next actions, но не отдаёт полные `answer_text`/`code_text`.
- Сырые данные остаются в Postgres и доступны через существующие drill-down tools:
  `program_progress`, `attempt_history`, `error_journal`, `reviews`, `manual_reviews`,
  `topic_theory`. Решение без pgvector намеренное: сейчас нужна компактная deterministic summary,
  а не семантический поиск.
- Добавлен runbook `!DOC/operations/PUBLISHING_SITE.md`: домен не обязателен. Базовый путь —
  Tailscale Serve для семейного tailnet; временный публичный путь — Cloudflare Quick Tunnel;
  стабильный публичный путь позже — Cloudflare Tunnel + Access с доменом.
- Добавлен public/student build flag `VITE_OPERATOR_MODE_AVAILABLE`. При `false` фронт скрывает
  operator toggle и не показывает `/operator`; build arg прокинут через `frontend/Dockerfile` и
  `docker-compose.yml`, `.env.example` обновлён.
- Publish attempt: Cloudflare Quick Tunnel через Docker не заработал в текущей сети — precheck
  показал блокировку outbound к Cloudflare Tunnel edge (`7844`, QUIC/TCP). Установлен Tailscale
  `1.98.8`; host уже авторизован в tailnet (`100.113.226.52`). `tailscale serve` CLI в Windows
  окружении зависает при установке config, поэтому текущая рабочая публикация — прямой tailnet URL
  `http://100.113.226.52:8088`.
- Runtime switched: локальный `.env` выставлен на
  `PUBLIC_FRONTEND_BASE_URL=http://100.113.226.52:8088` и `VITE_OPERATOR_MODE_AVAILABLE=false`;
  `web` пересобран, `bot` перезапущен. Проверено: web HTML `200`, `GET /api/health` через
  Tailscale IP возвращает `{"status":"healthy"}`, bot env видит новый URL, release smoke GREEN.
- Проверка: targeted pytest `26 passed`; full backend pytest `206 passed`; frontend
  `npm.cmd run build` OK; ruff по затронутым файлам с `--ignore E501` clean. Широкий ruff падает
  только на 4 старые E501.

Open tail: остановить вручную запущенный `python -m app.adapters.mcp.server` (`Ctrl+C`) и
перезапустить MCP-клиент/Codex/Claude, чтобы он сам поднял stdio-сервер и увидел `mentor_brief`.
Для ученицы: поставить/включить Tailscale на её устройстве в том же tailnet и открыть
`http://100.113.226.52:8088`.

Follow-up: добавлена отдельная инструкция для ученицы
`!DOC/operations/STUDENT_SITE_ACCESS.md` с прямыми ссылками на Tailscale download, сайт,
разделы `/program`, `/daily`, `/slice`, `/review`, визуализацию по векторам и Telegram-бота.
Также ужесточён `docker-compose.yml`: `api` и `postgres` теперь опубликованы только на
`127.0.0.1`, внешней/tailnet-точкой остаётся `web:8088`; после `docker compose up -d`
проверено `GET /api/health` через Tailscale IP и release smoke GREEN.

---

## 2026-07-09 - Visual feedback hardening: приватные ссылки и скалярное произведение

Status: реализовано, проверено и выкачено live; нужен reconnect ege-MCP.

- По обратной связи ученицы “визуализация не открывается” Telegram больше не отправляет прямую ссылку,
  если `PUBLIC_FRONTEND_BASE_URL` — private/LAN/localhost URL. Для текущего `http://192.168.1.60:8088`
  бот пишет: `Визуализация есть на сайте: «Программа» → эта тема.`
- `_task_text` больше не добавляет общий хвост “кратко распиши ход...” поверх уже заданных `instructions`;
  дриллы “отправь ответ числом” не получают противоречивую вторую инструкцию.
- В seed добавлена concept card `Скалярное произведение в координатах` (`vector_dot_product`) для темы
  `Векторы`; frontend `/theory/:topicId` получил простой SVG-рендер формулы `a·b = x1·x2 + y1·y2`.
  Карточки темы сортируются по title, поэтому scalar-product карточка идёт первой.
- Проверка: targeted pytest `28 passed`; full backend pytest `205 passed`; frontend `npm.cmd run build` OK;
  targeted ruff clean; Docker deploy сделан (`api` + seed + `bot web`), release smoke GREEN.
- Live check: API `/api/topics/00000000-0000-0000-0000-000000005012/theory` отдаёт
  `vector_dot_product` и `vector_2d`; live bot-text не содержит `192.168`; web route `/theory/...5012` отдаёт 200.

Open tail: reconnect ege-MCP. Текущий MCP-процесс всё ещё старый: `topic_theory` tool не виден,
а `program_progress` не отдаёт `visual_ready`. После reconnect проверить MCP `program_progress`/`topic_theory`.

---

## 2026-07-08 - Visual concept cards v1 для векторов и производной

Status: реализовано, проверено и выкачено live; нужен reconnect ege-MCP.

- Добавлена backend-модель `theory_cards` + alembic `e6f7a8b9c0d1`, порт/репозиторий,
  `LearningService.list_topic_theory`, API `GET /topics/{topic_id}/theory` и MCP read-tool
  `topic_theory(topic_id)`.
- `visual_ready` прокинут отдельно от `/ready`: в `program_progress`, mission payload и slice draw.
  `theory_ready` остаётся отметкой ученицы «теорию изучила», а не наличием визуального материала.
- Seed добавляет approved concept cards без ключей ответов: `Векторы` (`vector_2d`) и
  `Производная: геометрический смысл` (`derivative_tangent`).
- Telegram `/today` и `/slice` добавляют ссылку на `/theory/<topic_id>`; сайт получил маршрут
  `/theory/:topicId` с локальными SVG-рендерами и ссылками из «Программы», «Сегодня», «Среза».
- Regression: `test_theory_cards.py` + bot-тесты на ссылки; проверка — backend pytest `204 passed`,
  frontend `npm.cmd run build` OK, Docker web build OK, ruff clean на новом `test_theory_cards.py`.
- Live deploy: `docker compose up -d --build api`, `alembic upgrade head` до `e6f7a8b9c0d1`,
  `python scripts/seed.py`, затем `docker compose up -d --build bot web`. Контейнеры running/healthy,
  release smoke GREEN, `/theory/00000000-0000-0000-0000-000000005012` отдаёт 200, live service check
  видит `visual_ready=True` для `Векторы` и `Производная: геометрический смысл`.

Open tail: reconnect ege-MCP. Текущий MCP-процесс в этой сессии держит старый код: нового
`topic_theory` tool нет, а `program_progress` ещё не отдаёт `visual_ready`. После reconnect проверить
MCP `program_progress`/`topic_theory`.

---

## 2026-07-08 - UI-хвосты /ready + деплой (миграция, rebuild, smoke)

Status: сделано и выкачено live; для MCP-теста доставки — нужен reconnect ege-MCP.

- Три задачи из карточки (backend уже был готов):
  1. Текст пустой очереди в боте → «На сегодня всё сделано ✅ Новая порция — завтра утром» (`_send_next`); тест перенацелен.
  2. Карта фазы в `/progress` (`_progress_text`): «📚 Фаза «label» (дд.мм – дд.мм)», «Закрыто X из Y · в работе · на повторении», «Дальше: …» (до 3 открытых тем).
  3. Бейдж «📖 теория изучена» на «Программе»: поле `theory_ready` добавлено в `ProgramTopicOut` (pydantic его резал!) + TS-тип + бейдж `badge--ready` + CSS.
- Деплой: alembic `c0d1e2f3a4b5 → d5a6b7c8e9f0` применён к живой БД (theory_ready_at); `docker compose up -d --build api bot web`.
- Проверка: pytest `198 passed`, ruff чист, фронт tsc чист; live: api `healthy`, bot `healthy`, `/program` отдаёт `theory_ready`, runtime-smoke GREEN (`getMe @egemathandinformbot`, логи чистые).

Open tail: переподключить ege-MCP (текущий процесс держит код до `telegram_send`), затем проверить: MCP `publish_feedback` сразу шлёт в ТГ; `/send` из родительского чата; `/ready`-переключение тем + бейдж на «Программе».

---

## 2026-07-07 - /ready: отметка «теорию изучила» управляет новыми темами очереди

Status: реализовано и проверено локально; для live нужны alembic upgrade + rebuild api/bot.

- Колонка `topics.theory_ready_at` (миграция `d5a6b7c8e9f0`), `set_theory_ready` в репо/порте.
- `build_daily_queue`: при наличии хоть одной отметки новые дриллы идут только по отмеченным темам любой начавшейся фазы; неотмеченные темы текущей фазы придерживаются; без отметок — прежнее поведение. Ready-тема без свежей задачи попадает в shortage, не пропускается тихо.
- Сервис: `list_theory_ready_candidates` (открытые темы начавшихся фаз с банком, без manual-path) + `set_topic_theory_ready`; `theory_ready` виден в `list_program` / `program_progress`.
- TG: `/ready` + кнопка меню, inline-toggle с перерисовкой клавиатуры, «Готово» с итогом; help/команды обновлены; unauthorized-колбэки отбиваются.
- Перед слайсом закоммичен завершённый Codex-слайс telegram_send (`1833f8f`, 191 passed).

Verification: backend pytest `198 passed` (35 в test_bot, 4 новых queue-теста); ruff по затронутым файлам чист.

Open tail: деплой (alembic + rebuild), три простых задачи Кодексу в карточке (текст пустой очереди, карта фазы в /progress, бейдж на «Программе»).

---

## 2026-07-07 - Единая доставка заметок в Telegram (publish = отправка)

Status: реализовано, тесты зелёные; для live нужен rebuild api+bot и reconnect MCP.

- Проблема: `publish_feedback` клал заметку только в ленту; в Telegram она уходила лишь утренним пушем. Ручная отправка требовала `docker compose exec` (неэффективно).
- Новый модуль `app/infrastructure/telegram_send.py` — одна функция доставки `deliver_pending_notes(settings, student_id)` (sync urllib+прокси, self-contained, без aiogram; работает из любого процесса) + `send_telegram_message`. Это «1 функция везде».
- Подключено в трёх точках: MCP `publish_feedback` (сразу досылает, при ошибке ТГ — raise, заметка уже в ленте), API-роут `publish_mentor_note` = веб-форма оператора (то же, ошибка → HTTP 502), утренний пуш бота (переведён на общую функцию через `asyncio.to_thread`; старые aiogram `_deliver_mentor_notes`/`_notify_parent`/`_split_for_telegram` удалены).
- Ручной ТГ-канал родителя: команда `/send <текст>` в боте (только из `telegram_parent_chat_id`) — публикует заметку и сразу доставляет ученику.
- Заодно ранее в этой сессии: снят токен-гейт фронта (`App.tsx`) + `API_SHARED_TOKEN=` пусто; отправлена (вручную, exec) заметка Ульяне по срезу процентов 4/5.
- Проверка: `pytest` 191 passed (3 теста доставки перенацелены на `deliver_pending_notes`); ruff чист по новым файлам (осталась предсуществующая E501 в сигнатуре `publish_feedback`).

Open tail: выкатить — `docker compose up -d --build api bot` и переподключить MCP-сервер (текущий процесс держит старый код без `telegram_send`). После rebuild — проверить `/send` из родительского чата и что MCP-публикация сразу видна в ТГ.

---

## 2026-07-07 - Live Telegram attempt check via MCP

Status: in-progress slice not visible until completion.

- Checked the live student state through MCP while the learner was reportedly solving a slice and had sent one task through Telegram.
- `attempt_history`, `weekly_digest`, and `manual_reviews` did not show a fresh learner attempt; the latest attempts are still the operator-recovery records from the daily-mission outage recovery.
- The pending manual-review item is the old 2026-06-17 ODZ attempt, not today's Telegram submission.
- Runtime checks stayed green: `bot` is healthy, Telegram `getMe` succeeds, and `api`/`bot` logs had no errors in the checked window.
- Follow-up from the live chat confirmed the bot was processing the slice and returning verdicts. Code check: Telegram slice answers are kept in the in-process `_srez` session and persisted through `record_slice` only after the final task in the slice; MCP read tools see the completed diagnostic, not intermediate 1/5 answers.

Open tail: after the learner finishes all 5 slice tasks, re-check MCP `diagnostics` / `weekly_digest`; if the completed slice is still absent, inspect Telegram DB wiring or the final `record_slice` path.

---

## 2026-07-07 - Local service stack start

Status: running and verified.

- Confirmed the Docker stack with `docker compose up -d`: `postgres`, `api`, `web`, and `bot` are running; `postgres` and `bot` report healthy.
- Verified API health at `http://127.0.0.1:8001/api/health` and Docker web at `http://127.0.0.1:8088`.
- Started the Vite dev frontend through the Windows scheduled task `egeMentorFrontendDev`; `http://127.0.0.1:5174` returns HTTP 200.

Verification: `docker compose ps`; API health `healthy`; Vite dev frontend HTTP 200.

---

## 2026-07-07 - Daily mission recovery via MCP

Status: applied live and guarded.

- Used MCP read/write tools first: all due review cards through 2026-07-07 were marked passed, dropping operator-facing `due_reviews` to 0.
- Added MCP recovery tools backed by `LearningService`: `operator_close_daily_missions` records `operator-recovery` attempts/evidence and normal progression; `operator_skip_daily_missions` retires mistaken daily missions without learning evidence.
- Invoked the updated MCP server over stdio to close 5 stale open `daily:` missions as guardian-trusted completed work after the Telegram polling outage.
- A fresh queue build initially exposed 4 part-2 topics as daily drills; those 4 missions were retired as `skipped`, and `build_daily_queue` now excludes current part-2/manual-review topics from auto daily drills.
- Rebuilt/recreated live `api` and `bot` so the guard is active in the running services.

Verification: daily queue tests `9 passed`; task-bank/MCP-adjacent tests `5 passed`; full backend suite `191 passed`; frontend build green; release smoke GREEN; Telegram runtime smoke GREEN; `bot` is healthy.

Open tail: the current connected Codex MCP namespace will not hot-reload the two new tools until MCP reconnect/restart; the updated server was used via stdio for the live recovery.

---

## 2026-07-07 - Telegram polling regression guard

Status: implemented and verified locally.

- Added an in-process Telegram polling watchdog: repeated aiogram update/proxy/network failures now make the bot process exit with a non-zero code, letting Docker `restart: unless-stopped` recover it.
- Added container healthcheck `backend/scripts/telegram_getme_health.py` and wired it to the `bot` service in `docker-compose.yml`.
- Added read-only host smoke `backend/scripts/telegram_bot_runtime_smoke.py`: checks bot service state, fresh polling logs, and in-container Telegram `getMe`.
- Updated release checklist with the new runtime smoke before manual Telegram drill verification.
- Rebuilt/recreated the live `bot` path so the watchdog and Docker healthcheck are active now; Compose also recreated `api` from the shared backend image.

Verification: focused bot tests `18 passed`; full backend suite `188 passed`; frontend build green; release smoke GREEN after escalation; live runtime smoke GREEN; `bot` is `healthy`.

Open tail: ask the student to resend daily mission answers that may have been sent while polling was broken.

---

## 2026-07-07 - Telegram bot polling recovery

Status: fixed operationally and verified live.

- Investigated the mismatch between reported daily-mission work and empty attempt ledger.
- Confirmed no attempts/evidence after 2026-07-01, while Telegram bot logs were flooded with update-polling network/proxy failures.
- Confirmed direct Telegram API access from the bot container times out; the configured proxy is required.
- Verified the configured proxy can reach Telegram `getMe`, then restarted only the `bot` service.
- Post-restart verification: `egementor-bot-1` stayed up for 4 minutes, proxy `getMe` returned OK, and fresh bot logs had no `Failed to fetch updates` / `ProxyConnectionError` / `TelegramNetworkError`.

Verification: `docker compose restart bot`; `docker compose ps bot`; `docker compose logs bot --since 4m` error filter clean; in-container Telegram `getMe` OK.

Open tail: ask the student to resend the daily mission answers, because messages sent while polling was broken did not enter the product ledger.

---

## 2026-07-06 - Qwen follow-up: part-2 topic, manual gate lifecycle, intervention selector

Status: implemented and verified locally.

- Fixed the seeded part-2 #13 topic mismatch: task `part2-13-text-a` now belongs to the math topic `Задача 13: тригонометрическое уравнение`, and part-2 manual-gate missions take `topic_id` from their linked task to prevent future task/mission drift.
- Added the missing manual-gate lifecycle regression: submit text solution -> appears in manual-review queue -> manual PASSED verdict -> mission DONE -> +7/+30 review cards scheduled.
- Made manual-review queue show only unresolved `NEEDS_MANUAL_REVIEW` evidence; append-only evidence history stays intact after the manual verdict.
- Added pure, not-yet-wired `select_intervention_queue(...)`: requires repeated actionable category count >=2, ignores `none`/`other`, orders by count then category for deterministic future routing.
- Fixed weekly `T-lint-imports` command to call `python -m importlinter.cli`.

Verification: focused Qwen follow-up tests `14 passed`; full backend suite `187 passed`; frontend build green; weekly queue JSON parsed; import-linter rc=0.

Open tail: deterministic repeated-error intervention remains frozen until weekly-review data is available; selector is covered but not connected to queue creation.
