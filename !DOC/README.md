# EGE Mentor Documentation

Last updated: 2026-07-03

EGE Mentor — семейный пилот для подготовки к ЕГЭ по профильной математике и информатике.
Цикл обучения: `plan -> mission -> independent attempt -> evidence -> review -> next mission`.

## Быстрый вход

| Если тебе нужно... | Читай |
|---|---|
| Понять, что делает система | `README.md` (этот файл) |
| Понять, как устроена | `!DOC/architecture/ARCHITECTURE.md` |
| Понять требования | `!DOC/strategy/REQUIREMENTS.md` |
| Понять бизнес-решения | `!DOC/strategy/PRODUCT_DECISIONS.md` |
| Найти текущую задачу | `ACTIVE_TASK.md` (корень) |
| Прочитать последние решения | `SESSION_LOG.md` (корень) |

## Структура

```
!DOC/
  README.md              ← Ты здесь
  NAVIGATION.md          ← Полная карта ссылок
  DOC_GUIDELINES.md      ← Правила обслуживания

  operations/
    ACTIVE_TASK.md       ← Текущая рабочая карточка
    SESSION_LOG.md       ← Журнал сессий (корень репо)
    RELEASE_CHECKLIST.md ← Чеклист релиза
    V1_IMPLEMENTATION_REPORT.md ← Статус v1
    AGENT_EXECUTOR_HARNESS.md ← Правила работы с Qwen

  architecture/
    ARCHITECTURE.md      ← Слои, БД, LLM boundary, деплой

  strategy/
    REQUIREMENTS.md      ← Полные требования v1
    PRODUCT_DECISIONS.md ← Бизнес-решения

  research/
    fable/               ← Исследования и эксперименты
```

## Корневые файлы (не в !DOC/)

| Файл | Назначение |
|---|---|
| `README.md` | Описание проекта, локальный деплой |
| `ACTIVE_TASK.md` | Дублирует `!DOC/operations/ACTIVE_TASK.md` |
| `SESSION_LOG.md` | Журнал сессий (источник — корень) |
| `AGENTS.md` | Правила для Claude Code / Codex |
| `RELEASE_CHECKLIST.md` | Дублирует `!DOC/operations/RELEASE_CHECKLIST.md` |

## Контекстный бюджет (tier-0)

Файлы, которые агент обязан прочитать на старте сессии:

- `README.md` — 115 строк
- `ACTIVE_TASK.md` — 142 строки
- `SESSION_LOG.md` — ~750 строк
- **Итого:** ~1012 / 2000 строк

## Автоматизация

```bash
python scripts/docs_maintenance.py audit   # отчёт о здоровье доков
python scripts/docs_maintenance.py archive # архивация старых сессий
python scripts/docs_maintenance.py report  # JSON для CI
```

Настройки: `pyproject.toml` → `[tool.docs-maintenance]`
