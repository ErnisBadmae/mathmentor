# Active Task

Last updated: 2026-07-13

## Product direction review (2026-07-13)

The bounded L2a implementation in
`!DOC/operations/CODEX_L2_CONFIRMED_ERROR_TAG.md` is accepted locally after senior review.
It is not deployed. Before L3: commit the verified revision, deliberately deploy/migrate,
manually confirm real `other` slice errors, and inspect the resulting journal. Do not wire
interventions merely because the storage path now exists.

- **Positioning:** do not compete as a generic trainer, tutor CRM, or AI tutor. The
  product bet is a vertical EGE mentor operating system: verified evidence -> explicit
  intervention -> scheduled follow-up -> exam-like score outcome.
- **Moat:** dashboards, task banks, LLM feedback, and score forecasts are table stakes.
  The defensible asset is a trustworthy longitudinal intervention-to-outcome ledger plus
  a workflow that lets a tutor supervise more students without losing review quality.
- **External pilot gate:** do not invite unrelated students into the current runtime yet.
  The web app resolves `/students/current` to the first profile and uses one shared API
  token, so learner data is not isolated. Recruit tutor design partners/interviews now;
  give access to 2-3 external students only after a minimal identity/assignment boundary.
- **Measurement:** while the N=1 learner is ill, do not treat a timed cut as a baseline.
  Use the pause to dry-run mentor proactivity on existing evidence. Start with transparent
  trajectory status and confidence/insufficient-data labels; no ML score prediction before
  several comparable timed score events exist.
- **Visualization:** treat visuals as named interventions, not a content feature or moat.
  Prefer JSXGraph for reusable 2D geometry. GeoGebra 3D requires a commercial agreement
  for a paid product, so do not make it a commercial dependency without licensing review.
- **Next product slice:** close one observable loop end to end: repeated error/risk signal
  -> proposed action -> mentor approval -> mission delivery -> +7 review -> next timed
  score event. Record mentor time and intervention outcome alongside learner evidence.

### Agreed delta (Claude + Codex, 2026-07-13)

- **Primary goal is explicit:** daughter >=85 on profile math by EGE-2027. Effort split:
  80-90% learner outcome, 10-20% tutor interviews / commercial hypothesis logging,
  0% payments/SaaS/multi-tenancy. Every feature passes the filter "does it add points
  or prove the loop works".
- **Mock date reserved: 2026-07-26** (first timed baseline, conditional on recovery).
  If moved, it may only be moved by fixing a new concrete date, never left open.
- **Now it is a wedge, not a moat:** the pilot proves the workflow (tutor/operator runs
  the loop and saves time), not the intervention-outcome dataset. Data moat is a
  multi-year story.
- **Mentor minutes are measured explicitly** via a manual journal (student | date | task |
  minutes | decision). DB timestamps are NOT a valid proxy for operator time.
- **Error category is never auto-derived from task type.** Answer-only errors stay
  `other/unclassified`; mentor gets a fast manual tag; auto-category allowed only when
  reasoning/code is present; intervention selector consumes confirmed actionable
  categories only. This is the prerequisite slice before wiring the proactive loop
  (`other` currently dominates top_errors).
- **External pilot isolation = one Docker stack per student** (own DB, token, compose
  project, ports, TG bot). No identity/multi-tenant code. Needs only port/env
  parametrization of docker-compose. Tutor complaints about tab-switching become the
  evidence for building an aggregated cockpit later.
- **Sequencing guard:** interviews (8-12, three segments: strong solo tutors, small
  teams, parent-operators) start now — script and outreach templates:
  `!DOC/operations/TUTOR_INTERVIEWS.md`; design-partner onboarding only AFTER the first
  closed intervention loop and a visible N=1 delta — concierge pilot is not a 10-20%
  effort item.
- **Commercial gating metric is student engagement, not tutor price sensitivity:**
  the product only creates value if students actually solve between lessons; weekly
  active days (already a first-class KPI) measures exactly this on N=1 today.
  Interview probe: "how many of your students do homework between lessons unprompted?"
- **Content is a hidden COGS at scale;** flip it: tutor brings own tasks via existing
  `add_task -> approve_task` pipeline = tutor lock-in. Interview probe: "where do your
  tasks come from?"
- **Fallback buyer hypothesis:** parent-operator (B2C) if tutors do not convert; product
  already fits it. Both models gate on minors' personal-data compliance before any
  external launch.
- **Market frame:** TAM ~8k productive profile-math tutors (rough), 300 paying = ~4%
  penetration (reachable), 1000 = ~12% (ambitious). Plan as a small profitable vertical
  SaaS at the lower bound, not the 3M MRR case.
- **Bank refill is in-scope now** (it is learner-outcome work, not commercial work):
  July math topics (экономика/стерео/планиметрия/параметр) and interval topics
  (Неравенства/ОДЗ) are still thin; `shortage` in `build_daily_queue` is the trigger.
  Answers must stay code-verified (anti-poison scripts), same as the June refill.
- **Channel split stands (decided earlier, unchanged):** TG = учебный канал ученика
  (daily part-1 drill, повторы, срезы, /ready); сайт = part 2, теория/визуализации и
  операторская/родительская витрина. New slices map onto this split; no re-decision needed.

## Platform-devkit pilot (Phase C, 2026-07-13)

- **Status:** completed locally; repo-level docs tooling now uses
  `platform-devkit` through a compatibility shim.
- **Done:** `platform-devkit` editable-installed into root `venv`;
  `scripts/docs_maintenance.py` delegates to `platform_devkit`.
- **Local overrides:** `.claude/rules/simplicity.md` is not force-synced because
  egeMentor adds a project-specific Russian-dialogue rule.
- **Verified:** shim `--version` works; `platform-docs audit` runs with only
  pre-existing doc-size/session-log warnings; `platform-encoding-guard --check`
  clean; backend pytest 210 passed; ruff clean on the touched test file.
- **Next:** decide whether egeMentor should add a real `.pre-commit-config.yaml`
  later; do not force-sync local `.claude/rules/simplicity.md` unless the shared
  preset learns project-specific overrides.

> Кросс-проектная стратегия (verifiable-AI рамка, роли Claude/Codex/Qwen, ege-трек
> proven-delta в общей картине): канонический док — `expert-agent/!DOC/STRATEGY.md`.

## Current Snapshot (2026-07-10, deterministic planner MVP: prereq-gate + explanation)

- Реализовано (Claude): детерминированный learning planner MVP поверх существующего
  `build_daily_queue` — БЕЗ Дейкстры, weighted-frontier, LearningPlanner-класса, goal-входа и
  миграций. Оценка идеи Кодекса: Дейкстра — неверный инструмент (задача не shortest-path, а
  prerequisite-closure); weighted-scoring тоже преждевременен — это по сути замороженная
  error-intervention логика, тюнить не на чем (N=1). Ценные 20% (ворота + объяснение) едут дёшево,
  weighted-80% отложено до weekly-review данных и подключится через готовый `select_intervention_queue`.
- Что добавлено (~40 строк чистого domain, без БД):
  - `domain/prerequisites.py`: статичная карта `PREREQUISITES` (4 defensible-ребра внутри Части 1 на
    реальных названиях тем) + чистый предикат `prerequisites_met`.
  - `domain/policies.py`: чистый презентер `describe_pick(reason)` — строка «почему» для оператора/агента.
  - `application/use_cases.py` `build_daily_queue`: посчитан `passed_titles` (темы с `solved_count>0`),
    добавлен один gate-предикат в фильтр новых тем, к каждому пику прицеплены структурный `reason` (данные)
    и строка `why`. `select_daily_queue` (инвариантная функция) НЕ тронут — `reason` едет сквозь неё как
    лишний ключ dict.
- «Проблема 3 потребителей» решена архитектурно: domain отдаёт ОДИН структурный `reason` (узкий
  интерфейс), сверху N тонких форматтеров. В MVP реализован только один (`describe_pick`, оператор/агент).
  Детский и родительский тексты — будущие форматтеры над тем же dict; domain при их добавлении не меняется.
  Детский текст обязан вести «от достижения, а не от дефицита» (правило снижения тревоги от 25.06).
  LLM ни в одном форматтере: объяснение = честный след выбора (ложится в verifiable-AI линию).
- Инварианты целы: due→back_to_work→new, open-count в лимит, идемпотентный `source_ref`,
  manual-review темы вне авто-дрилла, phase/ready_mode, LLM не выбирает тему. Ворота применяются и в
  ready-mode (общий фильтр).
- Verification: targeted pytest `17 passed` (13 старых + 4 новых), full backend `210 passed`
  (было 206, +4), ruff по затронутым файлам с `--ignore E501` clean, import-linter `2 kept, 0 broken`
  («domain is pure» держится). Живое наблюдение на реальном seed: пара «Вычисления: логарифмы…» (база) →
  «Простейшие уравнения…» (зависимая) — до закрытия базы зависимая в очередь не попадает; после сдачи
  базы появляется, `why` называет закрытый пререквизит. НЕ задеплоено (deploy — отдельный шаг).
- Хвост: (1) решить, писать ли ADR и где (каталога `!DOC/adr/` пока нет — заводить схему не стал под
  Simplicity First); (2) когда фича подтвердится — детский форматтер `why` в утренний пуш TG и
  родительский в mentor-note/дашборд; (3) прокинуть `why` в `mentor_brief`/операторский дашборд как
  первый видимый потребитель; (4) при желании расширить `PREREQUISITES` за пределы 4 рёбер.

## Current Snapshot (2026-07-09, MCP context + no-domain publishing)

- Реализовано (Codex): компактный первый слой для MCP — `mentor_brief(student_id, days=14)`.
  Это не замена истории: сырые попытки, ошибки, ревью и программа остаются в Postgres и доступны
  через drill-down tools (`attempt_history`, `program_progress`, `error_journal`, `reviews`,
  `manual_reviews`, `topic_theory`). В `mentor_brief` намеренно не попадают полные `answer_text`
  и `code_text`, чтобы не раздувать контекст агента при первом чтении.
- Бизнес-логика оставлена простой: без pgvector/Qdrant/нового слоя памяти. Векторный поиск имеет смысл
  добавить позже только для задачи "найди похожие прошлые ошибки/задачи"; для текущей mentor-сводки
  достаточно детерминированной агрегации из Postgres.
- MCP: добавлен tool `mentor_brief`; после перезапуска MCP-клиента он должен стать первым read-tool
  перед глубокими запросами. Ручной запуск `python -m app.adapters.mcp.server` в отдельном терминале
  сам по себе не подключает Codex/Claude — stdio-сервер должен быть запущен MCP-клиентом.
- Публикация сайта: добавлен runbook `!DOC/operations/PUBLISHING_SITE.md`. Домен покупать не обязательно.
  Рекомендуемый no-domain путь для семьи — Tailscale Serve (`https://<machine>.<tailnet>.ts.net`);
  временный публичный путь — Cloudflare Quick Tunnel; стабильный публичный путь позже — Cloudflare
  Tunnel + Access и домен.
- Frontend/public mode: добавлен `VITE_OPERATOR_MODE_AVAILABLE`. При `false` операторский toggle
  скрывается, а `/operator` не показывает операторскую поверхность. `docker-compose.yml` и
  `frontend/Dockerfile` прокидывают этот build arg; `.env.example` документирует флаг и
  `PUBLIC_FRONTEND_BASE_URL`.
- Публикация начата live (2026-07-09): Cloudflare Quick Tunnel через Docker выдал
  `trycloudflare.com` URL, но не смог установить соединение — в сети заблокирован outbound к
  Cloudflare Tunnel edge (`7844`, QUIC/TCP). Установлен Tailscale `1.98.8`; host уже авторизован
  в tailnet как `100.113.226.52`. Tailscale Serve config из CLI зависает в этом Windows-окружении,
  поэтому текущий рабочий no-domain URL: `http://100.113.226.52:8088`.
- Runtime update: локальный `.env` переключён на
  `PUBLIC_FRONTEND_BASE_URL=http://100.113.226.52:8088` и `VITE_OPERATOR_MODE_AVAILABLE=false`;
  `web` пересобран, `bot` перезапущен и видит эти env values. Доступность проверена:
  `curl http://100.113.226.52:8088/api/health` → `{"status":"healthy"}`; release smoke GREEN.
- Verification: targeted pytest `26 passed`; full backend pytest `206 passed`; frontend
  `npm.cmd run build` OK; ruff по затронутым файлам с `--ignore E501` clean. Широкий ruff всё ещё
  падает на 4 старые E501 в `mcp/server.py` и `use_cases.py`, не связанные с этим слайсом.
- Хвост: устройство ученицы должно быть в том же Tailscale tailnet; тогда ссылка
  `http://100.113.226.52:8088` откроется. Остановить вручную запущенный MCP terminal (`Ctrl+C`) и
  перезапустить MCP-клиент/Codex/Claude, чтобы новый tool contract загрузился.
- Добавлена инструкция для ученицы: `!DOC/operations/STUDENT_SITE_ACCESS.md` — куда нажимать в
  Tailscale, какие ссылки открывать (`/program`, `/daily`, `/slice`, `/review`, визуализация по
  векторам) и что написать родителю, если сайт не открывается.
- Security hardening после публикации: `docker-compose.yml` теперь биндует `api` и `postgres`
  только на `127.0.0.1`; внешней/tailnet-точкой остаётся только `web` на `8088`. Проверено:
  `curl http://100.113.226.52:8088/api/health` OK, release smoke GREEN.

## Current Snapshot (2026-07-09, visual feedback hardening)

- Реализовано (Codex): минимальный hardening по реальной обратной связи ученицы “визуализация не открывается”
  и по текущему дриллу “Векторы — скалярное произведение”.
- Telegram: прямой URL на `/theory/<topic_id>` теперь отправляется только если `PUBLIC_FRONTEND_BASE_URL`
  выглядит публичным. Для `localhost`, `.local`, loopback/link-local/private IP (`192.168.x.x`) бот пишет
  коротко: `Визуализация есть на сайте: «Программа» → эта тема.` Это убирает битые LAN-ссылки у ученицы.
- Telegram UX: `_task_text` больше не добавляет общий хвост “кратко распиши ход...” поверх уже заданных
  `instructions`, поэтому дриллы формата “отправь ответ числом” не получают противоречивую вторую инструкцию.
- Content/frontend: в seed добавлена approved concept card `Скалярное произведение в координатах`
  (`vector_dot_product`) для темы `Векторы`; frontend `/theory/:topicId` получил простой SVG-рендер
  формулы `a·b = x1·x2 + y1·y2`. Сортировка карточек теперь по title, поэтому scalar-product карточка
  идёт первой, без новой skill-tag модели.
- Verification: targeted pytest `28 passed`; full backend pytest `205 passed`; frontend `npm.cmd run build` OK;
  targeted ruff по `bot.py`/bot+theory tests clean; release smoke GREEN.
- ВЫКАЧЕНО live (2026-07-09): `docker compose up -d --build api`, `alembic upgrade head`,
  `python scripts/seed.py`, `docker compose up -d --build bot web`. Live API по векторам отдаёт две карточки
  (`vector_dot_product`, `vector_2d`), live bot-text не содержит `192.168`, web `/theory/...5012` отдаёт 200.
- Хвост: reconnect ege-MCP. Текущий MCP-процесс всё ещё держит старый контракт: `topic_theory` tool не виден,
  а `program_progress` не отдаёт `visual_ready`, несмотря на обновлённые live API/bot/web. После reconnect проверить
  `program_progress`/`topic_theory`.

## Current Snapshot (2026-07-08, visual concept cards v1)

- Реализовано (Codex): безопасные визуальные concept cards до попытки, отдельно от `/ready`
  (`theory_ready` = ученик отметил теорию изученной; `visual_ready` = по теме есть approved
  визуальная карточка). Содержимое не содержит ключей ответов и не является task-specific
  разбором.
- Backend: новая таблица `theory_cards` (alembic `e6f7a8b9c0d1`), репозиторий/порт
  `theory_cards`, `LearningService.list_topic_theory`, API `GET /topics/{topic_id}/theory`,
  `visual_ready` в `program_progress`, mission payload и slice draw payload. MCP получил read-tool
  `topic_theory(topic_id)`; `program_progress` автоматически отдаёт `visual_ready`.
- Content seed: approved карточки для двух тем из реального запроса ученицы:
  `Векторы` (`vector_2d`) и `Производная: геометрический смысл` (`derivative_tangent`).
- Telegram/site: `/today` и `/slice` добавляют ссылку `PUBLIC_FRONTEND_BASE_URL/theory/<topic_id>`
  при `visual_ready`; сайт получил маршрут `/theory/:topicId` с локальными SVG-рендерами,
  ссылки из «Программы», «Сегодня» и «Среза».
- Verification: backend pytest `204 passed`; frontend `npm.cmd run build` OK; Docker web build OK;
  release smoke GREEN; ruff clean на новом `backend/tests/test_theory_cards.py`. Широкий ruff по
  старым изменённым backend-файлам всё ещё шумит существующими B008/E501 в routes/seed/use_cases,
  не связанными с этим слайсом.
- ВЫКАЧЕНО live (2026-07-08): `docker compose up -d --build api`, `alembic upgrade head`
  (`e6f7a8b9c0d1`), `python scripts/seed.py`, затем `docker compose up -d --build bot web`.
  Контейнеры running/healthy; `/theory/00000000-0000-0000-0000-000000005012` отдаёт 200;
  live service check показал `visual_ready=True` для `Векторы` и `Производная: геометрический смысл`.
- Хвост: reconnect ege-MCP. Текущий MCP-процесс в этой сессии держит старый код: `topic_theory`
  tool не виден, а `program_progress` ещё не отдаёт `visual_ready`. После reconnect проверить MCP
  `program_progress` + `topic_theory`.

## Current Snapshot (2026-07-07, /ready: теория изучена → приоритет очереди)

- Реализовано (Claude): отметка ученика «/ready — теорию изучила, готова решать» как
  сигнал приоритета сборщика дня. Выведено из реального случая: очередь пуста, ребёнок
  просит векторы/движение (июньская фаза — сборщик их не видел), а июльская фаза могла
  выдать стерео/параметр против её просьбы.
- Механика: `topics.theory_ready_at` (миграция `d5a6b7c8e9f0`); правило в
  `build_daily_queue` — есть хоть одна отметка → новые дриллы ТОЛЬКО по отмеченным темам
  любой начавшейся фазы, неотмеченные темы текущей фазы придерживаются; нет отметок —
  прежнее поведение. Отметка — сигнал приоритета, НЕ evidence (закрытие тем не меняется).
- TG: команда `/ready` + кнопка в меню («📖 Готова к новым темам»), inline-toggle тем,
  manual-path темы (стерео/параметр/№13–18) в кандидаты не попадают. `theory_ready`
  прокинут в `program_progress` (API/MCP) для бейджа на «Программе».
- Verification: backend pytest `198 passed`; ruff по затронутым файлам чист.
- ВЫКАЧЕНО live (2026-07-08): `alembic upgrade head` (`d5a6b7c8e9f0`, theory_ready_at)
  применён к БД; `docker compose up -d --build api bot web`. api/bot `healthy`, `/program`
  отдаёт `theory_ready`, runtime-smoke GREEN.
- Три UI-задачи (были «Кодексу») СДЕЛАНЫ Claude 2026-07-08 (pytest 198, tsc/ruff чист):
  1. TG пустая очередь → «На сегодня всё сделано ✅ Новая порция — завтра утром» (тест обновлён).
  2. TG `/progress`: карта фазы — «📚 Фаза «label» (дд.мм–дд.мм)», «Закрыто X из Y · в работе
     · на повторении», «Дальше: …» (до 3 открытых тем).
  3. Сайт «Программа»: бейдж «📖 теория изучена»; `theory_ready` добавлен в `ProgramTopicOut`
     (pydantic его резал), TS-тип и CSS `badge--ready`.
- Хвост: переподключить ege-MCP (держит код до `telegram_send`), затем live-проверить
  MCP `publish_feedback`→ТГ, `/send` из родительского чата, `/ready`-тоггл + бейдж.

## Current Snapshot (2026-07-04, AI-judge calibration baseline)

- New instrument: `backend/scripts/calibrate_ai_judge.py` (+5 tests) — offline-replay
  калибровка `LlmShortAnswerJudge` против детерминированного exact-авторитета по протоколу
  expert-agent ADR-013 (kappa-математика скопирована оттуда, VERSION 1.0). Exit non-zero
  при judge-failure-rate > 10% → готов как weekly night-runner task (no-prompt acceptance).
- Baseline (25 unique triples / 27 attempts, judge failures 0):
  - raw judge vs raw exact: agreement 0.36, kappa 0.04 — низкий ПО ДИЗАЙНУ: почти все
    ответы формата «покажи ход», raw exact совпал лишь на 1/25; судья и существует для
    этого разрыва.
  - guardrail-декомпозиция: из 16 judge-«спасений» **14 заземлены** extracted-ответом
    (прод принял бы законно), **2 opinion-only — прод отверг бы** (fail-closed held);
    false negatives 0 (судья не бракует верное).
  - продуктовые находки: (a) unit-синонимы «768 кб» vs «768 Кбайт» — exact промахивается
    на верном ответе → кандидат в `normalize_answer`; (b) code-задачи с описательным
    эталоном структурно не подходят short-answer политике — зона MANUAL_GATE, не exact.
- Next:
  1. Human_verdict по 14 grounded-спасениям в `backend/data/ai_judge_disagreements.jsonl`
     (~10 мин, поле `human_verdict: judge_right | exact_right` прямо в файле).
  2. Добавить `calibrate_ai_judge.py` в weekly night queue (перезапуск по мере роста данных).
  3. Малый slice: unit-синонимы (кб/Кбайт/КБ) в `normalize_answer` + тесты (Codex/Qwen класс).
- Codex follow-up 2026-07-04:
  - `backend/scripts/night_runner.py` синхронизирован с каноном expert-agent v1.1:
    VERSION=1.1, `.env` копируется из корня репо в worktree, acceptance/executor пишут
    full-log в `logs/<task>/`, отчёт показывает хвост `LOG_TAIL_CHARS=3000`; ege-пути и
    `C:\tmp\egeMentor-qwen-runs` сохранены.
  - `normalize_answer` теперь сводит синонимы единиц информации: `кб|кбайт|kb`,
    `мб|мбайт|mb`, `гб|гбайт|gb`; одиночная `б` не нормализуется.
  - Weekly queue получила no-prompt gate `T-calibrate-ai-judge` с acceptance
    `backend/scripts/calibrate_ai_judge.py --max-failure-rate 0.1` и `files_allowed`
    только для `data/ai_judge_disagreements.jsonl`.
  - Проверка baseline rerun: кодовый exact-case `answer_is_correct("768 кб", "768 Кбайт")`
    исправлен тестами, но live calibration rerun 2026-07-04 не дал валидной дельты:
    LLM endpoint из `.env` (`http://192.168.0.18:8000/v1`) недоступен, judge returned
    None 25/25 (`failure_rate=1.0`, rc=1). Дополнительно текущая replay-тройка в БД
    содержит полный текст решения, начинающийся с `768 кб, ...`, поэтому raw exact
    остаётся `False` без отдельного извлечения финального ответа.
  - Import-linter package B 2026-07-05: backend получил два layering-контракта в
    `backend/pyproject.toml` (`app.domain` не импортирует `app.infrastructure /
    app.adapters / app.application`; `app.application` не импортирует `app.adapters`),
    `import-linter` добавлен в `dev`, weekly queue получила `T-lint-imports`.
    Под эти контракты кодовых нарушений нет; `importlinter`/`grimp` пришлось посадить в
    локальную `.venv312` копированием из соседней venv, потому что `pip install -e .[dev]`
    упёрся в сетевой/proxy deny.

- Codex follow-up 2026-07-06:
  - Closed Qwen backend findings from the night run: part-2 #13 seed now uses the math topic
    `Задача 13: тригонометрическое уравнение`, and part-2 manual-gate missions take `topic_id`
    from their linked task to prevent task/mission drift.
  - Manual-gate lifecycle is covered through submit -> manual-review queue -> manual PASSED ->
    mission DONE -> +7/+30 reviews; resolved manual-review evidence no longer stays visible in
    the pending queue.
  - Added pure `select_intervention_queue(...)` with repeated actionable category count >=2 and
    `none`/`other` ignored. It is intentionally not wired while the deterministic intervention
    rule remains frozen.
  - Weekly `T-lint-imports` command now invokes `importlinter.cli`.
- Ops follow-up 2026-07-07:
  - Telegram bot polling recovered by restarting only `bot` after repeated proxy/update failures.
    Direct Telegram access from the container still times out, so the configured proxy remains required.
    Fresh logs stayed clean after restart and `getMe` via proxy returned OK.
  - Daily-mission recovery applied live through the MCP server: due review cards through
    2026-07-07 were marked passed, 5 stale open `daily:` missions were closed with
    `operator-recovery` evidence, and 4 accidental part-2 daily drills were retired as
    `skipped`.
  - MCP now has narrow operator tools for this class of recovery:
    `operator_close_daily_missions` and `operator_skip_daily_missions`. `build_daily_queue`
    now excludes current part-2/manual-review topics from auto daily drills.
  - Regression guard added: bot now has an in-process polling-failure watchdog, a Docker healthcheck
    for Telegram `getMe`, and a host-side `telegram_bot_runtime_smoke.py` for service/log/getMe checks.
    Live `api`/`bot` were rebuilt/recreated; Compose reports `bot` as `healthy`, release smoke is GREEN,
    and runtime smoke is GREEN.
  - Local service stack check: `docker compose up -d` confirmed `postgres`, `api`, `web`, and `bot`
    running; API health returned `healthy`, Docker web answered on 8088, and Vite dev frontend is
    running through scheduled task `egeMentorFrontendDev` at 5174.
  - Live Telegram slice check via MCP: the bot did process the learner's percent-slice answer and
    returned a verdict, but in-progress slice answers are held in the bot's `_srez` session and only
    persist via `record_slice` after the final task. MCP should show the completed slice in
    `diagnostics` / `weekly_digest`, not as individual `attempt_history` rows.

- Notes delivery unified 2026-07-07:
  - New `app/infrastructure/telegram_send.py` `deliver_pending_notes(...)` is the single delivery
    function (sync urllib+proxy, no aiogram, self-contained). Wired into MCP `publish_feedback`
    (instant, hard-fail), API `publish_mentor_note` (web operator form, HTTP 502 on delivery fail),
    and the bot morning push (now calls it via `asyncio.to_thread`; old aiogram
    `_deliver_mentor_notes`/`_notify_parent`/`_split_for_telegram` removed).
  - Parent manual TG channel: bot command `/send <text>` (parent chat only) publishes + delivers.
  - Frontend token gate removed (`App.tsx`) and `.env` `API_SHARED_TOKEN` blanked (temporary).
  - Verify: pytest 191 passed. NOT live yet — needs `docker compose up -d --build api bot` and an
    MCP server reconnect (running MCP holds pre-change code).
- Goal: execute the proven-delta strategy with verified small steps: monthly timed score events, weekly error-to-intervention review, part-2 manual-gated evidence, targeted content depth, and Qwen only as a bounded read-only/mechanical executor.
- Status: latest completed live nightly batch `C:\tmp\egeMentor-qwen-runs\2026-07-03\report-093450.md` is 4/4 GREEN. The part-2 text-only manual-gate slice is committed as `4294d09`; the MANUAL_GATE real-reviewer regression and sandbox simulator case are committed as `34e1f75` and verified by live Qwen. Retention KPI v1 is implemented locally: dashboard exposes weekly active days and a Wednesday risk alert.
- Current operating rules:
  - keep `current_score` tied to timed score events, not daily attempts;
  - start error intervention manually via `error_journal` + `publish_feedback`;
  - keep deterministic repeated-error intervention frozen until 2-3 weeks of observed weekly-review data;
  - keep Qwen as bounded read-only/mechanical QA: nightly synthetic QA + post-change reports, no content, no write-path, no senior MCP.
  - retention is a first-class operating signal: by Wednesday, fewer than 3 active days is an operator-facing dashboard risk.
- Triage of nightly batch 093450:
  - accepted: sandbox `manual_gate_text_solution`, sandbox MCP contract, error-intervention readiness, and part-2 post-change checks are GREEN;
  - no urgent code: suggested sandbox expansions (attempt-mode comparison, threshold close, error-category journal propagation) are useful later but not blockers;
  - future blocker before deterministic intervention: slice/srez errors currently land as `other`, and `other` already dominates `top_errors` (6); add a small Codex slice to categorize srez errors before using `top_error_category` for routing;
  - note for later operator work: when mission-create/edit UX grows part-2 support, guard against accidentally creating `part2:text:*` missions with `ATTEMPT_FIRST`;
  - skip/low: `publish_feedback` weekly dedup test, Part2Page empty-state/filter test, task 4071 wording check before first real part-2 session.
- Next:
  1. Commit the retention KPI v1 slice.
  2. Schedule/record the first July timed mini-mock as the score baseline.
  3. Start the weekly mentor review from `error_journal` and recent attempts.
  4. Deploy/reseed live data if the new #13/#15 manual-gate missions should affect the learner now.

## Current Snapshot (2026-07-03)

- Goal: execute the proven-delta strategy with verified small steps: monthly timed score events, weekly error-to-intervention review, part-2 manual-gated evidence, targeted content depth, and Qwen only as a bounded read-only/mechanical executor.
- Status: strategy accepted; canonical plan is aligned from the old LAN/scaffold next-plan to the three-horizon proven-delta plan. Latest completed live nightly batch `C:\tmp\egeMentor-qwen-runs\2026-07-02\report-235647.md` is 4/4 GREEN (plumbing, sandbox contract, error-intervention readiness, part-2 post-change QA). Score-spine visibility is implemented and committed in `edcaa70`. Qwen follow-up gate fix is committed in `9c4ad0b`. Night queue is now split: nightly core stays compact; broad surface reports moved to `backend/scripts/night_queue_weekly.json`. The first part-2 text-only manual-gate slice for #13/#15 is committed as `4294d09`; the follow-up MANUAL_GATE real-reviewer regression and sandbox simulator case are implemented locally.
- Current operating rules:
  - do not scale infrastructure or multi-student support until an N=1 delta is visible;
  - keep `current_score` tied to score events from timed mocks, not daily attempts;
  - start error intervention manually via `error_journal` + `publish_feedback`, then add a simple deterministic queue rule only after observed repetition;
  - use Qwen through `backend/scripts/night_runner.py` for read-only reports, smoke checks, and mechanical edits with machine gates.
- Current Qwen report triage:
  - done: timed mock score history is visible (`list_score_events` + dashboard trend + weekly digest score block);
  - done from latest report: sandbox MCP boundary is safe; no senior mentor MCP write tools in Qwen prompts;
  - fixed after latest report: score-spine Qwen acceptance no longer depends on missing frontend `node_modules`; added regression coverage that `topic_check` score events do not move `current_score`;
  - queue freshness finding implemented: nightly keeps plumbing + sandbox/error-intervention/part2; visualization, slice/review, Telegram, bank coverage, analytics, release-smoke, and score-spine postchange are weekly/change-triggered;
  - keep Qwen out of senior mentor MCP and real student-state write tools; sandbox MCP only exposes deterministic synthetic simulation;
  - process first: start weekly `error_journal` review and publish feedback manually before coding intervention routing;
  - part 2 first slice implemented: text-only submitted solution with manual verdict gate for #13/#15 before photo/OCR UX;
  - part 2 follow-up implemented: MANUAL_GATE is regression-tested through `RuleBasedReviewer`, and sandbox `run_student_simulation()` includes `manual_gate_text_solution`;
  - low-priority test gaps: bar-chart correct-answer simulator case, double-PASS review idempotency, slice/daily duplicate guard, extra Telegram callback/media/streak tests.
- Triage of nightly batch 235647 (2026-07-03):
  - done locally: MANUAL_GATE fail-closed regression through the real reviewer path + sandbox simulator `manual_gate` case so nightly QA guards the part-2 invariant;
  - design constraint for the frozen intervention rule: `top_error_category` must require a minimum count (>=2) before triggering anything;
  - low/skip: `publish_feedback` weekly dedup test (manual gate mitigates), Part2Page empty-state UX and filter test, task 4071 statement wording — operator checks wording at the first real part-2 session.
- Next:
  1. Commit the MANUAL_GATE reviewer-path + sandbox simulator follow-up.
  2. Deploy/reseed live data if the new #13/#15 manual-gate missions should affect the learner now.
  3. Schedule/record the first July timed mini-mock as the score baseline.
  4. Start the weekly mentor review from `error_journal` and recent attempts.
  5. Keep deterministic repeated-error intervention frozen until 2-3 weeks of observed weekly-review data.

## Current Snapshot (2026-07-01)

- Goal: add a safe local-Qwen execution harness for small, falsifiable overnight tasks.
- Status: Qwen harness is calibrated and documented; probability visuals are integrated; sandbox MCP/student-flow simulator covers interval visuals, probability bar chart, probability 2x2-table wrong answers, and probability 2x2-table correct-answer happy path for read-only Qwen reports.
- Done:
  - ported the night-runner queue shape to egeMentor-local paths;
  - added `files_allowed` enforcement before acceptance/commit;
  - fixed venv autodetect to ignore broken venvs without `pyvenv.cfg`;
  - moved run artifacts to external `C:\tmp\egeMentor-qwen-runs` and made reports per-run.
  - added a main-worktree contamination check around live executor runs.
- Current Qwen queue tasks: six read-only Qwen reports are queued after plumbing: visualization surface, slice/review lifecycle, Telegram learner flow, bank/content coverage, analytics/digest, and release-smoke readiness. Any file change by Qwen makes a report task RED.
- Latest live report: `C:\tmp\egeMentor-qwen-runs\2026-07-02\report-102003.md`: full Qwen read-only QA batch GREEN.
- Done from Qwen findings: added TG tests for post-attempt visual photo delivery, `/cancel` during active slice, unauthorized callbacks, and `/help`; made failed review result idempotent so repeated FAIL does not create duplicate back-to-work missions; made probability visual captions specific for bar-chart vs 2x2-table cases; expanded the probability bank from 3 to 10 approved tasks.
- Verification: probability bank focused tests `9 passed`; backend pytest `165 passed`; frontend `npm.cmd run build` green; `night_runner.py --dry-run` GREEN across all queued tasks.
- Next: commit probability bank expansion. Then either deploy/reseed live DB or continue content expansion with math foundations / informatics gaps.

## Current Snapshot (2026-06-30)

- Goal: improve pilot service reliability and analytics after the product/pedagogy review.
- Status: implemented the first two high-leverage items: safer exact-answer grading and a read-only weekly digest.
- Done:
  - grouped integer answers such as `7.776` are accepted for integer keys like `7776`;
  - decimal approximations such as `0.667` still do not override exact numeric mismatch;
  - diagnostics expose whether solution details were captured;
  - `LearningService.weekly_digest()` and MCP `weekly_digest` summarize recent attempts, active days, slices, errors, reviews, and manual queue.
- Verification: backend pytest `124 passed`; frontend `npm.cmd run build` green.
- Next: review the weekly mentor-note draft from the 2026-06-23..2026-06-30 digest; do not publish to TG until the operator approves the text. Then clear the 2 old manual-review OДЗ items.

> Короткая текущая карточка. История/детали — `SESSION_LOG.md` (верх) и
> код/контракты — канонические docs в `docs/` и `AGENTS.md`.

Запрещено:

- вести параллельные постоянные task logs;
- считать временные заметки отдельной историей проекта.

Запись в `SESSION_LOG.md` должна быть короткой:

- задача и статус;
- 3-6 пунктов по сути;
- проверка;
- открытый хвост, если он есть.

`ACTIVE_TASK.md` обновлять когда меняется цель, состояние, ключевые решения или следующие шаги.

## 3. Единый рабочий цикл

1. стартовать с одного набора источников (п. 1 + ACTIVE_TASK.md);
2. исследовать код только после этого;
3. завершать работу обновлением `ACTIVE_TASK.md` и короткой записью в `SESSION_LOG.md`;
4. обновлять канонические docs только если реально изменился active flow или контракт.

## 4. Simplicity First (обязательно)

Сложность накапливается необратимо. Каждое изменение должно уменьшать сложность или оставлять её прежней.

- Не вводи абстракции, параметры и слои "на будущее" — только под реальную текущую задачу
- Прячь неизбежную сложность за узким интерфейсом — снаружи просто, внутри можно сложно
- Три похожих строки лучше преждевременной абстракции
- Если код можно удалить без последствий — удали

## 5. Граф вместо разведки

Перед тем как тратить токены на разведку кода (Glob/Grep/чтение файлов по подозрению) — сначала смотри карту в `graphify-out/GRAPH_REPORT.md`. Она уже знает архитектуру, god nodes и связи. Лезь в код только когда граф не даёт ответа.

---

## Текущая карточка

- Цель: Telegram — канал ежедневного дрилла части 1 + повторов; сайт — части 2 + витрина-контролёр. Бэкенд сам решает что слать (повторы вперёд, новые темы фазы — в остаток лимита).
- Статус: **Phase 1 + Phase 2 реализованы и зелёные (pytest 92 passed)**. Phase 1: мгновенная точная проверка, `list_daily_drill`, in-process бот (aiogram через прокси), флаг `drill` в MCP. Phase 2: `build_daily_queue` (повторы→новые, carry-over, дедуп, `shortage`), `select_daily_queue` (policy), `list_approved_for_topic` (свежая=не назначавшаяся), корректный lifecycle повтора + разрешение back_to_work (option A), обязательный chat_id + онбординг, идемпотентный утренний пуш, MCP-инструмент `build_daily_queue`. **Вживую (пуш/чат после Phase 2) не прогнано.**
- Ключевые решения: бот = in-process adapter; маркер дрилла = `source_ref` (`daily:new:<topic>`/`daily:review:<card>`/`daily:manual`); review-PASS закрывает карточку без новых +7/+30; back_to_work передриллится свежей задачей → DONE; пустой банк → явный `shortage` (не молчаливый недобор).
- Срез по теме: **готов и live** (docker api+web). На странице «Срез знаний» — дропдаун «Тема»; проверка по ключу; диагностика подписана темой. Семантика `topic_check`.
- **Срез в TG + ИИ-приём ответов: реализовано и задеплоено live.** Курс: TG = ученический тренажёр, сайт = витрина (фронт не трогали). Общий `ShortAnswerJudge` (порт `assess→AiAssessment`, политика exact-авторитет в `_grade_answer`); API/MCP детерминированы (ExactOnly), ИИ только в боте (`LlmShortAnswerJudge`, `show-work-v2`). `judge_task_answer`/`record_slice` (аудит `details_json`, миграция `b8e4f1a2c3d9`). Бот: `/slice`→предмет→тема→по одной с ИИ-фидбеком, `/cancel`. Docker: сервис `bot` + `[bot]` extra (live: `llm ON`, `getMe OK`).
- **Формат «покажи ход» + мульти-чат:** бот просит расписать решение; LLM извлекает финальный ответ (заземляет вердикт) + оценивает метод (флажит «верный ответ, неверный метод»). Авторизация — список (`telegram_extra_chat_ids`); родитель `1682176470` добавлен в `.env`, live-контейнер видит оба ID; ученик — цель пуша.
- **TG UI/UX v1: реализовано и задеплоено live.** Нативные команды `/start`, `/today`, `/slice`, `/progress`, `/help`, `/cancel`; `/start` = главное меню с inline-кнопками, `/today` только читает backend-очередь, произвольный текст не запускает задания. Срез получил возврат к предметам и чистую замену inline-сообщений; прогресс берётся из `get_dashboard`. Host `HTTPS_PROXY` передаётся только в `TELEGRAM_PROXY_URL` bot-контейнера. Live: `getMe OK`, меню команд подтверждено через Telegram API. Детский smoke выявил два P0-дефекта грейдера: противоречивый positive-feedback после sanitize и потерю extracted-correct при повторном подсчёте среза.
- **Short-answer кластер РЕАЛИЗОВАН (A/B/C):** противоречие `✅ Верно!`/`Близко` снято (`_sanitize_feedback`→`_mask_answer`: маскируем эталон, разбор сохраняем); `record_slice` не теряет extracted-correct и не пишет ложные error-events (метка `exact` только для raw, извлечённый верный → `llm_equivalent`); детерминированное сравнение чисел/дробей через `Fraction` + запрет ИИ переопределять доказанное неравенство (`0,667≠2/3`, в т.ч. через «извлечённый» эталон). EvidenceReviewer миссий не трогали. `pytest` 112 passed, ruff чист, +3 регресс-теста.
- **Наставнические заметки в TG реализованы + pre-live правки по review сделаны:** агент пишет заметку через `publish_feedback`, бот доставляет её утренним пушем (`mentor_notes.delivered_at`, миграция `c0d1e2f3a4b5`). Закрыто: миграция бэкфилит существующие как доставленные (старьё не уйдёт); `_morning_push`→try/except+`_run_daily_push` (сбой не убивает цикл); `_split_for_telegram` режет текст ≤4096. Семантика — at-least-once (редкий дубль при краше send↔commit допустим для пилота). `pytest` 114 passed.
- **Release-smoke готов:** `scripts/release_smoke.py` (health + миграции код-head vs БД + бот getMe + живой Qwen-judge; read-only, без сообщений ученику; exit code). Прогон против live: health/getMe/judge OK, миграции RED (БД `b8e4f1a2c3d9` < код `c0d1e2f3a4b5`) — деплой не сделан. Реальную доставку ученику в автотест не прячем (необратимый outward); логика доставки/грейдинга уже e2e в pytest.
- **Контролёрская видимость заметок:** `delivered_at` выведено наружу — на дашборде («Обратная связь наставника») бейдж «✅ отправлено ученику <дата> / ⏳ ожидает» + полная история; при доставке родителю (`telegram_parent_chat_id`) уходит Telegram-пинг с превью. Гейт публикации — ручной (агент→ОК→публикация→авто-доставка). `pytest` 115 passed, фронт tsc ок.
- **ЗАДЕПЛОЕНО (24.06), смок GREEN:** миграция `c0d1e2f3a4b5` применена, api/web/bot на новом коде, Qwen-judge живой.
- **Полный отчёт-заметка доставлен Ульяне (24.06):** одна заметка `4c2d85ed` — мотивирующая часть сверху + подробная аналитика ниже; отправлена сразу (host-запуск `_deliver_mentor_notes`), `delivered_at`=11:40 → дашборд «✅ отправлено», пинг родителю (если задан `TELEGRAM_PARENT_CHAT_ID`). Утренняя короткая `131481a4` удалена по явной команде (одна чистая заметка). Ручную кнопку на сайте решили НЕ делать (YAGNI; поток «попроси агента → ревью → публикация» достаточен).
- **Снижение тревоги — язык прогресса (25.06, ЗАДЕПЛОЕНО, смок GREEN):** коммит `87533fd`; `up -d --build api web bot` (миграции не было — схему не меняли). Проверка боевого API: `/program` current-phase `coverage.under_review=7`; web HTTP 200; bot свежий образ, RestartCount=0. Фикс overlap (ревью Codex): «в работе» = `in_progress − under_review` (корзины непересекающиеся), +guard-тест. Дашборд показывал `confirmed=0 / 0%` → ребёнок слышит «ничего не закрыла». Меняли язык, не модель (ревью Codex). `coverage`+`under_review`; фронт «Программа» ведёт с «в работе/на повторении/подтверждено» (полоса = «затронуто» = total−open), не с «0%»; TG `/progress` — строка активности по текущей фазе. Правило «зачтено» (верная задача + повтор, не «100%») — на странице и в `/progress`. #1 (повтор другой задачей) **в коде уже корректен** (свежая задача / `shortage`, старую не переиздаёт) — блокер контентный (тонкий банк). #4/#5 (олимпиадные, полный разбор) отложены из кода — словами/ручной заметкой. `pytest` 115, tsc ок.
- **Банк математики Ч1 наполнен (25.06):** +36 задач через MCP (`add_task`→`approve_task`), 12 тем июня math `3→6/тема`. Ответы проверены вычислением (`scratchpad/gen_math.py`, анти-poison). Анблок #1: в темах появились неназначавшиеся siblings для «повтора другой задачей». Часть 2 (№13/14/16/17/18) не трогали (символьный ответ). Осталось по математике: при желании — июльские темы (экономика/стерео/планиметрия/параметр, по 3) и интервальные (Неравенства/ОДЗ).
- **Банк информатики (Python) наполнен (25.06):** +28 задач, 7 ядровых Python-тем по +4 (basics/arithmetic/conditions/for/while/strings/lists). Формат: «что выведет» (трассировка) + «напиши и дай число»; ответ = реальный stdout прогона (`scratchpad/gen_inf.py`). Итог: 5/5/5/5/4/5/4. Всего в банке 142 задачи.
- **Визуализация — фигура решения в drill-разборе (29.06, ЗАДЕПЛОЕНО, live-проверено):** коммит `d90a826`. Принцип: фигура — чистая функция эталона/условия, ИИ в рисовании нет; **показ только после попытки** (до — утечка ключа). Числовая прямая по интервальному ответу (неравенства/ОДЗ). `domain/figures.py` = чистый `parse_interval_answer` (leak-safe), `infrastructure/figures_render.py` = `render_number_line` (matplotlib, вынесен из domain), `LearningService.drill_solution_figure(mission_id)` отдаёт PNG post-attempt, бот `_on_answer` шлёт фото. Парсер не уверен → фигуры нет. matplotlib в extra `[bot]`. Live: рендер в прод-контейнере (кириллица ок, 8244B) + доставка из бота в родительский чат. Решения по ресёрчу: движок не пишем — web-интерактив = **JSXGraph** (MIT), 3D = **GeoGebra** embed (non-commercial!), оба отложены до доказанной потребности; `figure_json` на задаче не вводим (потечёт до попытки); OSS — только после пользы в пилоте ([[scenario-gate-oss-plan]]).
- **Банк информатики part-1 наполнен (29.06):** +28 задач, 7 верифицируемых тем по +4 (системы счисления, информ. объём, логика 1→5, делители №25, пути в графе, рекурсия-трассировка, кодирование Фано). Ответы посчитаны кодом (`scratchpad/gen_inf2.py`). Информатика всего 65 одобренных, в банке 170. Визуальные темы (диаграммы/БД/Excel/файл/теория игр) отложены — нужен другой канал.
- Следующие шаги: (1) **наблюдать визуализацию** на 3–5 дрилл-неравенствах; помогает → второй рендерер, нет → не расширять (решение пользователя); (2) визуальные информ-темы (диаграммы/БД/Excel) — отдельным каналом, когда дойдёт; (3) после 16:00 МСК проверить доставку/бейдж/пинг (`delivered_at`); задать `TELEGRAM_PARENT_CHAT_ID`; (4) единая политика на пути миссий (не зануляй верный ответ за метод); (5) часть 2 на сайте; (6) ревизия сайта; (7) погасить теневой uvicorn на host:8001.
