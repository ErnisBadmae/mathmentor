# NAVIGATION

Карта документации и правил навигации. Агенты и люди — читают только нужное, экономя токены.

## Токен-правило №1

Читай файлы последовательно, не все сразу. Каждый файл — ~200-300 строк. Если задача не требует деталей, прочитай `!DOC/README.md` → ссылку → конкретный раздел.

## Быстрый вход

| Если тебе нужно... | Читай | Строк |
|---|---|---|
| Понять, что делает система | `!DOC/README.md` | ~90 |
| Понять бизнес-правила системы | `!DOC/strategy/PRODUCT_DECISIONS.md` | ~32 |
| Понять, как работает система | `!DOC/architecture/ARCHITECTURE.md` | ~38 |
| Понять полные требования | `!DOC/strategy/REQUIREMENTS.md` | ~484 |
| Найти текущую задачу | `!DOC/operations/ACTIVE_TASK.md` | ~142 |
| Прочитать последние решения | `!DOC/operations/SESSION_LOG.md` (корень) | ~750 |

## Структура каталогов

```
egeMentor/
  README.md              ← Описание проекта, локальный деплой
  ACTIVE_TASK.md         ← Дублирует !DOC/operations/ACTIVE_TASK.md
  SESSION_LOG.md         ← Журнал сессий (корень, не в !DOC/)

  !DOC/
    README.md            ← Твой индекс (читай первым, ~90 строк)
    NAVIGATION.md        ← Эта карта
    DOC_GUIDELINES.md    ← Соглашения по обслуживанию документации

    operations/          ← Текущее состояние, runbooks, архив
      ACTIVE_TASK.md     ← Текущая рабочая карточка
      RELEASE_CHECKLIST.md
      V1_IMPLEMENTATION_REPORT.md
      AGENT_EXECUTOR_HARNESS.md

    architecture/        ← Подсистемы (каждый файл — отдельный контекст)
      ARCHITECTURE.md    ← Слои, БД, LLM boundary

    strategy/            ← Требования, бизнес-решения
      REQUIREMENTS.md    ← Полные требования v1
      PRODUCT_DECISIONS.md

    research/            ← Исследования и эксперименты
      fable/             ← Исследовательские заметки

  backend/               ← Python backend (FastAPI, SQLAlchemy)
  frontend/              ← Vite + React SPA
  scripts/               ← Утилиты, night_runner, docs_maintenance
  tests/                 ← Тесты
```

## Кто кому ссылается

```
!DOC/README.md
  ├── !DOC/architecture/ARCHITECTURE.md (как устроено)
  ├── !DOC/strategy/PRODUCT_DECISIONS.md (почему так)
  ├── !DOC/strategy/REQUIREMENTS.md (что должно делать)
  └── !DOC/operations/ACTIVE_TASK.md (что сейчас)

!DOC/architecture/ARCHITECTURE.md
  ├── !DOC/strategy/REQUIREMENTS.md (complement: how vs what)
  ├── !DOC/strategy/PRODUCT_DECISIONS.md (complement: how vs why)
  └── !DOC/operations/AGENT_EXECUTOR_HARNESS.md (bounded executor boundary)

ACTIVE_TASK.md (корень)
  └── !DOC/operations/SESSION_LOG.md (open tails → новые задачи)

SESSION_LOG.md (корень)
  └── ACTIVE_TASK.md (open tails → новые задачи)
```

## Чего читать НЕ надо (если не нужна глубина)

Эти файлы — исторический контекст. Читай только если:
- нужен полный обзор требований — `!DOC/strategy/REQUIREMENTS.md`
- изучаешь историю v1 — `!DOC/operations/V1_IMPLEMENTATION_REPORT.md`
- разбираешься в executor-harness — `!DOC/operations/AGENT_EXECUTOR_HARNESS.md`

Не читай заранее:
- `!DOC/archive/` — всё завершённое
- `!DOC/research/fable/` — эксперименты, не source of truth

## Как экономить токены

1. **Начинай с `!DOC/README.md`** — читай первым, даёт полную карту.
2. **Читай по ссылке** — `!DOC/README.md` → `!DOC/architecture/ARCHITECTURE.md` → конкретный раздел.
3. **Session-логи** — `SESSION_LOG.md` в корне содержит последние 15 записей.
4. **ACTIVE_TASK.md** — даёт контекст задачи. `SESSION_LOG.md` — детали. Не читай оба, если ACTIVE_TASK достаточно.
