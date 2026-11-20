# Session Log Archive - 2026-W29

---

## 2026-07-17 - TG: skip-кнопка + самостоятельный выбор темы (задеплоено)

Status: ЗАДЕПЛОЕНО, смок GREEN (release_smoke + telegram_bot_runtime_smoke).

- По запросу ребёнка: кнопка «⏭ Пропустить» на дневном задании (та же семантика,
  что уже была у текстовой `/skip` — задание остаётся ACTIVE, откладывается в
  сессии бота) + новая команда/кнопка `/topics` («➕ Своя тема») — самостоятельный
  выбор темы части 1 трека, задача добавляется в «Сегодня» сразу.
- Product-развилки закрыты перед кодом: self-pick только часть 1 (part-2/manual-
  review темы недоступны — им нужна ручная проверка на сайте), пререквизиты
  уважаются (это evidence-based авто-проверка по `solved_count`, не декларация —
  риска «забыла отметить» нет).
- Backend: `list_self_pick_candidates`/`self_add_topic_mission` в `use_cases.py`,
  переиспользуют существующие примитивы (`list_approved_for_topic`,
  `prerequisites_met`, `_requires_manual_review_path`). Новая миссия —
  `source_ref=daily:self:<topic_id>`, `daily:`-префикс даёт бесплатную интеграцию
  с остальным дрилл-конвейером. `describe_pick` — новая ветка `self_pick`.
  Bot: skip-клавиатура + общий хелпер `_skip_daily_task`, `_on_today_skip`,
  `_topics_keyboard`/`_on_topics`/`_on_topics_pick` по образцу `/ready`.
- Ноль миграций, ноль MCP, ноль фронтенда — фича целиком в TG-боте.
- Проверка: `pytest` 241 passed (было 228, +13); ruff по изменённым файлам без
  новых замечаний. Деплой: `docker compose up -d --build api bot`; `web` пришлось
  отдельно `restart` — nginx держал закешированный DNS на старый IP api-контейнера
  (502 до рестарта). `telegram_bot_runtime_smoke.py` и `release_smoke.py` — GREEN.

Open tail: реального тапа в живом Telegram-чате ребёнком ещё не было — проверено
только тестами и смоками. Попросить попробовать `/today` и `/topics` при следующем
заходе.

---

## 2026-07-17 - PDF-пайплайн для реальных прототипов ФИПИ + 9 задач в тонкие темы part-2

Status: live bank updated (draft->approved через MCP); no runtime code changed.

- Учебная обратная связь ребёнка: летний срез ~80% задач из открытого банка ФИПИ ->
  запрос вытягивать оттуда контент. Прямой скрейпинг (`ege.fipi.ru`, `sdamgia.ru`)
  заблокирован сетью/антиботом; нашли рабочий обходной путь — детали в
  `ACTIVE_TASK.md` ("Рабочая связка: реальные прототипы ФИПИ через PDF + PyMuPDF").
- Ключевая находка: `pdftotext` ломает буквы точек фигур в PDF-сборниках прототипов
  (курсивный Unicode Math Alphanumeric), `fitz` (PyMuPDF) из
  `expert-agent/venv_312` читает их корректно.
- Реальный shortage на момент сессии оказался НЕ в неравенствах/ОДЗ (уже 11-12 задач
  в банке — кто-то наполнил раньше), а в Стереометрии №14 / Планиметрии №17 /
  Параметре №18 (по 3 задачи каждая).
- Добавлено 13 approved-задач: 8 реальных прототипов ФИПИ (сборник MathStart, задачи
  14.6/14.15/14.20/17.3/17.7/17.14/18.2/18.8, каждый ответ пересчитан и перепроверен
  SymPy/координатной геометрией/численным перебором) + 5 задач той же формы,
  сконструированных агентом (честно помечены `source="agent"`, не выданы за
  прототипы).
- Банк по трём темам: 3->8 (стерео) / 3->8 (планиметрия) / 3->7 (параметр).
- Найден и обойдён баг дедупликации `add_task`: `source_url` служит уникальным
  `source_ref`; одинаковый плейсхолдер в двух вызовах тихо схлопнул вторую вставку
  в первую (задача пропала без ошибки). Исправлено уникальными пометками на задачу.

Open tail: метод воспроизводим для оставшихся ~40 прототипов на тему в том же PDF
(стерео/планиметрия/параметр) и для других part-2 тем при следующем заходе на
контент; экономическая (№16, вклады/кредиты) и неравенства/ОДЗ уже не в дефиците
(7 и 11-12 задач соответственно) — не трогать без явного запроса.

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
