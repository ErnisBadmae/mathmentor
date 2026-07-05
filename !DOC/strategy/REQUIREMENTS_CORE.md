# REQUIREMENTS — EGE Mentor Family Pilot (Core)

Status: active product specification.
Date: 2026-06-16.

This document defines what the product must do. `!DOC/architecture/ARCHITECTURE.md` defines how the system is shaped, `!DOC/strategy/PRODUCT_DECISIONS.md` explains why key choices were made, and `.claude/rules/simplicity.md` limits complexity.

Split from original REQUIREMENTS.md. Details (§11-19) — [REQUIREMENTS_DETAILS.md](REQUIREMENTS_DETAILS.md).

## 1. Scope

v1: family-pilot preparation for one real student (EGE 2027).

In scope:
- Profile mathematics, informatics.
- Local LAN deployment.
- Backend-owned preparation state.
- Loop: `plan -> mission -> independent attempt -> evidence -> review -> next mission`.
- Import from local EGE corpus tracker.
- Guardian/operator manual control where automation is unsafe.

Out of scope:
- Public SaaS, payments, vector/graph DB, queues, LangGraph, autonomous routing.
- Voice, bulk Obsidian import, Russian language as active track.

The student is a minor. Defaults: LAN/private use, no unnecessary external data transfer, explicit guardian access.

## 2. Source Corpus

Canonical import: `контроль\трекер_ЕГЭ-финал.xlsx`.

Markdown/Docx define requirements and planning rules, not DB rows:
- June plan (daily loop, 8/10 rule, AI restrictions)
- July-August plan (weekly control sets, Slice 2/3)
- Year program v2 (+7/+30 repetition, admin calendar)
- Weekly audit sample, admin calendar, history of first slices
- Math error analysis (arithmetic, sign transfer, ODZ logic)
- Informatics resources, probability remediation

## 3. Actors

`STUDENT`: submits attempts, completes reviews. Does not edit coaching logic, missions, or review decisions.

`GUARDIAN` / `OPERATOR`: creates/edits missions, records scores, resolves manual reviews. In v1 behaviorally equivalent. LAN deployment uses one shared token; per-role auth is out of v1 scope.

`LLM reviewer`: bounded evaluator — scores, classifies errors, produces feedback. Cannot move exam score, close topics, schedule reviews, or choose next mission.

`TUTOR`: future role for expert review. Not in v1.

## 4. Core Loop

```text
plan -> mission -> independent attempt -> evidence -> review -> next mission
```

Invariants:
- Attempt first, AI second. Math: answer + reasoning before AI. Code: write/run locally first (Thonny preferred).
- AI feedback only after independent attempt.
- Frontend renders backend state; no separate coaching rules.
- PostgreSQL is canonical source of truth.
- Evidence is append-only. Manual review creates new evidence record.

`plan` is human-owned in v1. Manual mission creation is priority 1 — without it, starter missions run out and the loop stops.

## 5. Entities

- `student_profile`: the family pilot student.
- `subject_track`: current/target exam score by subject. `current_score` moved only by score events.
- `topic`: learning unit, often mapped to EGE task number/type. Lifecycle computed from missions/evidence/reviews. Optional `phase`/`program_order` links to program phase (§17a).
- `task`: vetted bank item — statement + `expected_answer` (+ optional `solution`), with `status` (draft/approved), provenance, optional `topic`. Only approved tasks in missions. Answer key never exposed.
- `mission`: concrete assignment — one task, small review block, or daily practice set (~10 tasks). References bank `task` by `task_id`.
- `attempt`: one submitted attempt. Append-only.
- `evidence`: one review result for an attempt. Append-only, carries `model_id`, `prompt_version`, `rubric_version`.
- `error_event`: one categorized mistake. Append-only.
- `review_item`: spaced review card for +7/+30 repetition.
- `score_event`: objective exam-like score signal.
- `clean_sheet_event`: imported aggregate clean-sheet baseline.
- `study_log_entry`: imported daily log row.
- `audit_set`: future weekly cold control set. Table exists, lifecycle not yet product-supported.

## 6. Mission State

Statuses: `ACTIVE` (visible today), `REPEAT` (visible after failed/manual-failed), `DONE` (passed evidence or manual pass).

Transitions:
```text
ACTIVE -> DONE     on evidence PASSED
ACTIVE -> REPEAT   on evidence FAILED
REPEAT -> DONE     on evidence PASSED
REPEAT -> REPEAT   on evidence FAILED
```

`NEEDS_MANUAL_REVIEW` does not change mission status. `PLANNED` removed (unused). `SKIPPED` retained for dedup, not exposed in UI.

## 7. Evidence State

- `PASSED`: crossed threshold or guardian accepted.
- `FAILED`: did not cross threshold or guardian rejected.
- `NEEDS_MANUAL_REVIEW`: saved, but auto-review unsafe/unavailable.

Evidence is immutable. Resolution of `NEEDS_MANUAL_REVIEW`: new evidence with `PASSED` or `FAILED`, `model_id="manual-review"`. Target `NEEDS_MANUAL_REVIEW` via manual decision returns 400.

Effects:
- `PASSED` → closes mission, moves topic to provisional review.
- `FAILED` → mission `REPEAT`, creates `error_event` if `error_category != NONE`.
- `NEEDS_MANUAL_REVIEW` → no closure, no reviews scheduled, no score moved, no error events.

## 8. Review State

- `DUE`: waiting. `DONE`: passed. `BACK_TO_WORK`: failed, creates new work.

```text
DUE -> DONE          if review passed
DUE -> BACK_TO_WORK  if review failed
BACK_TO_WORK -> consumed by creating new ACTIVE mission for same topic
```

`BACK_TO_WORK` must not be terminal. Failed review creates new `ACTIVE` mission with defaults: copied student_id, subject, topic_id, status=`ACTIVE`, ai_policy=`ATTEMPT_FIRST`, threshold=`80`, due_date=`LOCAL_TIMEZONE` today, title=`Повтор: {topic}`, instructions=`2-3 холодные задачи...`.

## 9. Topic Lifecycle

Computed, not stored in v1:
- `open`: no recent passed mission.
- `in_work`: active/repeat mission exists.
- `under_review`: passed mission + scheduled +7/+30 reviews not both done.
- `confirmed`: passed evidence + both reviews done.
- `back_to_work`: latest review failed or new mission after failed review.

Rules: one passed mission ≠ fully closed. Confirmed only after spaced review succeeds. Failed review sends back to work via new mission. Cold audits can override confidence.

## 10. Daily Work Rules

Summer: ~4 hours/day, 6 days/week, Sunday off. Blocks: math, informatics, programming, closure (error journal + notes).

Closure: 8/10 correct → topic closed. Below 8/10 → same topic repeats, new topic does not start. Better to close one firmly than skim three.

V1: one daily topic = one mission (practice set of ~10 tasks, not 10 missions).
- `instructions`: `10 задач по теме ...`
- Student submits one attempt for the set
- Score: `tasks_total`, `tasks_correct`, `score_percent = correct/total * 100`
- Default threshold `80` (matches 8/10)
- `tasks_total=10, tasks_correct>=8` → `PASSED`; below → `FAILED`, mission `REPEAT`

Until `tasks_total`/`tasks_correct` are first-class API fields, preserve in evidence feedback/details. Next wave: add first-class fields.

Single-task missions: explicit threshold (usually `100` for exact answers).

Date boundary: store timestamps in UTC. Compute "today", closure, logs, due reviews by `LOCAL_TIMEZONE`. Late-evening local attempt → local calendar day.
