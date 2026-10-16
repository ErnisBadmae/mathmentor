# AGENTS.md

Короткий bootstrap для Codex и других terminal agents внутри `egeMentor`.

Личная стратегия и место проекта в портфеле живут только в
`../PERSONAL_STRATEGY.md`. Для межпроектных решений дополнительно читать
`../AGENT_OPERATING_MODEL.md` и `../PORTFOLIO_CONTEXT.md`. Не копировать сюда личный
календарь, карьерные цели или общий план портфеля.

## Start Here

1. `!DOC/operations/ACTIVE_TASK.md` - текущая цель, статус и следующий срез.
2. Верхняя запись `SESSION_LOG.md` - последняя сессия.
3. `!DOC/strategy/REQUIREMENTS_CORE.md` - устойчивые продуктовые правила.
4. `!DOC/strategy/PRODUCT_DECISIONS.md` - принятые продуктовые решения.
5. `!DOC/strategy/PRODUCT_ROADMAP.md` - evidence-gated развитие продукта.

Использовать один working cycle. Не заводить второй task log.

## Product Boundary

EGE Mentor - семейный N=1 контур подготовки к ЕГЭ по профильной математике и
информатике:

```text
plan -> mission -> independent attempt -> evidence -> review -> next mission
```

Это не generic AI tutor и не SaaS. Пользовательский результат важнее количества
функций. Новая разработка разрешена только под blocker, наблюдаемый в реальном учебном
цикле.

## Architecture Defaults

- `backend/` - FastAPI modular monolith.
- `frontend/` - Vite React SPA.
- PostgreSQL - источник истины для обучения, сессий и evidence.
- Telegram - delivery adapter, не planning engine.
- LLM - ограниченный evaluator или classifier, не источник учебной истины.
- Frontend отображает backend truth-state и не создаёт параллельную логику.
- Domain/application не зависят от FastAPI, SQLAlchemy, Telegram и конкретного LLM.
- AI evidence хранит `model_id`, `prompt_version` и `rubric_version`.

Слои:

```text
backend/app/domain          pure models and deterministic policies
backend/app/application     use cases and ports
backend/app/infrastructure  repositories, LLM client, importers, storage
backend/app/adapters        FastAPI and Telegram
```

## Product Rules

- Attempt first, AI second.
- Hints не улучшают clean-sheet metric.
- Тема закрывается evidence threshold, а не временем в приложении.
- Закрытые темы получают review на +7 и +30 дней.
- Part 2 остаётся на human-reviewed пути.
- Ошибка не получает категорию из task type без подтверждающего evidence.
- Прогресс по экзамену меняется только через валидный score event.
- N=1 не используется для ML-прогноза балла.

Текущий продуктовый результат и ближайшая реализация берутся только из
`!DOC/operations/ACTIVE_TASK.md`, а не из этого bootstrap.

## Non-Goals

- public SaaS, payments и multi-tenancy;
- внешний ученик до принятого N=1 gate;
- autonomous coaching router;
- Qdrant, Neo4j, CDC, voice и LangGraph без доказанной потребности;
- общий runtime или библиотека с EnglishFriend;
- новая инфраструктура ради изучения технологии.

## Engineering Rules

- Перед любым изменением или ревью кода прочитать `.claude/rules/simplicity.md` и следовать
  ему: это единое правило простоты для Claude Code и Codex, его не дублируют здесь.
- Читать только файлы, нужные для задачи; искать через `rg`.
- Держать domain logic в `domain` или `application`, не в routes или React.
- LLM-вызовы держать за ports.
- Сохранять append-only provenance и human gates.
- Делать маленькие проверяемые изменения.
- Перед завершением запускать релевантный backend pytest и frontend build.
- Не повторять свежую проверку той же ревизии без причины.

## Local Qwen Boundary

Qwen через `backend/scripts/night_runner.py` - bounded executor. Разрешены read-only
отчёты, smoke, fixtures, механические single-file изменения и задачи с машинной
приёмкой. Запрещены архитектура, policy semantics, migrations, write paths,
multi-file refactors, UX и новые capabilities. Self-report не является evidence.

Если спецификация дольше самой правки, правку делает основной агент.

## MCP

MCP server - тонкий adapter над `LearningService`:

```powershell
cd C:\Users\badmaev_es\develop\egeMentor\backend
.venv312\Scripts\python.exe -m app.adapters.mcp.server
```

Он не даёт модели новых прав и не меняет product authority.

## Useful References

- `!DOC/README.md`
- `!DOC/strategy/REQUIREMENTS_DETAILS.md`
- `!DOC/strategy/PRODUCT_ROADMAP.md`
- `!DOC/architecture/EGE_EQUIVALENCE_RULE_V1.md`
- `!DOC/operations/AGENT_EXECUTOR_HARNESS.md`
- `backend/README.md`
- `frontend/README.md`

Если `graphify-out/graph.json` существует, вопросы об архитектуре сначала проверять
через `graphify query`, затем подтверждать по актуальному коду.
