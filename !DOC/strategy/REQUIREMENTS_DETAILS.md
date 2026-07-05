# REQUIREMENTS — EGE Mentor Family Pilot (Details)

Status: active product specification.
Date: 2026-06-16.

Details (§11-19). Core (§1-10) — [REQUIREMENTS_CORE.md](REQUIREMENTS_CORE.md).

## 11. Score Rules

`subject_tracks.current_score` = latest objective exam-score signal.

| Source | Moves `current_score` | Notes |
|---|---:|---|
| Baseline score event | yes | Initial 65/50 |
| Weekly full variant | yes | Objective timed result |
| Exam-like control cut | yes | Timed estimate of exam score |
| Topic diagnostic check | no | Technique/topic checks |
| Manual guardian score | yes | Explicit override |
| Daily attempt | no | Practice ≠ exam score |
| Evidence `PASSED` | no | Closes mission/topic, not score |
| Review result | no | Confirms retention, not score |

Newest-by-`occurred_on`, not last row written. Backfilled events must not regress score.

Terminology:
- `exam_variant`: full timed variant → moves score.
- `exam_like_slice`: timed control cut → moves score.
- `topic_check`: diagnostic/narrow skill → evidence/error/review only.

Historical Slice 1-4 are mostly topic diagnostics — do not auto-update `current_score` unless guardian explicitly marks as exam-like.

## 12. Clean-Sheet Rules

Leading indicator for programming independence.

| Attempt | Clean numerator | Total |
|---|---:|---:|
| `CODE` + `CLEAN_SHEET` + `PASSED` | yes | yes |
| `CODE` + `CLEAN_SHEET` + `FAILED` | no | yes |
| `CODE` + `WITH_HINT` | no | yes |
| Non-code | no | no |

Rules:
- Hinted code never improves ratio.
- AI/internet/solution/adult-help before solving → not clean-sheet.
- Clean-sheet code in weekly audit = critical path. Failing it > ordinary single-task miss.
- Imported baseline `2/5 = 0.4` is epoch-0. Dashboard: cumulative + recent-window (30 days).
- Live source: code attempts. `clean_sheet_event` not auto-appended. Future aggregate-input UI needed.

## 13. Weekly Audit Rules

Detect familiar-task illusion.

Conditions: No AI, no internet, no phone, no crib sheet, timed, math on paper, code in Thonny/local. Guardian checks by answer key (no expert grading for v1).

Default format:
- Math: 90 min. Target: ≥4/5 first tasks correct + one Part 2 carried correctly.
- Informatics: 60 min. Target: ≥3/4 correct + clean-sheet code solved independently.

Results:
- Create error events for misses.
- Score event only if marked `exam_variant` or `exam_like_slice`.
- Topic diagnostics → evidence/error/review, no score movement.
- Update clean-sheet for code tasks.
- Feed next week's plan via leading error categories.

`AuditSetORM`: data structure without lifecycle yet. Define API/UI before implementation.

## 14. LLM And Error Rules

LLM may: assign `score_percent`, classify `error_category`, produce `feedback`, produce `next_action`.

LLM must not: close topics, move `current_score`, schedule reviews, improve clean-sheet, choose next mission.

If LLM disabled/invalid → `NEEDS_MANUAL_REVIEW`.

Golden error examples (require regression fixtures):
- Probability double count: used `P(A)` instead of `P(only A)`.
- Arithmetic transfer: `2x - 1 = 9` → `2x = 8`.
- Sign transfer: moved terms without sign change → `-4` instead of `4`.
- Condition reading: solved correctly, wrong requested root.
- ODZ logic: rejected all roots when only one violated denominator.
- Code syntax/runtime mistake.
- Code algorithm: wrong loop/condition/aggregation/complexity.

Changing model/prompt/rubric → replay golden examples before trusting.

## 15. AI Policy

v1: `ATTEMPT_FIRST` only. Student attempts first → AI/reviewer feedback after submission. Reviewer output is evidence, not coaching authority. `BLOCKED` and `ALLOWED_AFTER_ATTEMPT` removed (unused).

## 16. Import Mapping

| Source sheet | Canonical records |
|---|---|
| `Дашборд` | subject tracks, baseline scores |
| `Дневной лог` | study log entries |
| `Журнал ошибок` | error events |
| `Чистый лист` | clean-sheet events |
| `Повторение` | review items |
| `Варианты` | score events |

Requirements: idempotent by `source_ref`; preserve `source_file/sheet/row`; no raw Markdown prose into DB; informational rows must not overwrite score; re-runs must not duplicate.

## 17. Admin Calendar

External checklist, not a DB entity or mission source. May later become reminders.

Hard reminders:
- Aug 2026: FIPI EGE 2027 demo → verify numbering/mapping.
- Dec 2026: final essay as admission requirement.
- By Feb 1, 2027: submit EGE application.
- Apr-May 2027: confirm schedule, locations, travel.

Monthly check: upcoming deadlines, `Повторение` queue maintained, school load not consuming preparation.

External calibration: Dec 2026 mock, Mar 2027 mock. If external << home, tighten home conditions.

## 17a. Program Phases And Controller View

Fixed phase metadata in code (`app/domain/program.py`), not a DB table. Each topic carries optional `phase`/`program_order`. June/July-August seeded granularly (Slice 1/2/3); later phases (Sept-May) coarse milestones.

Controller view: computed topic lifecycle (§9) on program topics, grouped by phase, with coverage and per-topic progress. Diagnostics surfaced from `study_log_entry`. Student never sees task answer keys.

## 17b. Implementation Status (2026-06-17)

Implemented: local LLM reviewer with provider switch, constrained decoding + fail-closed manual review; golden replay gate for error classification; task bank with approval/provenance; computed topic lifecycle with failed-review → new ACTIVE mission; program/controller view; slice diagnostics; §11 newest-by-`occurred_on` score rule.

Open P1: first-class `tasks_total`/`tasks_correct` (§10); guardian mission-create/score-event UI on frontend (§19); golden error fixtures as in-suite regression.

## 18. Acceptance Tests

Each accepted state transition needs a regression test.

Existing: seed 65/50/0.4; passed → DONE + reviews; passed ≠ score update; failed → REPEAT + error; hinted code ≠ clean-sheet improvement; rule-based → NEEDS_MANUAL_REVIEW; missing mission 404; idempotent importer; dashboard ≠ score overwrite.

Required next:
- Practice-set: `tasks_total=10, tasks_correct=8` → `score_percent=80`.
- Practice-set `7/10` → fail, remain/re-enter repeat.
- Single-task explicit threshold ≠ 8/10 forced.
- Manual `PASSED`/`FAILED` mirror attempt behavior.
- Manual target `NEEDS_MANUAL_REVIEW` → 400.
- `NEEDS_MANUAL_REVIEW` leaves mission/topic unchanged.
- Review pass → DONE; review fail → BACK_TO_WORK + new ACTIVE mission.
- Topic states: `under_review`, `confirmed`, `back_to_work`.
- Score: newer updates, older doesn't regress, diagnostics don't update, exam variants do.
- Clean-sheet: passed improves num+den, failed improves den only, hinted improves den only.
- LLM schema failure → NEEDS_MANUAL_REVIEW.
- Golden examples classify correctly.
- Weekly audit with AI/internet/phone/crib not accepted; failed clean-sheet = critical signal.

## 19. Implementation Backlog

Priority 1:
- Guardian/operator mission create/edit UI (v1 cannot depend on seed).
- Daily practice-set scoring: `tasks_total` + `tasks_correct`, default 8/10.
- Consume `BACK_TO_WORK` → new ACTIVE mission for same topic.
- Computed topic lifecycle query.
- Latest-by-date score event behavior.
- Manual review transition tests.
- Golden error-category fixtures.

Priority 2:
- Score-event UI (weekly variants, control cuts).
- Weekly audit lifecycle.
- Recent-window clean-sheet metric.
- Admin reminder surface.

Priority 3:
- Unsupported enum: behavior or remove.
- Russian track after separate requirements pass.
- Import Markdown planning structures after explicit mapping.
