# Codex Task: Deterministic Declared-Answer Grading

Status: READY. Execute after the two approved L2a confirmations. This is an evidence-
integrity fix and must be completed before L3 intervention selection.

## Executor Contract

Implement exactly this task. Do not redesign the grader, add a general NLP parser, change
LLM prompts, or repair historical rows. If the current code cannot support this design in
the allowed files, stop and report the mismatch.

## Confirmed Incident

Live event `74f3e876-25af-45e3-80f2-05ab38d4e519` is a false learner error:

- task `5ddaef18-6c51-4c4b-ade9-46c5e9fa43da` has expected answer `7776`;
- the submitted text starts with `ответ 7776`, followed by a multiline solution;
- the daily drill ran through `ExactOnlyJudge`;
- whole-string exact comparison failed and persisted `FAILED`, score `0`, model
  `exact-answer`.

The existing grouped-integer policy is not the root cause. The deterministic path cannot
extract an explicitly declared final answer from a multiline solution.

## Objective

When a learner places one explicit `Ответ ...` line in a multiline answer, compare that
declared value deterministically with the task key. Preserve the existing exact-answer and
LLM-equivalence behavior for every other input.

The historical incident must pass after the fix:

```text
ответ 7776
решение: при одинаковых основаниях степени складываются ... 6^5=7.776
```

## Fixed Design

Add one pure domain helper:

```python
def extract_declared_answer(text: str | None) -> str | None: ...
```

Rules:

- inspect lines independently;
- ignore leading/trailing whitespace;
- match case-insensitive Russian `ответ` only at the start of a line;
- allow whitespace and one optional separator `:` or `=` after `ответ`;
- return the non-empty remainder of that line;
- return `None` for unlabelled text;
- return `None` when more than one non-identical declared-answer line exists;
- do not search for the last number, arbitrary numbers, equation results, or task keys;
- do not call an LLM and do not import infrastructure.

Examples:

```text
"Ответ: 7776\nрешение: ..." -> "7776"
"  ОТВЕТ = 1/2  "          -> "1/2"
"Ответ -3"                  -> "-3"
"получили 7776"            -> None
"не ответ 7776"            -> None
"Ответ: 5\nОтвет: 6"        -> None
```

Use the extracted candidate in `LearningService._grade_answer`:

1. existing whole-string exact match remains first;
2. a declared candidate matching through `answer_is_correct` is correct;
3. a declared numeric candidate proven unequal through `numeric_mismatch` is incorrect
   and an LLM must not override it;
4. otherwise preserve the current raw numeric mismatch, LLM-extracted grounding, and LLM
   equivalence order.

Add `explicit_exact` to `AnswerJudgment.grading_method`. Return it only when the whole raw
text is not exact but the declared candidate is deterministically exact. Update
`record_slice` to accept the server-produced methods `explicit_exact` and
`llm_equivalent`; continue to recompute whole-string exact locally.

Do not make arbitrary prose such as `решение ... 7776` pass under `ExactOnlyJudge`.

## Files Allowed

Only edit these files:

1. `backend/app/domain/policies.py`
2. `backend/app/application/use_cases.py`
3. `backend/tests/test_grader.py`
4. `backend/tests/test_drill.py`

Do not edit migrations, models, repositories, API/MCP/Telegram adapters, frontend, seed
data, task content, or documentation.

## Required Tests

Add focused regression coverage for all of these behaviors:

1. helper extracts `Ответ: 7776`, `ответ 7776`, `ОТВЕТ = 1/2`, and preserves the
   sign in `Ответ -3`;
2. helper rejects unlabelled prose and conflicting declared-answer lines;
3. `_grade_answer` returns correct + `explicit_exact` for the confirmed incident text
   under `ExactOnlyJudge`;
4. a declared wrong numeric answer remains incorrect even if later prose contains the key;
5. an LLM claiming equivalence cannot override a declared numeric mismatch;
6. `record_slice` counts `explicit_exact` as correct and creates no error event;
7. a full `submit_attempt` daily-drill regression using the incident shape persists
   `PASSED`, closes the mission, schedules reviews, and creates no error event;
8. existing pure short-answer, grouped-integer, decimal-approximation, and
   `llm_equivalent` tests remain green.

Do not weaken an existing assertion to make the new tests pass.

## Stop Conditions

Stop and report instead of broadening the diff if the implementation appears to require:

- a database migration or historical-row update;
- an LLM prompt/provider change;
- frontend/API/Telegram changes;
- a generic mathematical-expression parser;
- scanning unlabelled solution text for candidate numbers;
- changing task keys or the historical attempt directly;
- files outside the allowed list.

## Verification

Run from the repository root:

```powershell
cd backend
.venv312\Scripts\python.exe -m pytest tests\test_grader.py tests\test_drill.py -q
.venv312\Scripts\python.exe -m pytest tests -q
.venv312\Scripts\python.exe -m ruff check --ignore E501 app\domain\policies.py app\application\use_cases.py tests\test_grader.py tests\test_drill.py
cd ..\frontend
npm.cmd run build
cd ..
git diff --check
```

Do not deploy, mutate live data, amend the L2a commit, or commit this task. A senior review
must inspect the diff first.

## Required Final Report

Return only:

1. files changed;
2. exact parsing and grading behavior;
3. new tests and pass counts;
4. exact verification outputs;
5. `git diff --stat`;
6. blockers or deviations.
