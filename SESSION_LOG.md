# Session Log

Журнал рабочих сессий. Последние записи + текущая неделя.
Старые недели — в `archive/SESSION_LOG_YYYY-Www.md`.

---

## 2026-07-14 - 12 advanced (⭐) tasks added by senior model, code-verified

Status: live bank updated; no runtime code changed.

- Learner asked for more advanced tasks but sent no new photos; senior model authored
  12 ⭐ tasks itself via `scratchpad/gen_advanced_claude.py` (seed-style ORM insert,
  idempotent by `source_ref`, `source=agent-advanced`).
- Topics: Вычисления лог/триг (3), степени и корни (3), Векторы (2), Неравенства (2),
  Простейшие уравнения (2). Every answer computed by code (sympy/Fraction) with asserts;
  `answer_is_correct` self-check 12/12; both interval answers parse via
  `parse_interval_answer`.
- Verified in live DB: 12 rows `claude-adv:*`, all APPROVED (math bank now 221 approved
  total across subjects: 209 + 12).
- Known quirk: the script's final print crashed on `∞` in the cp1251 console AFTER
  commit — cosmetic only, data intact.

Open tail: thin fresh-task topics remain Задача 13 (обе темы, 2-3 fresh) and Текстовые
задачи: движение (4 fresh); next refill spec can target them. Learner should re-photo
the cropped book task (m value).

---

## 2026-07-13 - L2a live triage and grader false-failure found

Status: two confirmations approved; grader-fix task ready; L3 remains blocked.

- L2a is committed as `939bf53`, deployed, and live Alembic head is `f7a8b9c0d1e2`.
- Approved manual tags: legacy log-difference execution miss -> `arithmetic`; reviewed
  logarithm-method error -> `unknown_method`. Five other events remain unclassified.
- Live inspection proved event `74f3e876...` false: key `7776`, submitted text starts
  `ответ 7776`, but `ExactOnlyJudge` compared the entire multiline solution and persisted
  `FAILED` with model `exact-answer`.
- Added `!DOC/operations/CODEX_GRADER_DECLARED_ANSWER.md`: a four-file deterministic
  declared-answer parser/grader regression task. No historical mutation is in its scope.

Open tail: apply the two MCP confirmations, implement and senior-review the grader fix,
then correct the historical evidence through the existing append-only manual path before L3.

---

## 2026-07-13 - L2a senior review accepted

Status: local implementation accepted; not committed or deployed.

- Reviewed the complete seven-file runtime diff against the bounded task card and graph.
- Confirmed immutable raw category, manual provenance, idempotent same-category write,
  rejection paths, MCP serialization, and a single Alembic head.
- Verification repeated: backend `218 passed`; frontend build passed; `git diff --check`
  passed; Alembic head is `f7a8b9c0d1e2`.
- Exact broad Ruff remains red only on the four previously documented E501 lines; L2a
  introduces no new Ruff finding.

Open tail: commit the verified revision, decide the live migration explicitly, then use MCP
to confirm real `other` slice errors and review journal quality before specifying L3.

---

## 2026-07-13 - Bounded L2a task card prepared for weaker Codex

Status: implementation plan only; runtime code unchanged.

- Added `!DOC/operations/CODEX_L2_CONFIRMED_ERROR_TAG.md` with fixed architecture,
  seven allowed files, deterministic confirmation rules, tests, stop conditions, and
  exact verification commands.
- Scope is L2a annotation + MCP write tool only. Raw error category stays immutable;
  `record_slice`, intervention selection, API/frontend, dashboard, and deploy are forbidden.
- The weaker model must return raw test results and diff stats; a senior review gates L3.

Open tail: hand the task card to the weaker Codex model and review its diff before any
live migration or intervention wiring.

---

## 2026-07-13 - Plan clarification: interviews do not freeze development

Status: docs clarification only; no runtime code changed.

- The first 3 interviews are a calibration batch for the interview script, not a market
  sample and not a prerequisite for development; the intended total remains 8-12.
- Renamed the no-code section in `AGENTS.md` to a parallel operating lane.
- Made explicit that L2 confirmed slice-error tagging starts now while the learner is
  recovering; mock scheduling, interviews, and the manual time journal run alongside it.

Open tail: deploy the already verified planner revision when operationally ready, then
spec and implement L2 without starting auth, payments, or tutor-cockpit work.

---

## 2026-07-14 - Bank refill spec for junior executor + child's photo tasks verified

Status: spec/docs only; no runtime code changed.

- Wrote `!DOC/operations/TASK_BANK_JULY_REFILL.md` — executor contract for a weaker
  model: part A refills July/thin math topics (economy #16, part-1 stereo/planimetry,
  inequalities/ODZ; parameter #18 excluded as non-verifiable), part B adds the
  learner's 6 photo tasks from `data/примеры задач профмат/` as an advanced block
  (`⭐ Усложнённая.` prefix, `source=book-photo`, idempotent source_ref).
- All 6 photo answers were independently recomputed by the senior session: 0,04; 27,9;
  0,4; -3; 25; 12. Photo `...064` is cropped (m value missing) and excluded. The
  learner's handwritten answer to log_0.25(64) is `3`; correct is `-3` — review material.
- Guardrails in the spec: every answer must be produced by executed code (anti-poison),
  add_task DRAFT only, no approve/deploy/code changes, stop-on-mismatch.

Open tail: run the spec in a separate junior session; senior review + approve_task
afterwards; ask the learner for a full photo of the cropped task.

---

## 2026-07-13 - Global/local plan synchronized to evidence gates

Status: strategy/docs only; no runtime code changed.

- Replaced the calendar-led `AGENTS.md` plan with the agreed North Star: profile math
  >=85 for Ulyana, 80-90% learner outcome / 10-20% interviews / 0% SaaS work.
- Global horizons now advance by evidence: valid baseline + first closed intervention,
  proven N=1 score delta, gated external workflow pilot, then product-form decision.
- Local development order is now explicit: ground truth/engagement -> confirmed error
  tagging -> human-gated intervention proposal -> part 2 -> observed visual/content needs.
- External onboarding is gated on a closed intervention loop and visible N=1 delta;
  concierge isolation uses one Docker stack per learner, not shared-tenancy code.

Verification: `git diff --check` clean apart from CRLF notices; docs audit OK with the
two pre-existing size warnings; encoding guard clean.

Open tail: execute the no-code commitments first (mock date, three interviews, manual
operator-time journal), then spec L2 confirmed slice-error tagging before implementation.

---

## 2026-07-13 - Strategy delta agreed (Claude + Codex), recorded in ACTIVE_TASK

Status: discussion only, no code changed; delta written to ACTIVE_TASK "Agreed delta".

- Primary goal made explicit: daughter >=85 (EGE-2027); effort 80-90% learner /
  10-20% interviews / 0% SaaS. Mock date reserved 2026-07-26 (move only with a new date).
- Now = wedge (workflow + tutor time savings), not data moat. Mentor minutes measured
  by manual journal, not DB timestamps.
- Error category never auto-derived from task type; confirmed-tag slice is the
  prerequisite before wiring the proactive loop.
- External pilot isolation = one Docker stack per student (ports/env parametrization
  only); design partner onboarding gated on first closed loop + visible N=1 delta.
- Added: student between-lesson engagement is the commercial gating metric (weekly
  active days KPI already measures it); content-as-COGS flipped to tutor-brings-tasks
  lock-in; parent-operator kept as fallback buyer hypothesis; TAM reframed to ~8k
  tutors (300 paying = ~4%).

Open tail: schedule first 3 tutor interviews; set up the manual minutes journal;
spec the srez-error manual-tag slice.

---

## 2026-07-13 - Product direction audit: mentor OS and pilot gate

Status: strategy reviewed from the current graph/code and the live market surface; no
runtime code changed.

- Confirmed that the current product has the evidence primitives (score events, errors,
  reviews, manual gates, mentor brief, deterministic daily queue), but proactivity stops
  at read-only recommendations: `select_intervention_queue` is intentionally not wired.
- Decided against a broad trainer launch. Current `/students/current` returns the first
  profile and access uses one shared token, so external learner access needs a minimal
  identity/assignment boundary first.
- Recommended recruiting tutor design partners now, then a concierge pilot with one tutor
  and 2-3 students who already produce comparable timed mocks.
- Product moat hypothesis: verified intervention -> outcome history and tutor operating
  leverage, not generic analytics, forecasts, content, or LLM feedback.
- Visualization should be instrumented as an intervention. JSXGraph is the preferred 2D
  path; GeoGebra commercial licensing must be resolved before paid-product dependency.

Open tail: specify the smallest proactive-loop acceptance test and the minimal external
pilot access boundary; do not implement ML forecasting or broad multi-tenant SaaS work.

---

## 2026-07-13 - platform-devkit Phase C pilot

Status: completed locally; not deployed.

- Installed `platform-devkit` editable into the root `venv`.
- Replaced `scripts/docs_maintenance.py` with a compatibility shim that delegates
  to `platform_devkit.cli.docs_maintenance`.
- Left `.claude/rules/simplicity.md` local: `platform-sync` dry-run refused it
  as unmanaged, and the local file has an egeMentor-specific Russian-dialogue
  rule that should not be overwritten by the shared preset.
- No pre-commit hook was installed in this repo because there is no
  `.pre-commit-config.yaml` yet.
- `platform-encoding-guard` found 3 real mojibake strings in
  `backend/tests/test_bot.py`; restored them to proper UTF-8 Russian text.

Verification: shim `--version` works; `platform-docs audit` runs with 2
pre-existing doc warnings (`ACTIVE_TASK` oversized, `SESSION_LOG` too long);
`platform-encoding-guard --check` clean; backend pytest 210 passed; ruff clean
on `tests/test_bot.py`.

Open tail: decide whether egeMentor should adopt a small project-specific
platform preset for repo hygiene.

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

## 2026-07-08 - UI-хвосты /ready + деплой (миграция, rebuild, smoke)

Status: сделано и выкачено live; для MCP-теста доставки — нужен reconnect ege-MCP.

- Три задачи из карточки (backend уже был готов):
  1. Текст пустой очереди в боте → «На сегодня всё сделано ✅ Новая порция — завтра утром» (`_send_next`); тест перенацелен.
  2. Карта фазы в `/progress` (`_progress_text`): «📚 Фаза «label» (дд.мм – дд.мм)», «Закрыто X из Y · в работе · на повторении», «Дальше: …» (до 3 открытых тем).
  3. Бейдж «📖 теория изучена» на «Программе»: поле `theory_ready` добавлено в `ProgramTopicOut` (pydantic его резал!) + TS-тип + бейдж `badge--ready` + CSS.
- Деплой: alembic `c0d1e2f3a4b5 → d5a6b7c8e9f0` применён к живой БД (theory_ready_at); `docker compose up -d --build api bot web`.
- Проверка: pytest `198 passed`, ruff чист, фронт tsc чист; live: api `healthy`, bot `healthy`, `/program` отдаёт `theory_ready`, runtime-smoke GREEN (`getMe @egemathandinformbot`, логи чистые).

Open tail: переподключить ege-MCP (текущий процесс держит код до `telegram_send`), затем проверить: MCP `publish_feedback` сразу шлёт в ТГ; `/send` из родительского чата; `/ready`-переключение тем + бейдж на «Программе».

## 2026-07-07 - /ready: отметка «теорию изучила» управляет новыми темами очереди

Status: реализовано и проверено локально; для live нужны alembic upgrade + rebuild api/bot.

- Колонка `topics.theory_ready_at` (миграция `d5a6b7c8e9f0`), `set_theory_ready` в репо/порте.
- `build_daily_queue`: при наличии хоть одной отметки новые дриллы идут только по отмеченным темам любой начавшейся фазы; неотмеченные темы текущей фазы придерживаются; без отметок — прежнее поведение. Ready-тема без свежей задачи попадает в shortage, не пропускается тихо.
- Сервис: `list_theory_ready_candidates` (открытые темы начавшихся фаз с банком, без manual-path) + `set_topic_theory_ready`; `theory_ready` виден в `list_program` / `program_progress`.
- TG: `/ready` + кнопка меню, inline-toggle с перерисовкой клавиатуры, «Готово» с итогом; help/команды обновлены; unauthorized-колбэки отбиваются.
- Перед слайсом закоммичен завершённый Codex-слайс telegram_send (`1833f8f`, 191 passed).

Verification: backend pytest `198 passed` (35 в test_bot, 4 новых queue-теста); ruff по затронутым файлам чист.

Open tail: деплой (alembic + rebuild), три простых задачи Кодексу в карточке (текст пустой очереди, карта фазы в /progress, бейдж на «Программе»).

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

---

## 2026-07-05 - Import-linter contracts for backend

Status: implemented and verified locally.

- Added `import-linter>=2.0` to backend `dev` extras and configured two contracts in `backend/pyproject.toml`: `app.domain` must stay pure from `app.infrastructure` / `app.adapters` / `app.application`; `app.application` must not import `app.adapters`.
- Added weekly no-prompt queue task `T-lint-imports` to `backend/scripts/night_queue_weekly.json`.
- Under these two contracts the backend already had no violations, so no source import rewrites were needed; diff stayed config-only.
- Local environment note: `pip install -e .[dev]` could not reach the package index because of proxy/socket denial, so `importlinter` + `grimp` were copied into `backend/.venv312` from the neighboring `expert-agent` venv to run the gate without changing repo runtime code.

Verification: `backend\.venv312\Scripts\python.exe -m importlinter.cli --config backend/pyproject.toml` rc=0; backend suite `182 passed`; weekly queue JSON parsed.

Open tail: if backend `.venv312` is recreated, `import-linter` will need a normal `.[dev]` install once package-index access works again.

---

## 2026-07-04 - Night runner v1.1 + unit synonyms + judge weekly gate

Status: implemented and locally verified; live calibration rerun blocked by unavailable LLM endpoint.

- Synced `backend/scripts/night_runner.py` with expert-agent v1.1 behavior: VERSION stamp, `.env` copy into isolated worktree, full command logs under run `logs/<task>/`, report tail `LOG_TAIL_CHARS=3000`; ege queue paths and `C:\tmp\egeMentor-qwen-runs` preserved.
- Added exact-answer unit synonyms in `normalize_answer`: `кб|кбайт|kb`, `мб|мбайт|mb`, `гб|гбайт|gb`; single `б` stays distinct.
- Added weekly no-prompt queue task `T-calibrate-ai-judge` with `--max-failure-rate 0.1` and `files_allowed=["data/ai_judge_disagreements.jsonl"]`; runner now enforces `files_allowed` after acceptance too.
- Calibration rerun attempted from `backend/`: judge returned `None` for 25/25 triples because `http://192.168.0.18:8000/v1` was unreachable; no valid baseline delta recorded. The unit exact case is fixed, but the current replay row is full show-work text starting with `768 кб, ...`, so raw exact remains false without extracted-answer replay.

Verification: focused grader/calibration tests `21 passed`; full backend suite `182 passed`; night runner `--dry-run` GREEN with full-log paths; weekly queue JSON parsed; `py_compile` for runner/calibration OK. `black`/`flake8` are not installed in backend venv.

Open tail: rerun `scripts/calibrate_ai_judge.py` when the local LLM endpoint is reachable; if the goal is to remove the `768 кб` show-work replay disagreement, calibration needs an extracted-answer axis, not only unit suffix normalization.

---

## 2026-07-03 - Retention KPI dashboard

Status: implemented and verified locally.

- Added dashboard `retention`: current-week active days, target 3, Wednesday risk flag, message, and current `daily_drill_size`.
- Active day v1 counts any learning contact in the current local week: attempt/evidence, diagnostic/srez, or score event; duplicate same-day events count once.
- Added dashboard card for weekly rhythm; risk state is dashboard-only, with no Telegram or mentor-note side effects.
- Added regressions for Wednesday risk, Monday non-risk, active-day dedupe, and dashboard exposure.

Verification: focused retention slice `10 passed`; full backend suite `175 passed`; frontend build green.

Open tail: commit this slice, then record the first July timed mini-mock and start weekly mentor review.

---

## 2026-07-03 - Qwen live report 093450 review

Status: reviewed; no product code changes required.

- Live nightly run `C:\tmp\egeMentor-qwen-runs\2026-07-03\report-093450.md`: 4/4 GREEN.
- Accepted: sandbox MCP contract and `manual_gate_text_solution` are guarded by tests; part-2 post-change QA passed; error-intervention readiness remains read-only.
- No urgent code from Qwen findings: attempt-mode comparison, threshold-close simulator, and error-category journal propagation can wait.
- Future blocker before unfreezing deterministic intervention: slice/srez errors currently write category `other`, and `other` already dominates `top_errors` (6); add a small Codex slice to categorize srez errors before routing by `top_error_category`.
- Frozen rule stays frozen: do not implement deterministic repeated-error daily-queue routing until 2-3 weeks of weekly-review data.
- Later operator note: if part-2 mission creation is exposed in UX/MCP flows, guard `part2:text:*` missions from accidental `ATTEMPT_FIRST`.

Verification: report acceptance was green (`test_figures` 13 passed, sandbox tests 2 passed, error/intervention slice 55 passed, part2 slice 36 passed).

Open tail: first July timed mini-mock score event, then weekly mentor review.

---

## 2026-07-03 - Manual-gate QA follow-up

Status: implemented and verified locally.

- Added a MANUAL_GATE regression through `RuleBasedReviewer`, not only `StaticReviewer`: reviewer output with nonzero score/error category still lands as `needs_manual_review`, score `0.0`, mission `active`.
- Added sandbox simulator case `manual_gate_text_solution` so `run_student_simulation()` and the sandbox MCP surface guard the part-2 fail-closed invariant every night.
- Updated sandbox script/MCP tests to assert manual-review presence, active mission state, and zero score.
- Updated weekly visualization-surface acceptance to tolerate the new non-visual sandbox case while still checking visual cases.
- Updated executor-harness docs from stale part2 readiness wording to post-change QA + manual_gate simulator coverage.

Verification: focused slice `34 passed`; simulator script `ok=true`; queue JSON parsed; nightly dry-run GREEN; weekly dry-run GREEN; full backend suite `172 passed`; frontend build green.

Open tail: commit this follow-up, then choose live deploy/reseed for #13/#15 or schedule the first July timed baseline. Deterministic repeated-error intervention remains frozen.

---

## 2026-07-03 - Morning review of nightly batch 235647

Status: reviewed; no product code changed.

- Live nightly run `C:\tmp\egeMentor-qwen-runs\2026-07-02\report-235647.md`: 4/4 GREEN (plumbing, sandbox contract, error-intervention readiness, part-2 post-change QA).
- Part-2 finding: MANUAL_GATE fail-closed invariant is only tested with StaticReviewer; needs a regression through the real reviewer path. Minor: Part2Page empty-state/filter test, task 4071 wording check at first session.
- Error-intervention finding: `top_error_category` lacks a minimum-count guard (>=2) — recorded as a design constraint for the still-frozen deterministic rule; `publish_feedback` weekly dedup untested (low, manual gate mitigates).
- Sandbox finding: worth adding simulator cases `manual_gate`, retry-then-pass, failed-attempt -> error_journal; the `manual_gate` case makes nightly QA guard the part-2 invariant.

Verification: read-only review; all acceptance in the report rc=0.

Open tail: hand the MANUAL_GATE regression + simulator `manual_gate` case to Codex as the next slice.

---

## 2026-07-02 - Nightly queue: part-2 post-change QA

Status: implemented and verified locally.

- Replaced stale `T-report-part2-manual-gate-readiness` with `T-report-part2-postchange` in `night_queue.json`, since the part-2 slice landed in `4294d09`.
- New Qwen report: read-only post-change QA of the #13/#15 text flow — fail-closed check of `MANUAL_GATE`, answer-key leak check, missing tests before the first real session.
- Acceptance: pytest (`test_v1_flow`, `test_task_bank_mcp`) + static text checks only; no npm build inside isolated worktrees (known false-RED).

Verification: acceptance replayed with exact runner argv (rc=0 both commands); `night_runner.py --dry-run` GREEN across all 4 nightly tasks.

Open tail: operator runs the live nightly batch; weekly queue untouched.

---

## 2026-07-02 - Part-2 text manual gate

Status: implemented and verified locally.

- Added `AiPolicy.MANUAL_GATE`; manual-gate attempts always become `NEEDS_MANUAL_REVIEW`, score `0.0`, and do not progress the mission before mentor verdict.
- Exposed safe mission metadata (`ai_policy`, `task_number`, `source_ref`) without exposing answer keys.
- Seeded two text-only part-2 missions for math #13/#15, linked to approved tasks with no usable autograde key.
- Added frontend `/part2`: learner selects #13/#15, submits full text reasoning, and sees manual-review pending state.
- Added regressions for manual-gate submission and seeded part-2 missions.

Verification: focused backend slice `35 passed`; full backend suite `171 passed`; frontend build green.

Open tail: commit this slice, then deploy/reseed live data only when ready to expose these missions to the learner. Deterministic repeated-error intervention remains frozen for 2-3 weeks of observation.

---

## 2026-07-02 - Qwen queue split

Status: implemented and verified locally.

- Kept `backend/scripts/night_queue.json` as the nightly core: plumbing, sandbox MCP contract, error-intervention readiness, and part-2 manual-gate readiness.
- Added `backend/scripts/night_queue_weekly.json` for broad weekly/change-triggered reports: visualization, slice/review, Telegram, bank coverage, analytics, release-smoke, and score-spine postchange.
- Added `--queue` to `backend/scripts/night_runner.py` so the weekly queue can be run explicitly.
- Documented the split and the frontend acceptance rule: Qwen worktree gates must not require `frontend/node_modules`; use static frontend source checks there and run `npm.cmd run build` from main during Codex/Claude verification.

Verification: both queue JSON files parsed; `night_runner.py` py_compile OK; nightly dry-run GREEN; weekly dry-run GREEN; backend suite `169 passed`; frontend build green.

Open tail: start the text-only part-2 manual-gate flow for #13/#15. Do not code deterministic repeated-error intervention yet.

---

## 2026-07-02 - Qwen report 214053 review

Status: reviewed and follow-up implemented locally.

- Latest completed live report: `C:\tmp\egeMentor-qwen-runs\2026-07-02\report-214053.md`.
- Result: 11 GREEN, 1 RED. The RED was `T-report-score-spine-postchange`, caused by `npm.cmd --prefix frontend run build` inside an isolated Qwen worktree without `frontend/node_modules`; the same frontend build is green in main.
- Replaced that Qwen acceptance with backend score/grader tests plus a static frontend integration check for `getScoreEvents`, dashboard query key, and operator invalidation.
- Accepted one real Qwen test gap: added regression coverage that a `topic_check` score event does not move `current_score`.
- Queue-freshness finding: broad surface reports should move to weekly/manual or change-triggered runs; nightly should stay focused on sandbox MCP, error-intervention, and part-2 readiness.

Verification: score/grader slice `20 passed`; frontend build green; queue static acceptance rc=0 via JSON argv; backend suite `169 passed`; night-runner dry-run GREEN.

Open tail: commit this follow-up, then trim/split the Qwen queue before the next live run.

---

## 2026-07-02 - Qwen live rerun review

Status: reviewed; no completed Qwen QA report was produced.

- Checked latest live report `C:\tmp\egeMentor-qwen-runs\2026-07-02\report-180331.md`: plumbing was GREEN, all report tasks were BLOCKED because main worktree was dirty.
- Committed the verified score-spine + queue slice as `edcaa70 Add score trend visibility`, making main clean for Qwen.
- Started a second live Qwen rerun from clean main; the tool call timed out while Qwen was running, then the background run hung/spawned fresh `opencode` executors without producing a consolidated report.
- Stopped the fresh 18:06-18:19 runner/executor chain; older OpenCode processes from the morning were left alone.
- No Qwen findings are accepted from the interrupted run; only `report-153010.md` remains the latest completed GREEN Qwen report.

Verification: before commit backend suite `168 passed`, frontend build green; after stopping interrupted Qwen run, main worktree was clean.

Open tail: rerun live Qwen from clean checkout with longer operator-side timeout or a reduced queue, then review the raw consolidated report.

---

## 2026-07-02 - Qwen nightly queue refresh

Status: implemented and verified locally.

- Replaced stale `T-report-score-spine-readiness` with `T-report-score-spine-postchange` for the implemented score-events endpoint, dashboard score trend, weekly digest scores, and operator invalidation.
- Added `T-report-sandbox-mcp-contract` so Qwen reviews only the deterministic sandbox MCP/simulator boundary, not senior mentor MCP write tools.
- Added `T-report-night-queue-freshness` to keep nightly reports aligned with `ACTIVE_TASK.md` and the latest session log.
- Updated `ACTIVE_TASK.md`: next live Qwen run should happen only from a clean checkout after this score-spine + queue slice is committed.

Verification: night queue JSON parse OK; focused score/sandbox acceptance `21 passed`; backend suite `168 passed`; frontend build green; `night_runner.py --dry-run` GREEN across all queued tasks; `git diff --check` clean except CRLF warnings.

Open tail: commit this slice, then run live `backend\.venv312\Scripts\python.exe backend\scripts\night_runner.py` and review raw reports.

---

## 2026-07-02 - Score-spine visibility

Status: implemented and verified locally.

- Added read-side score history: `ScoreRepository.list_events`, `LearningService.list_score_events`, and `GET /students/{student_id}/score-events`.
- Added score-spine data to `weekly_digest`: recent score events and latest current/target/gap by subject.
- Added dashboard "Тренд баллов" panel using backend score events, with latest score, event kind/date/note, and delta to the previous score event per subject.
- Invalidated the new `score-events` query after operator score-event creation.
- Added score history, endpoint, and weekly digest regression tests.

Verification: focused score/digest tests `19 passed`; backend suite `168 passed`; frontend build green.

Open tail: commit this slice, then schedule/record the first July timed mini-mock and start weekly error-journal review.

---

## 2026-07-02 - Qwen proven-delta report review

Status: reviewed live report; no code changes from findings yet.

- Latest report: `C:\tmp\egeMentor-qwen-runs\2026-07-02\report-153010.md`.
- GREEN: all 10 tasks, including new score-spine, error-intervention, and part-2 manual-gate readiness reports.
- Highest-value implementation slice: expose score-event history and show timed-mock trend toward 85/85 on dashboard/weekly digest.
- Error intervention remains process-first: weekly `error_journal` review + `publish_feedback`, then deterministic queue rule only after observed repetition.
- Part 2 should start text-only with existing manual review/fail-closed path for #13/#15; photo/OCR is a later UX layer.
- Lower-priority gaps: visual bar-chart correct-answer simulator case, review double-PASS/idempotency tests, slice/daily duplicate guard, Telegram callback/media/streak tests, and content gaps in #13/#16/informatics divisors/graphs.

Verification: report acceptance in Qwen run was GREEN; no runtime code changed in this review.

Open tail: implement score-spine visibility after committing current doc/queue and probability-bank work.

---

## 2026-07-02 - Proven-delta strategy alignment

Status: implemented and verified locally.

- Replaced the stale LAN/scaffold global and local plans in `AGENTS.md` with the proven-delta strategy: monthly timed score events, error-to-intervention review, part-2 manual-gated evidence, targeted content depth, and hygiene.
- Updated `ACTIVE_TASK.md` so the current goal is strategy execution with Qwen as a bounded read-only/mechanical executor.
- Added three read-only Qwen report tasks to `backend/scripts/night_queue.json`: score-spine readiness, error-intervention readiness, and part-2 manual-gate readiness.
- Kept Qwen out of architecture/product decisions; new tasks are reports with existing pytest acceptance and report-file-change RED behavior.

Verification: night queue JSON parsed; strategy acceptance test slice `59 passed`; backend suite `165 passed`; frontend build green; `night_runner.py --dry-run` GREEN.

Open tail: commit these doc/queue changes, then run the next live Qwen batch and review raw reports before coding L1/L2/L3 slices.

---

## 2026-07-02 - Probability content-bank expansion

Status: implemented and verified locally.

- Expanded the approved probability task bank from 3 to 10 tasks in `seed.py`.
- Added 7 exact-answer probability tasks covering independent multiplication, complement, at-least-one via complement, conditional probability, without replacement, three-trial counting, and disjoint union.
- Kept existing probability visual source_ref gate unchanged: only the three reviewed visual tasks render diagrams; the new tasks are regular exact-answer drills/slices.
- Added a seed regression test that asserts all 10 probability source_refs are present and checks fraction answers for the nontrivial cases.

Verification: probability bank focused tests `9 passed`; backend suite `165 passed`; frontend build green; night-runner dry-run GREEN.

Open tail: commit this content batch. To affect live data, run the seed/update path during deploy/reseed; otherwise continue with math foundations or informatics content gaps.

---

## 2026-07-02 - TG/review hardening from Qwen findings

Status: implemented and verified locally.

- Reviewed full GREEN Qwen report `C:\tmp\egeMentor-qwen-runs\2026-07-02\report-102003.md` and acted on the low-risk actionable findings.
- Added Telegram tests for post-attempt visual photo delivery, `/cancel` while a slice is active, unauthorized callback rejection, and `/help` home-keyboard flow.
- Made `record_review_result(..., passed=False)` idempotent for already `BACK_TO_WORK` review cards, preventing duplicate back-to-work missions on retry.
- Made probability visual captions specific: bar chart vs 2x2 table, including highlighted cell intent.

Verification: focused TG/review/visual tests `49 passed`; backend suite `164 passed`; frontend build green; night-runner dry-run GREEN across all queued tasks.

Open tail: commit this hardening slice; next likely work is content-bank expansion, starting with probability variety and high-gap math/informatics topics.

---

## 2026-07-02 - Morning review of Qwen synthetic QA batch

Status: reviewed live report and fixed the one real gate issue.

- Latest report: `C:\tmp\egeMentor-qwen-runs\2026-07-02\report-095629.md`.
- GREEN: plumbing, visualization, slice/review, Telegram flow, bank/content coverage, release-smoke readiness.
- RED: analytics/digest acceptance, caused by `test_scores.py` using fixed `2026-07-01` as a "newer" score-event date while seed baseline uses `date.today()`.
- Fixed `test_scores.py` to use relative dates: future event moves `current_score`, older backfill does not regress it.
- Qwen findings to triage later: scalar/non-interval visuals are absent by scope; Telegram visual delivery path lacks a direct photo-send test; content gaps remain in probability variety, economics, informatics divisors/string topics.

Verification: analytics gate `25 passed`; backend suite `156 passed`; frontend build green; night-runner dry-run GREEN across all queued tasks.

Open tail: commit the score-test date fix; rerun live Qwen batch only if a fully GREEN report is needed.

---

## 2026-07-01 - Night queue expanded for read-only synthetic QA

Status: implemented and verified locally; ready for operator live run.

- Added `probability_table_neither_correct_answer` to the sandbox simulator: correct probability table answer now verifies `passed`, mission `done`, and post-attempt `probability` visual.
- Updated MCP/simulator tests and visualization report acceptance for the probability correct-answer happy path.
- Expanded `backend/scripts/night_queue.json` from one report into six read-only Qwen reports: visualization, slice/review lifecycle, Telegram learner flow, bank/content coverage, analytics/digest, and release-smoke readiness.
- All new Qwen tasks are `kind=report`; runner will mark them RED if Qwen edits any file.

Verification: simulator direct run OK with 7 cases; MCP/simulator tests `2 passed`; backend suite `156 passed`; frontend build green; `release_smoke.py` py_compile green; night-runner dry-run GREEN across all queued tasks.

Open tail: run live `backend\.venv312\Scripts\python.exe backend\scripts\night_runner.py`; morning-review raw reports before changing product code.

---

## 2026-07-01 - Synthetic tester coverage expanded for probability tables

Status: implemented and verified locally.

- Addressed the actionable finding from live Qwen report `report-163515.md`: sandbox flow covered probability bar chart only, not the 2x2-table renderer.
- `simulate_student_flow.py` now exercises all three source-ref-gated probability visuals: task-a bar chart, task-b `neither` 2x2 table, and task-c `only_a` 2x2 table.
- Updated sandbox/script tests to assert all three probability cases.
- Strengthened `T-report-visualization-surface` acceptance so a future Qwen GREEN requires the probability bar-chart and both 2x2-table cases.
- Deferred non-actionable/low-priority Qwen notes: PNG magic wording and repeated `matplotlib.use("Agg")`.

Verification: simulator direct run OK with 6 cases; focused simulator/probability tests `13 passed`; backend suite `156 passed`; frontend build green; night-runner dry-run GREEN.

Open tail: commit this follow-up, then run one live Qwen report against the expanded simulator.

---

## 2026-07-01 - Night-runner dry-run for local Qwen harness

Status: egeMentor harness port tested in dry-run; first live Qwen smoke found an isolation/config issue.

- Added egeMentor-local `backend/scripts/night_queue.json`: one acceptance-only plumbing task and one tiny Qwen sandbox-doc task.
- Hardened `backend/scripts/night_runner.py`: `files_allowed` is enforced, untracked files are counted, commit failure turns the task RED, and broken venvs without `pyvenv.cfg` are ignored.
- Run artifacts now go to ignored `.night-runs/` with per-run report names.
- Dry-run report: `T-night-plumbing-tests` GREEN with `backend/tests/test_figures.py` -> 13 passed; prompt-dependent sandbox task skipped by design.
- First live report `report-123842.md`: plumbing GREEN, sandbox RED because Qwen claimed the file was created but the isolated worktree had no changes.
- A stray `docs/NIGHT_RUNNER_SANDBOX.md` appeared in the main worktree; removed it and added a main-worktree contamination check around executor runs.
- Second live report `report-124445.md`: isolation was clean, but sandbox stayed RED because Qwen wrote `docs/NIGHT_RUNNER_SANDBOX.md` as UTF-16; queue acceptance now rejects UTF-16 BOM and requires exact two-line UTF-8 content.
- Third live report `report-125020.md`: Qwen wrote UTF-8 but creative markdown instead of exact content. Replaced the sandbox-doc task with `T-qwen-write-probe`: one file, one machine-token line, exact UTF-8 acceptance.
- Fourth live report `report-125401.md`: Qwen made no changes and claimed the prompt missed the token after a multiline instruction. The probe prompt is now one line, with the token inline, and runner reports a prompt preview for future debugging.
- Fifth live report `report-125830.md`: Qwen wrote the exact probe token, but into the main worktree; contamination guard blocked the run. Root cause: worktrees were nested under `.night-runs/` inside the repo, so OpenCode/file tools could resolve the parent checkout. Runner now uses external `C:\tmp\egeMentor-qwen-runs`.
- Sixth live report `report-132447.md`: external worktree isolation held, but Qwen wrote `\ufeff-NoNewlineQWEN_WRITE_PROBE_OK`. Queue now forbids PowerShell-style writers/`-NoNewline`, asks for Python `Path.write_text(..., encoding='utf-8')`, and rejects UTF-8 BOM explicitly.
- Seventh live report `report-134418.md`: GREEN. Qwen wrote exact UTF-8 probe file in the external worktree, acceptance passed, `test_figures.py` passed, and runner committed `bc08955` on `auto/2026-07-01-134418/T-qwen-write-probe`.

Verification: `backend\.venv312\Scripts\python.exe backend\scripts\night_runner.py --dry-run` -> GREEN; `backend\.venv312\Scripts\python.exe -m py_compile backend\scripts\night_runner.py` -> green; `git worktree list` / `git branch --list "auto/*"` show no leftovers.

Open tail: morning-review auto branch `auto/2026-07-01-134418/T-qwen-write-probe`, then replace the probe queue with a real but low-risk report/mechanical task.

---

## 2026-07-01 - Night queue switched from probe to report task

Status: implemented and dry-run verified.

- Morning-review of `auto/2026-07-01-134418/T-qwen-write-probe`: branch contains only test artifact `docs/QWEN_WRITE_PROBE.txt`; do not merge into product.
- `backend/scripts/night_runner.py` now supports `kind=report`: Qwen may produce raw-output reports, but any file change makes the task RED.
- `backend/scripts/night_queue.json` now contains `T-report-visualization-surface`, a read-only report over the current visualization implementation and tests.
- Added `backend/scripts/simulate_student_flow.py`: in-memory sandbox flow for interval overlay, unparseable interval answer, and probability visual; no prod DB and no Telegram.
- Added `backend/tests/test_student_simulation.py` so the simulator stays under the normal test suite.
- Updated `T-report-visualization-surface` to run the simulator and summarize visual kinds/source_refs/tests as raw-output report.

Verification: simulator OK; focused tests `28 passed`; backend suite `155 passed`; frontend build green; `night_runner.py --dry-run` -> GREEN.

Open tail: operator may run live report task manually; deploy/smoke of `api` + `bot` remains an operator/Codex action, not a Qwen task.

---

## 2026-07-01 - Sandbox MCP for synthetic tester

Status: implemented and verified locally; live Qwen report should wait for clean main checkout.

- Added `backend/app/adapters/mcp/sandbox_server.py` with `run_student_simulation()` only. It exposes no prod DB, no Telegram, and no write tools.
- Refactored `backend/scripts/simulate_student_flow.py` to provide `build_report()` / `run_json()` for script and MCP reuse.
- Added `backend/tests/test_mcp_sandbox.py`.
- Updated `T-report-visualization-surface` so Qwen acts as synthetic tester through sandbox MCP/function and reports raw flow observations.
- Hardened `night_runner.py`: live executor is BLOCKED when the main checkout is dirty, preventing Qwen from staging/touching the active work package.

Verification: sandbox MCP direct call OK; simulator OK; MCP/simulator tests `2 passed`; backend suite `156 passed`; frontend build green; night-runner dry-run GREEN.

Live Qwen report `report-161442.md`: GREEN. Qwen used the sandbox surface, changed no files, and gates passed (`test_figures.py`, sandbox MCP assertion, simulator script, probability/drill tests). Reported rough edges: unparseable interval answer lacks learner-facing reason, no passed-case visual scenario in simulator, sandbox covers only drill exact path, seed monkeypatch is fragile, and `probability` visual kind hides chart subtype.

Open tail: decide which Qwen findings to address first; stale auto worktrees from earlier calibration can be cleaned after review.

---

## 2026-07-01 - Synthetic tester finding fixed: passed case + unparseable caption

Status: implemented and verified locally.

- Added `interval_correct_answer` to `simulate_student_flow.py`: correct interval answer now verifies `passed`, mission `done`, and post-attempt `number_line` visual.
- Changed unparseable interval caption to explain why no orange overlay appears: the answer could not be recognized as an interval.
- Updated drill and simulator tests for the new behavior.

Verification: simulator direct run OK with 4 cases; focused tests `18 passed`; backend suite `156 passed`; frontend build green; night-runner dry-run GREEN.

Open tail: next sandbox expansion candidate is slice/review-card flow, not another renderer.

---

## 2026-07-01 - Probability visual spike integrated narrowly

Status: implemented and verified locally.

- Reviewed Qwen probability spike and integrated it only after interval parsing fails, using source_ref-gated `parse_probability_visual_spec`.
- `LearningService.drill_solution_visual` now returns `VisualAid(kind="probability")` for the three known probability seed tasks; unknown scalar tasks still return `None`.
- Telegram needs no separate change because it already sends any returned `VisualAid`.
- Added drill integration tests for known probability visual and unknown scalar fallback.

Verification: `backend\.venv312\Scripts\python.exe -m pytest backend\tests -q` -> 154 passed, 1 existing Starlette/httpx warning; `npm.cmd run build` in `frontend` -> green.

Open tail: deploy/observe whether probability visuals reduce `PROBABILITY_DOUBLE_COUNT`; do not generalize parser beyond known source_refs until more tasks justify it.

---

## 2026-07-01 - Docker deploy and release smoke after visuals

Status: deployed locally; live boundaries green.

- Rebuilt/recreated `bot`; compose also recreated `api` from the shared backend image. `web` and `postgres` stayed running.
- Ran `alembic upgrade head` in `api`; no pending migration output.
- Host `release_smoke.py` hit Windows/proxy access error on Telegram, so the equivalent smoke was run inside the `bot` container with `PUBLIC_API_BASE_URL=http://api:8001`.
- Container smoke GREEN: API health OK, migrations at `c0d1e2f3a4b5`, bot `getMe` OK, live Qwen short-answer judge OK.
- `api`, `bot`, and `web` all running with RestartCount=0.

Verification command: `docker compose exec -T -e PUBLIC_API_BASE_URL=http://api:8001 bot python scripts/release_smoke.py` -> GREEN.

Open tail: manual Telegram smoke remains: send `/today`, answer an interval drill if available, and verify post-attempt visual image/caption.

---

## 2026-06-30 - Weekly digest run and mentor-note draft

Status: digest read from DB; note drafted in chat, not published to TG.

- Period 2026-06-23..2026-06-30: 6 attempts, 2 active days, 4 passed attempts, pass rate 0.67.
- Diagnostics: 3 slices, all captured with details; probability moved from 1/3 to 5/5, powers/roots stayed 3/5.
- Errors: 6 recent, mostly `other` plus 2 old `probability_double_count`; latest powers/roots errors include the `7776`/`7.776` issue now fixed in code.
- Manual queue still has 2 old OДЗ items from 2026-06-17.

Verification: read-only service calls through current `LearningService.weekly_digest`, `list_manual_reviews`, `list_attempt_history`; no DB writes.

Open tail: operator should approve/edit the mentor-note text before publishing; then close the two old manual-review items if they are known correct/incorrect.

---

## 2026-06-30 - Judge reliability + weekly digest

Status: implemented and verified locally.

- Fixed exact-answer policy for grouped integer notation: `7.776` now matches key `7776`, while `0.667` still does not match `2/3` or `667`.
- Added `weekly_digest` in `LearningService` and MCP: attempts, active days, pass rate, touched topics, diagnostics capture status, errors, reviews, manual queue.
- Extended diagnostics rows with `captured` / `captured_items` derived from existing `details_json`; no migration or new tables.
- Added regression tests for grouped integers, decimal approximation guard, and digest data from existing slice/error events.

Verification: `backend\.venv312\Scripts\python.exe -m pytest backend\tests -q` -> 124 passed, 1 existing Starlette/httpx warning; `npm.cmd run build` in `frontend` -> green.

Open tail: use MCP `weekly_digest` for the next weekly mentor note; feedback compression and complex-practice track remain deferred until observed need.

---

## 2026-06-29 - Заметка по срезу 28.06 опубликована и доставлена Ульяне

Статус: на сайте + доставлена в TG (`delivered_at`=29.06 06:59)

- Анализ срезов: подтверждено, что 28.06 было два среза — вероятность **5/5 (33%→100%, закрыт приоритет №1 прошлой заметки)** и степени/корни 3/5. По истории попыток виден реальный путь обучения вероятности (двойной счёт → независимость → верная формула → 5/5).
- Нюанс честно: пошаговых решений вчерашних срезов в системе нет (пришли только баллы, последняя попытка в истории — 26.06). Степени 60% — по истории это потеря на ЗАПИСИ ответа (7776 → «7.776»), не на математике. Чтобы видеть ход — решать через бота `/slice`.
- Заметка `9f113dd1` через `publish_feedback` (сайт-лента) → доставлена в чат ученика прод-ботом (`_deliver_mentor_notes`). Детальная+мотивирующая: победа по вероятности, фикс записи степеней, фокус (проценты №11, ОДЗ формально), часть 2 как рост. Два вопроса ей: отметить новые темы (темп за ней) и в каком формате давать задачи посложнее (она просила) — отдельно «для себя» или вперемешку, по каким предметам.
- Открытый хвост: ждём ответы Ульяны (отметки тем + формат сложных задач); 2 старые попытки 17.06 (ответ x=5 — верный) всё ещё висят на ручной проверке — можно отметить зачтёнными по слову пользователя.

---

## 2026-06-29 - Банк информатики part-1: +28 задач (контентный хвост слабого предмета)

Статус: залито и одобрено в боевой БД через MCP; ответы проверены вычислением

- Возврат к контенту (по решению: визуализацию пока наблюдаем, не расширяем). 7 верифицируемых part-1 тем по +4: системы счисления, информационный объём, логика (таблицы истинности, было 1 → стало 5), делители (№25), подсчёт путей в графе, рекурсия (трассировка), кодирование Фано (префиксные коды).
- Ответы посчитаны кодом (`scratchpad/gen_inf2.py`): переводы СС, перебор таблиц истинности, делители, подсчёт путей DFS, прогон рекурсии, ceil(log2) для кодов — не с моих слов.
- Темы, требующие таблиц/картинок/файлов, **отложены** (нужен другой канал): анализ диаграмм (5017), БД (5024), Excel (5025), задание 17 по файлу (5035), теория игр (5027 — ответ-условие, не короткий).
- Итог банка (read-only): системы счисления/информ.объём/делители/пути/рекурсия/Фано = 4, логика = 5. Информатика всего **65** одобренных (старт сессии — 9), всего в банке **170**.

Проверка: `gen_inf2.py` — 28 OK; прямой SQL-count (enum хранится как `INFORMATICS`/`APPROVED`). Побочное: темы, бывшие `open` с пустым банком (системы счисления, делители, пути, рекурсия, Фано, информ.объём), теперь могут попадать в ежедневную очередь новых тем. Открытый хвост: визуальные информ-темы (диаграммы/БД/Excel/файл) — отдельным каналом; наблюдать визуализацию неравенств.

---

## 2026-06-29 - Визуализация: фигура решения в drill-разборе (post-attempt)

Статус: ЗАДЕПЛОЕНО (коммит `d90a826`), live-проверено в прод-контейнере

- Первая реальная post-attempt визуализация (урезанный план по ревью Codex): числовая прямая по интервальному ответу неравенства/ОДЗ, **показ только после попытки** (до — слил бы эталон). Парсер не уверен → фигуры нет (никогда не рисуем неверное).
- Слои (правка Codex): `domain/figures.py` = только чистый `parse_interval_answer` (leak-safe spec); рендер вынесен в `infrastructure/figures_render.py` (`render_number_line`, matplotlib, ленивый импорт). `LearningService.drill_solution_figure(mission_id)` отдаёт PNG post-attempt (эталон не покидает бэкенд сырым ключом — уходит готовая картинка). Бот `_on_answer`: после вердикта шлёт фото, если есть.
- Зависимость: matplotlib в extra `[bot]` (рисует только бот; образ общий — api её не импортит, рендер ленивый). Свап на drawsvg/resvg отклонён (та же Cairo-боль; matplotlib уже работает).
- Ресёрч (живой): движок не пишем. Web-интерактив — **JSXGraph** (MIT/LGPL), 3D-стерео — **GeoGebra** embed (внимание: non-commercial), Penrose/DeTikZify — мимо (тяжело/врёт геометрию). Наша новизна = тонкая ЕГЭ-склейка «ответ/условие→спека→фигура», OSS только после пользы в пилоте.
- Решения отложены осознанно: JSXGraph (нет доказанной потребности в интерактиве), `figure_json` на задаче (потечёт до попытки — фигура живёт в разборе/evidence), 3D.

Проверка: `pytest -q` 121 passed; ruff чист по новым файлам; live — `docker compose exec bot` отрисовал интервал (кириллица ок, PNG 8244B) и прод-бот доставил фото в родительский чат; bot RestartCount=0. Тесты: parse (скобки/объединения/неравенства/запятая, скаляр→None), render→PNG, склейка `drill_solution_figure` (interval→PNG, scalar→None). Открытый хвост: следующий рендерер (график параболы) по потребности; геометрия из условия может быть pre-attempt.

---

## Архив

| Неделя | Файл |
|--------|------|
| 2026-W26 | [SESSION_LOG_2026-W26.md](!DOC/archive/SESSION_LOG_2026-W26.md) |
| 2026-W25 | [SESSION_LOG_2026-W25.md](!DOC/archive/SESSION_LOG_2026-W25.md) |
