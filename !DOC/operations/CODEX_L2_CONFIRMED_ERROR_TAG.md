# Codex Task: L2a Confirmed Error Tag

Status: ACCEPTED LOCALLY (senior review 2026-07-13). Not deployed.

This is L2a only. It creates trustworthy confirmed input for the later intervention
selector; it does not complete the full L2 acceptance criterion or wire that selector.

Senior verification: backend `218 passed`; frontend build passed; Alembic has exactly one
head, `f7a8b9c0d1e2`; `git diff --check` passed. The exact broad Ruff command still reports
the four pre-existing E501 findings already documented for `use_cases.py` and
`mcp/server.py`; no new line introduced by L2a is reported.

## Executor Contract

Implement exactly this task. Do not redesign the model, broaden the feature, or start L3.
If the repository differs from this specification, stop and report the mismatch instead of
inventing a replacement.

This task adds a manual confirmation annotation to an existing `error_event`. The raw event
and its original `category` remain unchanged. No category is inferred from a task type or an
answer-only miss.

## Objective

Allow the senior mentor, through MCP, to confirm one actionable category for an existing
answer-only error. Persist the confirmation and return it from `error_journal`.

## Fixed Design

Add these nullable columns to `error_events`:

- `confirmed_category`: `ErrorCategory`, nullable, indexed;
- `category_confirmed_at`: timezone-aware datetime, nullable;
- `category_confirmation_source`: string(80), nullable.

The existing `category` column is the raw observation and MUST NOT be changed.

Confirmation rules:

- allowed: any `ErrorCategory` except `NONE` and `OTHER`;
- first confirmation writes the three fields with source `manual`;
- confirming the same category again is idempotent and preserves the original timestamp;
- confirming a different category after confirmation raises `ValueError`;
- missing error id raises `LookupError`;
- no automatic classification, correction history, selector wiring, or mission creation.

## Files Allowed

Only edit/create these files:

1. `backend/alembic/versions/f7a8b9c0d1e2_error_category_confirmation.py` (new)
2. `backend/app/infrastructure/models.py`
3. `backend/app/application/ports.py`
4. `backend/app/infrastructure/repositories.py`
5. `backend/app/application/use_cases.py`
6. `backend/app/adapters/mcp/server.py`
7. `backend/tests/test_error_classification.py` (new)

Do not edit frontend files, API routes/schemas, `record_slice`, dashboard aggregation,
`select_intervention_queue`, seed data, task-bank content, Docker, or documentation.

## Mechanical Steps

### 1. Migration

Create revision `f7a8b9c0d1e2`, revising `e6f7a8b9c0d1`.

`upgrade()` adds the three nullable columns and a non-unique index for
`confirmed_category`. Use this exact non-native SQLAlchemy enum definition, matching the
initial migration:

```python
sa.Enum(
    "ARITHMETIC",
    "SIGN_TRANSFER",
    "ODZ_LOGIC",
    "CONDITION_READING",
    "PROBABILITY_DOUBLE_COUNT",
    "UNKNOWN_METHOD",
    "ALGORITHM_LOGIC",
    "CODE_SYNTAX",
    "CODE_ALGORITHM",
    "TIME_MANAGEMENT",
    "NONE",
    "OTHER",
    name="errorcategory",
    native_enum=False,
)
```

Do not edit `backend/app/domain/enums.py`. `downgrade()` drops the index, then the three
columns.

Do not update existing rows: they must remain unconfirmed.

### 2. ORM

Add matching nullable fields to `ErrorEventORM`. Keep `category` untouched.

### 3. Port

Add this operation to `ErrorRepository`:

```python
def confirm_category(
    self,
    error_id: UUID,
    category: ErrorCategory,
    confirmed_at: datetime,
) -> UUID: ...
```

It returns the event's `student_id`, which the service uses to reload the public dict.

### 4. Repository

Implement `ErrorSqlRepository.confirm_category` with the fixed rules above. Set
`category_confirmation_source = "manual"`. Flush but do not commit.

Extend `list_errors` output with:

```python
"confirmed_category": event.confirmed_category,
"category_confirmed_at": event.category_confirmed_at,
"category_confirmation_source": event.category_confirmation_source,
```

Do not change the existing `category` filter; it still filters the raw category.

### 5. Application Service

Add:

```python
def confirm_error_category(
    self, error_id: UUID, category: ErrorCategory
) -> dict[str, object]: ...
```

Validate that `category` is not `NONE` or `OTHER`, call the repository with
`datetime.now(UTC)`, commit once, reload the event through `list_errors(student_id)`, and
return the matching dict. If it cannot be reloaded, raise `LookupError`.

Do not call `select_intervention_queue` and do not create missions or feedback.

### 6. MCP Tool

Add a write tool:

```python
confirm_error_category(error_id: str, category: str) -> Any
```

Convert inputs with `UUID(error_id)` and `ErrorCategory(category)`, call the application
service inside `SessionLocal`, and return `_serialize(...)` of the result. The docstring must
say this is a manual mentor confirmation and that `none`/`other` are rejected.

### 7. Tests

Create focused tests using `seeded_session`, `SqlAlchemyUnitOfWork`, and `LearningService`.
Insert an `ErrorEventORM` fixture with raw category `OTHER` directly in the test; do not
change seed data.

Required tests:

1. confirmation stores actionable category, timestamp, and source `manual`;
2. raw `category` remains `OTHER` after confirmation;
3. `list_errors` returns all confirmation fields;
4. confirming the same category twice preserves the first timestamp;
5. confirming a different category raises `ValueError`;
6. confirming `NONE` or `OTHER` raises `ValueError` and leaves the event unconfirmed;
7. unknown error id raises `LookupError`.

## Stop Conditions

Stop without broadening the diff if any of these is required:

- a new table or correction-history model;
- changing append-only evidence behavior;
- changing how slices create errors;
- adding frontend/API controls;
- wiring intervention selection;
- editing files outside the allowed list.

Report the blocker with the exact file/line and failing command.

## Verification

Run from the repository root:

```powershell
cd backend
.venv312\Scripts\python.exe -m pytest tests\test_error_classification.py -q
.venv312\Scripts\python.exe -m pytest tests -q
.venv312\Scripts\python.exe -m ruff check app\application\ports.py app\application\use_cases.py app\infrastructure\models.py app\infrastructure\repositories.py app\adapters\mcp\server.py tests\test_error_classification.py
.venv312\Scripts\alembic.exe heads
cd ..\frontend
npm.cmd run build
```

Expected migration result: exactly one Alembic head, `f7a8b9c0d1e2`.

Do not deploy, run a live migration, reseed, commit, or edit task/session documentation.

## Required Final Report

Return only:

1. files changed;
2. concise behavior implemented;
3. exact verification commands and pass/fail counts;
4. `git diff --stat`;
5. blockers or deviations, if any.
