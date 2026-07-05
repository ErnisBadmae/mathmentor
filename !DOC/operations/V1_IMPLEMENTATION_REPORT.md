# V1 Implementation Report

Дата: 2026-06-16

## Зачем был нужен этот срез

Цель работы была не “добавить много кода”, а довести EGE Mentor до первой рабочей версии, которой можно начать пользоваться в семейном пилоте:

- открыть dashboard;
- увидеть реальные 65/50/0.4 из текущего трекера;
- получить список сегодняшних миссий;
- отправить попытку;
- сохранить evidence;
- закрыть тему или вернуть её в повтор;
- увидеть журнал ошибок и очередь повторения;
- поднять это локально через один production-путь;
- закрыть критичные узлы регрессионными тестами.

Главный риск до этого среза: продукт выглядел как “дашборд подготовки”, но backend ещё не владел полным циклом состояния. Значит интерфейс мог показывать пустые, старые или слишком оптимистичные данные.

## Обязательное ограничение сложности

Для дальнейшей разработки обязательно придерживаться `.claude/rules/simplicity.md`.

Практический смысл для этого проекта:

- каждое изменение должно решать текущую продуктовую боль, а не добавлять слой “на будущее”;
- новая абстракция допустима только с явным обоснованием;
- не добавлять LangGraph, очереди, vector DB, CDC, отдельные сервисы и registry-паттерны, пока семейный пилот не доказал, что без них нельзя;
- если задачу можно решить внутри текущего FastAPI modular monolith, решать внутри него;
- сложность внешних протоколов и LLM скрывать за узкими портами;
- frontend не должен изобретать coaching logic, он показывает backend truth-state.

Это правило зафиксировано в `AGENTS.md`, чтобы следующие агенты не расширяли архитектуру без причины.

## Что болело и что было сделано

### 1. Dashboard мог быть пустым или врать о прогрессе

Проблема: `subject_tracks.current_score` был полем, но не было понятного пути, кто и когда его обновляет. Был соблазн двигать score после каждой успешной mission, но это смешивает тренировочную задачу и экзаменационный балл.

Решение v1: `current_score` обновляется только объективными score events: стартовый baseline, недельный вариант, срез или ручное событие guardian/operator. Daily missions и evidence не двигают экзаменационный score.

Почему так:

- успешное решение одной темы не равно приросту экзаменационного балла;
- dashboard должен быть консервативным, иначе продукт будет мотивирующе врать;
- daily evidence остаётся важным сигналом для topic closure/repeat, но не для exam score.

Что добавлено:

- `ScoreEventORM`;
- endpoint `POST /students/{student_id}/score-events`;
- seed baseline 65/50;
- importer dashboard/variants;
- regression test, что passed attempt закрывает mission, но не меняет `current_score`;
- regression fix: dashboard importer больше не перезаписывает информатику нулём из информационной строки “под-трек программирования”.

### 2. Rule-based reviewer был опасно оптимистичным

Проблема: при `LLM_PROVIDER=disabled` fallback мог ставить `score=100` и закрывать тему, хотя реальной проверки не было. Это самый опасный тип ошибки для подготовки: ребёнок получает зелёную тему без знания.

Решение v1: fallback fail-closed.

Теперь:

- известные простые ошибки могут быть классифицированы как failed;
- непустая содержательная попытка без LLM получает `needs_manual_review`;
- topic не закрывается до ручной проверки;
- manual review создаёт новый evidence record, а не мутирует исходный.

Почему так:

- лучше честно требовать guardian review, чем автоматически засчитывать;
- evidence ledger остаётся append-only;
- можно восстановить, что сказал AI/fallback и что потом решил взрослый.

### 3. Evidence не был достаточно удобен для истории по теме

Проблема: evidence был связан с mission, а topic history приходилось получать через mission. Для v1 это работает, но для динамики по теме нужен прямой ключ.

Решение v1:

- добавлен `topic_id` в evidence;
- при submit/manual decision он копируется из mission;
- manual review и spaced reviews используют topic связь.

Ограничение: отдельное materialized view или сложный аналитический слой не добавлялись. Это сознательно отложено по правилу simplicity.

### 4. Невалидный `mission_id` давал 500

Проблема: stale frontend/cache или ручной запрос могли отправить несуществующую mission. API должен возвращать понятный 404, а не Internal Server Error.

Решение v1:

- `LookupError` маппится в 404 на уровне FastAPI app;
- `ValueError` маппится в 400;
- добавлен regression test;
- smoke-check через nginx proxy подтвердил 404 на несуществующую mission.

### 5. Не было одного production-пути запуска

Проблема: можно было поднять отдельные части, но не было одного documented path: Postgres -> migrations -> seed -> import -> API/web.

Решение v1:

- добавлен Dockerfile для backend;
- добавлен Dockerfile/nginx для frontend;
- `docker-compose.yml` теперь поднимает `postgres`, `api`, `web`;
- добавлен `scripts/prod_up.ps1`;
- добавлен `scripts/backup_postgres.ps1`;
- README описывает LAN production path.

Smoke status после работы:

- `postgres` Up/healthy;
- `api` Up на `8001`;
- `web` Up на `8080`;
- `http://127.0.0.1:8080/api/health` возвращает 200;
- protected API работает через `X-EGE-MENTOR-TOKEN`.

### 6. Seed и import были разорваны

Проблема: пустая схема после migration не даёт полезный dashboard. Нужно было гарантировать стартовое состояние 65/50/0.4 и импорт текущего tracker без дублей.

Решение v1:

- seed создаёт guardian, student, subject tracks, стартовые missions, score events, clean-sheet baseline;
- importer пишет canonical records из текущего workbook;
- importer idempotent через `source_ref`;
- сохраняются `source_file`, `source_sheet`, `source_row`, `source_ref`;
- root `scripts/preview_tracker.py` умеет preview и `--write`.

Импортируемые листы:

- `Дашборд`;
- `Дневной лог`;
- `Журнал ошибок`;
- `Чистый лист`;
- `Повторение`;
- `Варианты`.

Ограничение: импорт сейчас покрывает Excel tracker. Полный Obsidian-корпус не был изучен и не превращён в требования.

### 7. Frontend показывал не весь backend truth-state

Проблема: frontend был shell/flow, но не закрывал полный операторский контур.

Решение v1:

- API client знает token header;
- добавлен token gate;
- dashboard берёт current student и backend dashboard;
- daily work берёт backend missions и submit endpoint;
- error journal берёт backend errors;
- review queue берёт backend reviews;
- manual review queue позволяет guardian/operator принять решение по evidence.

Ограничение: mission create/edit UI и score-event UI ещё не сделаны. API уже есть, но операторский интерфейс надо добавить отдельно.

### 8. Нужны были регрессионные тесты на бизнес-инварианты

Добавлены backend tests на v1-инварианты:

- seed создаёт 65/50/0.4;
- passed attempt закрывает mission и создаёт +7/+30 reviews;
- passed attempt не двигает `current_score`;
- failed attempt переводит mission в repeat и пишет error event;
- hinted code attempt не улучшает clean-sheet ratio;
- rule-based fallback требует manual review;
- missing mission возвращает 404;
- importer idempotent;
- dashboard importer не затирает score информационной строкой без числового балла;
- повторный import не откатывает score, полученный из листа variants.

## Принятые продуктовые решения

### `current_score` не равен progress по миссиям

`current_score` означает “последний объективный экзаменационный сигнал”. Это baseline, weekly variant, контрольный срез или ручной score event. Решение mission влияет на topic state, evidence, repeat/review, но не на exam score.

### AI не является product brain

LLM/fallback только оценивает попытку. Application layer решает:

- закрывать mission или repeat;
- создавать error event;
- ставить spaced reviews;
- учитывать clean-sheet;
- требовать manual review.

### Evidence append-only

Ручная проверка не переписывает исходный evidence. Она создаёт новый evidence с `model_id=manual-review`. Это нужно для replay/debug: можно видеть, что реально пришло от AI/fallback и какое решение принял взрослый.

### LAN production вместо публичного SaaS

Для семейного пилота достаточно Docker Compose на локальной машине и access через LAN. Это меньше инфраструктуры, меньше рисков, быстрее до реального использования.

## Что проверено

Команды:

```powershell
cd C:\Users\badmaev_es\egeMentor\backend
.venv312\Scripts\python.exe -m pytest tests -q
```

Результат: `11 passed, 1 warning`.

```powershell
cd C:\Users\badmaev_es\egeMentor\frontend
npm.cmd run build
```

Результат: production build успешен.

Production smoke:

- `docker compose ps`: `postgres`, `api`, `web` Up;
- `GET http://127.0.0.1:8080/api/health`: 200;
- `GET /api/students/current` с токеном: 200;
- `GET /api/students/{id}/dashboard`: 65/50/0.4;
- `GET /api/students/{id}/errors`: импортированные ошибки доступны;
- `GET /api/students/{id}/reviews`: очередь повторения доступна;
- invalid `POST /api/attempts` с несуществующим `mission_id`: 404.

## Что я изучил из источников `C:\Users\badmaev_es\Desktop\ЕГЭ`

Изучено:

- Excel tracker через `scripts/preview_tracker.py`;
- структура листов `Дашборд`, `Дневной лог`, `Журнал ошибок`, `Чистый лист`, `Повторение`, `Варианты`;
- стартовые численные сигналы 65/50/0.4;
- текущие категории ошибок из tracker;
- формат provenance для импортируемых строк.

Не изучено:

- полный Obsidian vault;
- Markdown-заметки с логикой подготовки;
- материалы, где может быть описан реальный учебный процесс, критерии закрытия тем, недельные правила, семейные договорённости;
- исходная “business logic” вне Excel tracker.

Вывод: перед следующей крупной волной программирования нужно сделать отдельный product/specification pass по Obsidian-источникам.

## Почему теперь нужен документ требований

Код уже закрыл технический v1-loop, но следующая опасность не техническая. Опасность в том, что мы начнём добавлять фичи поверх неполной бизнес-логики.

Нужно кристаллизовать:

- какие роли реально есть в семье: ребёнок, родитель, оператор, tutor;
- что считается “темой” и когда она закрыта;
- какие типы mission нужны: тренировка, cold task, timed slice, review, weekly audit;
- как из ошибок рождается следующая mission;
- как отличать “знает метод” от “узнал знакомую задачу”;
- какие данные ребёнок реально готов вводить каждый день;
- какие решения должен принимать взрослый вручную;
- где AI допустим, а где запрещён;
- как должна выглядеть weekly review;
- какие Obsidian/Excel поля являются source of truth, а какие временные заметки.

Минимальный следующий документ: `docs/REQUIREMENTS.md`.

Предлагаемая структура:

- `Scope`: что входит в семейный пилот, что явно не входит;
- `Actors`: ребёнок, guardian/operator, LLM reviewer;
- `Core Loop`: plan -> mission -> attempt -> evidence -> review -> next mission;
- `Entities`: student, subject_track, topic, mission, attempt, evidence, error_event, review_item, score_event, audit;
- `State Machines`: mission status, evidence status, review status;
- `Scoring Rules`: что двигает exam score, что не двигает;
- `Clean-sheet Rules`: что улучшает ratio, что не улучшает;
- `Manual Review Rules`: когда нужен взрослый;
- `Import Mapping`: Obsidian/Excel -> canonical DB;
- `Acceptance Tests`: бизнес-сценарии, которые обязаны проходить.

## Что осталось после v1

Ближайшие задачи без добавления новой инфраструктуры:

- провести inventory Obsidian vault и составить `docs/REQUIREMENTS.md`;
- добавить frontend формы для mission create/edit и score events;
- подключить реальный OpenAI-compatible reviewer или явно работать в manual-review режиме;
- сделать smoke на телефоне ребёнка через LAN URL;
- настроить Windows Task Scheduler для `scripts/backup_postgres.ps1`;
- добавить restore-инструкцию из backup;
- расширить regression fixtures под реальные ошибки: sign transfer, ODZ over-filtering, condition reading, probability double count;
- добавить недельный audit как отдельную простую use case, без agent framework.

## Текущая оценка готовности

Готово для локального семейного pilot smoke:

- backend truth-state;
- frontend read/submit/manual review flow;
- import current tracker;
- production Docker path;
- basic backup script;
- regression tests for core invariants.

Не готово как “полный продукт подготовки”:

- нет формального требований-документа по Obsidian business logic;
- нет удобного operator UI для создания/редактирования mission;
- нет реального LLM rubric quality loop;
- нет расписанного restore процесса;
- нет недельного audit UI/flow;
- нет проверки реального LAN-доступа со второго устройства.

