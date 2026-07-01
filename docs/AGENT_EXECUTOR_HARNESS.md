# Architect to Executor Harness

Portable pattern for using a strong model as architect/reviewer and local Qwen/OpenCode as
a bounded executor. This project runs it through `backend/scripts/night_runner.py`.

## Principle

Qwen is not a junior developer. It is a bounded executor for low-risk work whose correctness
is checked by deterministic gates. Architecture, product judgment, gate design, runtime
contracts, and multi-file refactors stay with Codex/Claude and the human operator.

The architect front-loads the work into small task specs and falsifiable gates. The runner
executes each task in an isolated git worktree, records raw output, and either commits a
green auto-branch or removes the worktree on red/blocked. Morning review accepts or rejects
by raw logs, exact commands, and diff, never by Qwen's self-report.

## Allowed Work

- `report` / read-only tasks: endpoint smoke, latency profile, coverage/diff snapshots.
- Single-file mechanical edits with strict `files_allowed`.
- YAML, fixture, or doc-table additions from an explicit template.
- Keyword, scenario, or marker additions where the expected diff is obvious.
- Formatting and trivial lint fixes when the gate proves the result.

## Forbidden Work

- Architecture, source-of-truth contracts, policy/intent semantics, or gate design.
- Multi-file refactors, new imports, layer moves, runtime contract changes, or new capabilities.
- DB migrations, assignment execution, calendar/review mutation, and other write-path work.
- UX/product decisions or anything where morning review would take more than five minutes.

Calibration rule: if the task spec is longer than the expected diff, do the edit directly.
If review finds a false-green for a task class, remove that class from the Qwen queue.

## Task Schema

`backend/scripts/night_queue.json` currently uses a compact JSON form:

```json
{
  "id": "T-example",
  "comment": "What this proves.",
  "files_allowed": ["docs/EXAMPLE.txt"],
  "prompt": "Exact executor instruction.",
  "acceptance": [
    ["{PY}", "-m", "pytest", "backend/tests/test_figures.py", "-q"]
  ],
  "timeout": 600
}
```

Rules:

- `prompt: null` means a dry-run/read-only plumbing task with acceptance only.
- `{PY}` is replaced with the detected project venv Python.
- Edit tasks must set `files_allowed`.
- Acceptance must be machine-checkable and falsifiable without human judgment.
- Keep tasks single-purpose and small enough that a morning diff review is trivial.

## Gate Contract

GREEN means all acceptance commands pass and guardrails are satisfied:

- task runs in an isolated worktree under `NIGHT_RUNNER_WORKTREE_ROOT` or
  `C:\tmp\egeMentor-qwen-runs`;
- the main developer checkout is clean before live executor starts;
- changed files are within `files_allowed`;
- the main developer checkout did not change during executor run;
- executor made a real file change for prompt tasks;
- commit to `auto/<date>-<run>/<task-id>` succeeds.

RED means the executor ran but acceptance or guardrails failed. The runner removes the
worktree and deletes the temporary branch. BLOCKED means setup, worktree creation, timeout,
or isolation checks prevented a trustworthy result.

## Report Contract

Every run writes a per-run report under the worktree root, for example:

```text
C:\tmp\egeMentor-qwen-runs\<date>\report-<hhmmss>.md
```

The report must include:

- task id and status;
- branch name;
- prompt preview for executor tasks;
- exact commands;
- exit codes;
- raw stdout/stderr tails.

Raw output is mandatory. It is the morning-review evidence.

## Current egeMentor Rollout

The current queue is only a harness calibration:

1. `T-night-plumbing-tests`: acceptance-only dry-run task that runs
   `backend/tests/test_figures.py`.
2. `T-qwen-write-probe`: tiny write probe that may only create
   `docs/QWEN_WRITE_PROBE.txt` with exact UTF-8 token content.

Do not add real overnight work until the write probe produces a GREEN auto-branch from the
external worktree root and morning review confirms the diff.

## Sandbox MCP For Synthetic Testing

Local Qwen may use the sandbox MCP, not the senior mentor MCP, for synthetic tester work.
The sandbox server exposes deterministic in-memory flows only:

```powershell
cd backend
.venv312\Scripts\python.exe -m app.adapters.mcp.sandbox_server
```

Current tool:

- `run_student_simulation()` -> JSON report for interval overlay, unparseable interval
  fallback, and source_ref-gated probability visual.

It must not connect to production Postgres, Telegram, or student state. Add new tools here
only when they remain sandboxed and machine-checkable.

## Operating Commands

Dry-run, safe for Codex/Claude to run:

```powershell
backend\.venv312\Scripts\python.exe backend\scripts\night_runner.py --dry-run
```

Live run, operator only because OpenCode uses auto-approve inside the isolated worktree:

```powershell
backend\.venv312\Scripts\python.exe backend\scripts\night_runner.py
```

If a live run reports main-worktree contamination, stop and fix OpenCode `--dir`/workspace
resolution before trusting any overnight task.
