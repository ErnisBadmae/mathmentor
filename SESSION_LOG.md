# Session Log

Журнал рабочих сессий. Последние 15 записей. Старое — в `archive/SESSION_LOG_[YEAR]-[MONTH].md`.

---

## 2026-06-23 — TG: мульти-чат авторизация + формат «покажи ход»

Статус: реализовано, зелёное, задеплоено live

- Мульти-чат авторизация: настройка `telegram_extra_chat_ids` (через запятую) + property `authorized_chat_ids` (ученик + тестовые); `_is_authorized` = членство. В `.env` добавлен `TELEGRAM_EXTRA_CHAT_IDS=1682176470` (родитель для тестов); ученик остаётся целью утреннего пуша. Также ранее дописан `TELEGRAM_PROXY_URL` (из `HTTPS_PROXY`) — у bot-контейнера своего нет.
- Формат «покажи ход» (выбор пользователя — часть 1 + метод): промпты бота/дрилла просят кратко расписать решение и указать ответ. `AiAssessment += extracted_answer`; LLM извлекает финальный ответ + оценивает метод (метод-фидбек, явно флажит «ответ верный, но метод неверный»). `_grade_answer` заземляет вердикт на `extracted_answer` (+ exact на сыром), forced-correct → безопасный фидбек. `prompt_version=show-work-v2`.
- Деплой: пересобран `bot` (+`api`, общий образ); в контейнере `show-work-v2`, `llm ON`, `getMe OK`. Миграций нет.

Проверка: `pytest` 103 passed (show-work тесты в `test_grader.py`, мульти-чат в `test_bot.py`). ruff мои строки чисты (2 pre-existing).

Открытый хвост: вердикт «покажи ход» заземляется на ИИ-извлечённый финальный ответ (сырой текст с ходом целиком не совпадёт) — слабее чистого exact, но сравнение детерминированное + провенанс; метод влияет на фидбек, не на вердикт/lifecycle. Часть 2 (полные задания 13-19; текст неудобен, естественно — фото/vision-модель) — отдельным решением.

## 2026-06-23 — Срез в TG + ИИ-приём ответов (общий ShortAnswerJudge)

Статус: реализовано, тесты зелёные, миграция применена; вживую (бот) не прогнано

- Общий грейдер (по ревью Codex, 2 раунда): порт `ShortAnswerJudge.assess → AiAssessment` (сырое мнение ИИ, без политики); политика 1–6 в `LearningService._grade_answer` — exact-match авторитетен, ИИ только вытаскивает эквивалент на промахе, сбой ИИ → детерминированный exact (fail-open), провенанс, `_sanitize_feedback` (best-effort режет утечку ключа), forced-correct → безопасный фидбек. `LlmShortAnswerJudge` (JSON {equivalent,feedback}, temp0) + `ExactOnlyJudge`.
- Поверхности: API/MCP = `ExactOnlyJudge` (веб-срез детерминирован, текст «по ключу» правдив, фронт НЕ трогаем); бот = `LlmShortAnswerJudge` — ИИ только в TG.
- Срез: `judge_task_answer` (единая точка оценки) + `record_slice` (единая точка персистентности: re-load задач, пере-верификация exact, доверие только флагу `llm_equivalent` без повторного ИИ; аудит-детали в новой JSON-колонке `StudyLogEntry.details_json`, миграция `b8e4f1a2c3d9`). `grade_slice` стал async. Дрилл переведён на общий грейдер.
- Срез в TG: `/slice` → предмет (inline) → тема (inline) → задачи по одной, `judge_task_answer` + фидбек сразу, `record_slice` в конце, `/cancel`; callback'и проверяют авторизацию + закрывают спиннер; маршрут режима срез>дрилл>nudge.
- Docker: `Dockerfile` ставит `.[dev,bot]`; в compose добавлен сервис `bot` (long-poll, `restart: unless-stopped`) — пересборка api бота не обновляет.

Проверка: `pytest` 101 passed (+ `test_grader.py`, срез-флоу в `test_bot.py`). ruff на моих строках чист (2 pre-existing). `alembic upgrade head` применён к боевой БД (details_json). Бот импортируется, aiogram-обвязка (4 msg + 2 callback) ок.

Открытый хвост: (1) вживую не прогнано — нужен deploy: пересобрать docker (api+web+bot) + поднять сервис `bot`; в `.env` задать `TELEGRAM_STUDENT_CHAT_ID` и (если Telegram закрыт напрямую) `TELEGRAM_PROXY_URL`/`HTTPS_PROXY` для bot-контейнера. (2) Лёгкость ИИ-судьи (ложное «верно») — провенанс/`details_json` для аудита. (3) Контент-глубина банка; (4) ревизия/чистка сайта — отдельный план.

## 2026-06-23 — Срез по выбранной теме (live)

Статус: done, задеплоено (docker api+web), вживую через 8088

- Запрос: ребёнок изучил теорию темы → хочет прорешать тематические верифицированные задачи; срез выбирается по теме.
- Бэкенд: `list_gradable(subject, topic_id)`, `draw_slice(subject, size, topic_id)`, `grade_slice` подписывает диагностику темой (если все задачи из одной темы). Роут `/slices/draw?topic_id`.
- Фронт: `SlicePage` — дропдаун «Тема» (из `getProgram`, темы предмета с `tasks_in_bank>0`), «Вся тема (случайно)» по умолчанию; заголовок и диагностика по теме. `client.drawSlice(topicId)`.
- Семантика среза не изменена: это `topic_check` (балл не двигает), логирует диагностику + error-event на промах; lifecycle темы НЕ двигает.

Проверка: `pytest` 94 passed (2 новых — `test_slice_topic.py`); `npm run build` ок; пересобрал docker `api`+`web`, health 200; срез по теме через 8088 (user-facing) → 3 задачи темы, по предмету → 10.

Открытый хвост: (1) на host:8001 висит **сторонний старый uvicorn** (PID 32588) — теневой; фронт его не использует (ходит через 8088 → docker-сеть), но прямые тесты на 8001 отдают старый код — стоит погасить. (2) «умножение вероятностей» отдельной темы/задач нет — контент-гэп. (3) если нужно чтобы зачётный срез по теме двигал прогресс темы — отдельное решение.

## 2026-06-23 — Phase 2: авто-сборщик дня + lifecycle повторов (по ревью Codex)

Статус: реализовано, тесты зелёные; вживую (пуш/чат) не прогнано

- `build_daily_queue(student, limit) -> {filled, shortage}`: повторы (DUE + back_to_work) вперёд, новые OPEN-темы фазы в остаток; уже открытые daily-миссии считаются в лимит (carry-over); дедуп темы между повтором и новой; пустой банк по теме → явный `shortage`, не молчаливый недобор. Чистая `select_daily_queue` в `policies.py`.
- «Свежая задача = не назначавшаяся ученику» (а не просто нерешённая): `TaskSqlRepository.list_approved_for_topic(exclude_assigned_to)`.
- Lifecycle повтора (швы №1+№6): origin парсится из `source_ref`; `review` PASS → карточка `DONE` БЕЗ новых +7/+30; FAIL → `BACK_TO_WORK` без спавна; карточку трогаем только пока `DUE`/`BACK_TO_WORK`. back_to_work (решение польз., option A): сборщик передриллит карточку свежей задачей, успех → `DONE` (чинит пред-баг вечного BACK_TO_WORK, тема может дойти до CONFIRMED).
- Бот: `telegram_student_chat_id` обязателен (неавторизованному — его `chat_id` для онбординга, дриллы не выдаём); идемпотентный утренний пуш (`telegram_push_time`, `daily_drill_size`) через `build_daily_queue`, с уведомлением о дефиците. MCP: инструмент `build_daily_queue` (оператор собирает день + видит shortage).

Проверка: `pytest` 92 passed (8 новых: `test_daily_queue.py`, `test_bot.py`). ruff на изменённых строках чист (остались pre-existing: `_resolve_score` E501, `publish_feedback` E501, сортировка импортов MCP — не мои строки). Бот импортируется; `_seconds_until` ок.

Открытый хвост: (1) вживую не прогнано — нужен реконнект MCP (подхватить `build_daily_queue` + `drill`-флаг), `TELEGRAM_STUDENT_CHAT_ID` ребёнка, и/или дождаться пуша 16:00 MSK. (2) **ОБЯЗАТЕЛЬНЫЙ следующий срез — контент-глубина**: банк >3/тема + наполнить информатику. (3) дальше — часть 2 на сайте.

## 2026-06-22 — Telegram-дрилл части 1 (Phase 1)

Статус: Phase 1 done; Phase 2 не начата

- Продуктовая граница (решения через AskUserQuestion): TG = ежедневный дрилл части 1 + повторы (мгновенная точная проверка в чате), сайт = части 2 + витрина-контролёр; очередь по правилам бэкенда, повторы вперёд → новые темы фазы в остаток лимита.
- Грейдинг: `_grade_exact_answer` + ветка в `submit_attempt` (при drill+task+непустой `expected_answer`) → PASSED/FAILED без LLM, переиспользует `_apply_progression` (повторы +7/+30, error-event с категорией задачи).
- Выделенная поверхность `list_daily_drill` (только `daily:`-миссии со связанной задачей), НЕ `missions/today` — чтобы части 2 / операторские миссии не утекли в чат.
- Бот переписан как in-process adapter (как MCP): прямой `LearningService` через `SessionLocal`, без self-HTTP/токена; БД — source of truth, память — кэш; aiogram long-poll `/start`→условие→ответ→вердикт→следующая. `build_parent_digest` тоже на прямой вызов (чинит сломанный auth). Поправки по критике Codex.
- MCP `create_mission` получил флаг `drill` (`source_ref=daily:manual`); config `telegram_student_chat_id`.

- Живой прогон: установлен `[bot]` extra (aiogram 3.29). **Telegram в этом окружении доступен только через прокси** (прямой connect к `api.telegram.org` таймаутится; в env есть `HTTPS_PROXY`). aiogram гонит прокси через `aiohttp-socks` — добавил его в `[bot]` extra. Бот читает прокси из `telegram_proxy_url` или env `HTTPS_PROXY`. `getMe` через прокси OK → бот `@egemathandinformbot` (id 8708048855). Скурировал 3 части-1 дрилла в живой БД (`source_ref=daily:manual`), `list_daily_drill` отдаёт 3.

Проверка: `pytest` 84 passed (4 новых в `tests/test_drill.py`). ruff на изменённых файлах чист. Бот поднят и поллит через прокси (лог `Run polling for bot @egemathandinformbot`).

Открытый хвост: (1) E2E в чате — ждём `/start` от ребёнка по 3 скурированным дриллам (бот живой); (2) Phase 2 (авто-сборщик `build_daily_queue`/`select_daily_queue`/`list_approved_for_topic` + связка review-card с защитой `DUE` + carry-over + утренний пуш) не начата.

## 2026-06-19 — Конфликт порта 8080 (web)

Статус: done

- Диагноз: `WinError 10013` у основного проекта (стек `expert_*`/`englishfriend`) — это не резерв Windows (8080 вне excluded-диапазонов), а коллизия: хост-порт 8080 держал `egementor-web-1`.
- egeMentor web переехал 8080 → **8088**: правки в `docker-compose.yml` (`8088:80`) и `scripts/prod_up.ps1` (URL-строки).
- Пересоздал только web (`docker compose up -d web`); PID Docker-proxy не трогал (он общий для всех контейнеров).

Проверка: `http://127.0.0.1:8088/api/health` → 200 `{"status":"healthy"}`; 8080 в netstat свободен.

Открытый хвост: историчный `docs/V1_IMPLEMENTATION_REPORT.md` всё ещё упоминает 8080 — это лог прошлого прогона, не трогал. Новый локальный UI egeMentor: `http://<lan>:8088`, API напрямую — 8001.

## 2026-06-18 — Первый замер + публикуемая обратная связь

Статус: done

- Создал 4 миссии math_profile через MCP (`source=mcp:agent`): 2 рецидива (дробное неравенство, вероятность «только A») + 2 зонда части 2 (тригонометрия №13, экономика №16). Инструкции требуют расписать ход и засечь время.
- Новая фича `MentorNote`: заметки наставника, которые ученица читает на дашборде (лента, публикация сразу — без модерации). Решения уточнены через AskUserQuestion.
- Вертикальный срез по всем слоям: `MentorNoteORM` + миграция `f3c4d5e6a7b8`; порт+репо (`add`/`list_recent`); `LearningService.publish_feedback` + домерж `mentor_notes` в `get_dashboard`; `MentorNoteOut` в `DashboardOut`; MCP-инструмент `publish_feedback`; панель на `DashboardPage` (pre-wrap, без новых npm-зависимостей).
- Опубликована первая реальная заметка (стартовая, поясняет 4 миссии).

Проверка: `alembic upgrade head` ок; `pytest` 66 passed; `npm run build` ок; get_dashboard отдаёт `mentor_notes: 1`.

Открытый хвост: новый MCP-инструмент `publish_feedback` и обновлённый `get_dashboard` появятся в сессии агента только после реконнекта MCP (сервер stdio держит старый код). Настоящий разбор по ученице — после того как она прорешает 4 миссии (сейчас по ним 0 попыток).

## 2026-06-18 — Наполнение банка math_profile

Статус: done

- Накатил пропущенную миграцию `e2b3c4d5f6a7` (колонка `tasks.source_url`) — без неё MCP `add_task`/`list_tasks` падали с `UndefinedColumn`.
- Заполнил 18 пустых тем `math_profile` (13 фазы «Июнь», 5 фазы «Июль-август») по 3 проверенные задачи каждая — 54 штуки, все `approved`.
- Источник — reshuege.ru/sdamgia.ru (зеркало банка ФИПИ, Д. Гущин), `source_url` указывает на конкретную страницу задачи.
- Задачи, требующие картинку для решения, отбрасывались — брал только решаемые из текста.
- Нюанс: `add_task` дедуплицирует по `source_url`. Если одна и та же исходная задача нужна в двух разделах банка (было с темой 13 и «отбор корней на отрезке») — `source_url` нужно слегка варьировать (например, `&part=b`), иначе вторая запись тихо схлопнется с первой.

Проверка: `mcp__ege__program_progress` — у всех 18 тем `tasks_in_bank: 3`.

Открытый хвост: остальные `tasks_in_bank: 0` темы — informatics (задания 17/26/27, графы, ДП и т.д.) не трогали, только math_profile по просьбе пользователя.
