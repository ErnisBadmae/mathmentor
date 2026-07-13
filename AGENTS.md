# AGENTS.md

Compact bootstrap memory for Codex and other terminal agents working inside `egeMentor`.

## Start Here

Before reading anything else in this file, read `ACTIVE_TASK.md` (current goal/status/next steps) and the top entry of `SESSION_LOG.md` (most recent session). Both Codex and Claude Code share this single working cycle — do not keep a separate task log. At the end of a session, update `ACTIVE_TASK.md` and append a short entry to `SESSION_LOG.md`.

## Project Summary

EGE Mentor is a family-pilot preparation system for Russian EGE profile mathematics and informatics.

The product is **not** a generic AI tutor and not a toolbox. It is a guided preparation loop:

```text
plan -> mission -> independent attempt -> evidence -> review -> next mission
```

The first user is a real child preparing for EGE 2027. Existing preparation materials live outside the repo at:

```text
C:\Users\badmaev_es\Desktop\ЕГЭ
```

Important current observed baseline from the tracker:

- Goal: profile mathematics >= 85, informatics >= 85.
- Current rough baseline: profile mathematics 65, informatics 50.
- Programming clean-sheet ratio: 0.4.
- Current leading errors: arithmetic/sign transfer, ODZ logic, condition reading, probability double count.

## Why This Exists

The useful part of the current EngFriend project is the product discipline, not the codebase:

- backend-owned truth state
- mission progression
- structured evidence ledger
- model-agnostic LLM port
- replay/eval mindset

Do **not** import EngFriend runtime complexity. EGE Mentor is a separate sibling project because the domain, user journey, and risks are different.

## Architecture Defaults

- `backend/` is a FastAPI modular monolith.
- `frontend/` is a Vite React SPA.
- PostgreSQL is canonical for product/session/evidence state.
- The frontend renders backend truth-state and must not invent parallel coaching logic.
- Telegram is a delivery adapter only, not a planning engine.
- LLMs are bounded evaluators/classifiers, not the product brain.
- Every AI-produced evidence record must carry `model_id`, `prompt_version`, and `rubric_version`.

Layering:

```text
backend/app/domain          pure models, enums, deterministic policies
backend/app/application     use cases and ports
backend/app/infrastructure  DB repositories, LLM client, importers, storage
backend/app/adapters        FastAPI and Telegram delivery
```

Domain/application code must not depend on FastAPI, SQLAlchemy, Telegram, or concrete LLM providers.

## Product Rules

- Attempt first, AI second.
- For code: the learner writes in Thonny/local environment first, then submits code/answer for feedback.
- For math: the learner submits answer and reasoning/photo/text before any AI explanation.
- A topic closes by evidence crossing a threshold, not by time spent.
- Closed topics schedule spaced review at +7 and +30 days.
- Hinted code attempts must not improve the clean-sheet metric.
- Weekly audits should catch ?familiar task illusion?: cold tasks, timed, no AI/internet/phone.

## Current Repo State

Initial scaffold exists and is committed.

Working pieces:

- FastAPI app and health route.
- Alembic migrations and LAN-prod Docker Compose path.
- SQLAlchemy ORM models for users, invite codes, student profiles, subject tracks, topics, missions, attempts, evidence, error events, reviews, audits.
- `LearningService.submit_attempt` use case.
- append-only manual review path for LLM-disabled/failed checks.
- OpenAI-compatible LLM reviewer port with fail-closed manual review behavior.
- Excel preview/importer for the current tracker, preserving source provenance.
- React dashboard shell, daily attempt flow, error journal, review queue, manual review queue.
- Telegram parent digest helper stub.
- Domain and v1 regression tests.

Verified commands at scaffold time:

```powershell
cd C:\Users\badmaev_es\egeMentor\backend
.venv312\Scripts\python.exe -m pytest tests -q

cd C:\Users\badmaev_es\egeMentor\frontend
npm.cmd run build

cd C:\Users\badmaev_es\egeMentor
backend\.venv312\Scripts\python.exe scripts\preview_tracker.py
```

Known dev URLs when servers are running:

```text
Backend:  http://127.0.0.1:8001/api/health
Frontend: http://127.0.0.1:5174
```

## Global Plan

The primary goal through EGE-2027 is explicit: help Ulyana score **>=85 in profile
mathematics**. Product work is subordinate to that outcome:

- 80-90% learner outcome and evidence quality;
- 10-20% tutor/parent interviews and commercial hypothesis logging;
- 0% payments, public SaaS, or multi-tenant product work.

The product being built now is a **family-operated EGE preparation control loop**. It
decides what evidence is needed next, keeps independent attempts and reviews honest,
and tells the adult where intervention is required. It is not yet a commercial tutor OS.

The reusable product value is the closed evidence loop:

```text
attempt -> deterministic check -> error classification -> targeted intervention -> review -> score delta
```

The commercial hypothesis, to test later, is a vertical operating layer for
high-accountability profile-math tutors: the system runs between-lesson work and gives
the tutor only cases needing judgment. The ledger is an internal trust mechanism; the
external value proposition is student adherence, saved tutor time, and credible parent
reporting. Parent-operator B2C remains the fallback buyer hypothesis.

Four evidence-gated horizons:

1. **Valid baseline and first closed loop, July-August 2026, N=1.** Reserve
   2026-07-26 for the first timed profile-math mock, conditional on recovery; any move
   must set a new date. Close at least one confirmed-error -> intervention -> +7 review
   loop and explicitly log operator minutes. Exit: one valid score event, one auditable
   intervention outcome, and weekly active-day engagement visible.
2. **Proven delta, through December 2026, N=1.** Run comparable monthly EGE-format
   mocks, bring part 2 into the human-reviewed evidence path, and make the daily loop run
   without repeated parental pushing. Exit: 4-5 comparable mocks trending upward, with a
   December profile-math target around >=75, plus measured engagement and operator cost.
3. **Workflow generalization, only after a closed N=1 loop and visible score delta.**
   Interviews start now, but no external student onboarding occurs before the gate. Then
   test one design-partner tutor with 2-3 students for 4-6 weeks, using one isolated Docker
   stack per student. Exit: students work between lessons, the tutor acts on the briefs,
   mentor minutes remain acceptable, and the workflow runs without developer operation.
4. **Product form, after EGE-2027 or equivalent strong evidence.** Decide tutor B2B2C
   vs parent-operator B2C from observed adoption and willingness to pay. Only then consider
   shared tenancy, payments, public onboarding, broader subjects, or a content marketplace.

Explicit non-goals for now:

- no public SaaS onboarding
- no payments
- no external student pilot before the N=1 evidence gate
- no identity/multi-tenant implementation for the concierge pilot
- no generic AI tutor or autonomous coaching router
- no content-volume race with public EGE banks
- no ML score forecast from sparse N=1 data
- no Qdrant/Neo4j/CDC
- no voice
- no LangGraph/autonomous routing
- no shared/open-source libraries until common code proves stable across projects

## Local Next Plan

The first priority is to make the N=1 loop measurable and reviewable. Prefer process and
existing ports before code. A local development starts only when it removes a blocker
observed in the learner loop. The operating commitments below run in parallel with the
first code slice (L2); they are not prerequisites that freeze development.

### Parallel: Operating Commitments (Do Not Block Code)

- Keep 2026-07-26 reserved for the first valid profile-math mock, conditional on recovery.
- Schedule the first 3 interviews as a short calibration batch, then refine the interview
  script and complete 8-12 across strong solo tutors, small tutor teams, and parent-operators.
  Three interviews are not a market verdict. Ask about between-lesson homework adherence
  and task sources.
- Start the manual operator-time journal: student | date | task | minutes | decision.
- Do not infer operator minutes from DB timestamps.

### L1: Ground Truth and Student Engagement

- Run comparable monthly timed mocks in EGE conditions: no AI, internet, phone, or hints.
- Record exam progress only through `record_score_event`; daily work and topic checks must
  not move `current_score`.
- Treat weekly active days as both the current learner-retention metric and the first
  commercial adoption signal: the product has no value if students do not work between lessons.
- Do not add a numerical forecast. Show actual score events, target gap, and insufficient-data
  or risk status only when supported by explicit rules.

### L2: Confirmed Error Classification (First Code Slice)

- Start this slice now while the learner is recovering; it fixes an already observed data
  blocker and does not depend on a new mock or completed interviews.
- Specify and implement a fast mentor tag for answer-only slice errors before wiring
  `select_intervention_queue`.
- Never derive the learner's error category from the task type. Answer-only misses remain
  `other/unclassified` until a human confirms a category; automatic classification is allowed
  only when reasoning/code supplies evidence.
- Preserve provenance and append-only evidence semantics. Intervention selection consumes
  confirmed actionable categories only, never `none`, `other`, or an unconfirmed guess.
- Acceptance: regression tests prove that unclassified slice misses cannot trigger an
  intervention and a confirmed category can.

### L3: Human-Gated Intervention Proposal

- Run the weekly mentor review first through existing `mentor_brief`, `error_journal`,
  `publish_feedback`, and `create_mission` ports.
- Once L2 is trustworthy, expose `select_intervention_queue` as a read-only proposal with
  an explicit reason. The mentor must approve before a mission or note is created.
- Start with the observed categories: arithmetic/sign transfer, ODZ, condition reading,
  and probability double count. Use a prerequisite drill or method example, not merely
  another same-topic task.
- Link signal, approved action, mission, +7 review, and next score event with auditable
  source references. No autonomous router or weighted model.
- Acceptance: at least one real intervention completes the full loop and its operator time
  is recorded.

### L4: Part 2 Evidence Loop

- Keep profile-math part 2 on the reviewed path: solve on paper -> submit photo/text ->
  model structures the solution -> mentor approves the verdict.
- Make task types #13 and #15 routine before adding #16-18.
- Never autograde part 2 or let it move score/topic truth without human approval.
- Acceptance: 5-10 real reviewed solutions with clear evidence and sustainable mentor time.

### L5: Visual and Content Interventions

- Add a visual only for an observed misconception, record it as an intervention, and test
  transfer on a later cold task without the visual. Do not build a generic visual engine.
- Prefer JSXGraph for reusable 2D geometry; use a small task-specific 3D path only when
  stereometry evidence justifies it. Resolve commercial licensing before depending on GeoGebra.
- Add tasks only where the current loop reports shortage. Every task needs topic/skill,
  provenance, and an exact answer where possible.
- Treat content as a future tutor-supplied input through existing `add_task -> approve_task`,
  not as an internal volume race.

### Gated: External Workflow Pilot

- Start only after one closed intervention loop and visible N=1 score delta.
- Parameterize Compose project ports/env, then run one DB/token/bot stack per student.
- Do not implement shared identity or tenancy. Multiple-tab friction is pilot evidence for
  a future aggregated tutor cockpit, not a reason to build it upfront.
- Measure student active days, tutor actions on briefs, explicit tutor minutes, content
  onboarding cost, and willingness to continue/pay after 4-6 weeks.

### Operations and Hygiene

- Commit verified local changes promptly.
- Deploy/reseed live data when content-bank changes should affect the student.
- Keep release smoke, backups, Telegram parent delivery, and stray local services under operator control.

## Engineering Rules

- Always follow `.claude/rules/simplicity.md`: every change must keep complexity flat or reduce it; added complexity needs explicit product justification.
- Read only files needed for the current task.
- Prefer targeted search with `rg`.
- Keep domain logic in `domain` or `application`, not in API routes or React.
- Keep LLM calls behind ports.
- Do not add infrastructure because it is available; add it only when the product loop needs it.
- Use small, focused commits.
- Run backend tests and frontend build before reporting done.
- `scripts/verify.py` is the Claude Code Stop-hook for automatic backend `pytest` when
  backend files changed. Codex does not receive that hook: run verification once per
  revision, but do not repeat it when a fresh hook result already covers the same changes.

## Local Qwen Executor Boundary

Treat local Qwen/OpenCode through `backend/scripts/night_runner.py` as a bounded executor,
not as an architect or junior developer. Use it only for low-risk, machine-checkable work:

- read-only reports, smoke checks, latency snapshots, and coverage/diff snapshots;
- single-file mechanical edits with strict `files_allowed`;
- fixture/YAML/doc-table additions from an explicit template;
- keyword/marker additions where the expected diff is obvious;
- formatting or trivial lint fixes covered by gates.

Do not give Qwen architecture, source-of-truth contracts, policy semantics, gate design,
multi-file refactors, imports, runtime contract changes, migrations, write-path changes,
new capabilities, UX/product decisions, or anything requiring judgment-heavy review.

For the proven-delta strategy, Qwen is especially useful for read-only overnight reports:
score-event/digest readiness, error-journal/intervention candidates, part-2 manual-gate
readiness, content coverage, and release-smoke readiness. Accept only raw logs, exact
commands, diffs, and machine gates; never accept Qwen's self-report as evidence.

Calibration rule: if writing the task spec takes longer than doing the edit, do it in
Codex/Claude. If morning review finds a false-green, remove that task class from the Qwen
queue. Qwen output is accepted only through raw logs, exact commands, diff review, and
machine gates; self-report is not evidence. See `docs/AGENT_EXECUTOR_HARNESS.md`.

## MCP Server (agent as senior mentor)

An MCP server exposes this project's data and track edits so an agent (Claude/Codex) can act as the senior mentor — read student state/progress/history and edit missions/tasks/scores/reviews — **without any paid cloud LLM API in the backend**. It is a thin adapter over `LearningService` (`backend/app/adapters/mcp/server.py`); the local model stays the per-attempt evaluator.

Run (needs the `mcp` extra and DB access):

```powershell
cd C:\Users\badmaev_es\egeMentor\backend
.venv312\Scripts\python.exe -m pip install -e .[mcp]
.venv312\Scripts\python.exe -m app.adapters.mcp.server
```

Connect from Claude Code: `claude mcp add ege -- <python> -m app.adapters.mcp.server` (run with cwd `backend/`). Codex: add the same stdio command to its MCP config.

Tools — read: `student_overview`, `program_progress`, `topic_lifecycle`, `diagnostics`, `error_journal`, `attempt_history`, `reviews`, `manual_reviews`, `list_tasks`. Write (provenance-tagged): `create_mission`, `update_mission`, `add_task` (lands as DRAFT), `approve_task`, `record_score_event`, `record_review_result`. Only APPROVED bank tasks reach missions; answer keys are never sent to the student. Note: during a session the student's data goes to the agent's provider — use with guardian consent.

## Useful References

- `README.md`
- `docs/REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/PRODUCT_DECISIONS.md`
- `backend/app/domain/policies.py`
- `backend/app/application/use_cases.py`
- `scripts/preview_tracker.py`

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- The installed `post-commit` hook updates graphify automatically in the background.
  Do not run `graphify update .` manually after normal code changes; only investigate or
  rebuild manually when the hook reports a failure or the graph is demonstrably stale.
