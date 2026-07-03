# Active Task

## Current Snapshot (2026-07-03, after Qwen 093450)

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
