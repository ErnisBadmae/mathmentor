# REQUIREMENTS — EGE Mentor Family Pilot

Status: active product specification.
Date: 2026-06-16.

This document defines what the product must do. `docs/ARCHITECTURE.md` defines how the system is shaped, `docs/PRODUCT_DECISIONS.md` explains why key choices were made, and `.claude/rules/simplicity.md` limits how much complexity may be added.

## 1. Scope

EGE Mentor v1 is a family-pilot preparation system for one real student preparing for EGE 2027.

In v1 scope:

- Profile mathematics.
- Informatics.
- Local LAN deployment.
- Backend-owned preparation state.
- The loop: `plan -> mission -> independent attempt -> evidence -> review -> next mission`.
- Importing current tracker data from the local EGE corpus.
- Guardian/operator manual control where automation is unsafe.

Out of v1 scope:

- Public SaaS onboarding.
- Payments.
- Vector DB, graph DB, queues, CDC, LangGraph, autonomous routing.
- Voice.
- Bulk import of the whole Obsidian Markdown corpus into canonical DB state.
- Russian language as an active product track.

Russian language is roadmap-only for now. The corpus contains Russian-language planning materials, diagnostics and administrative deadlines, but v1 product behavior remains limited to profile mathematics and informatics.

The student is a minor. Product defaults must assume LAN/private use, no unnecessary external data transfer, and explicit guardian access.

## 2. Source Corpus

Studied source corpus at `C:\Users\badmaev_es\Desktop\ЕГЭ`:

- `контроль\трекер_ЕГЭ-финал.xlsx`: current operational tracker and canonical v1 import source.
- `контроль\План июня — подготовка к ЕГЭ (математика + информатика).md`: daily loop, 8/10 closure rule, AI/code restrictions, June Slice 1 criteria.
- `контроль\План июль–август + глобальная картина лета.md`: summer arc, weekly control sets, audit generation rules, Slice 2/3 criteria.
- `контроль\Годовая программа v2 (июнь 2026 — июнь 2027).md`: year arc, +7/+30 repetition tab, admin calendar, Russian as roadmap track.
- `контроль\Контрольный набор — июль, неделя 1 (образец).md`: weekly audit conditions and pass threshold.
- `контроль\админ_календарь_чеклист.md.docx`: hard administrative deadlines and monthly check rules.
- `срезы знаний\история первых срезов.md`: observed errors, slice results, tracker recording rules, probability double-count case.
- `срезы знаний\Срез №4 — уравнения и неравенства (математика).md`: real error categories: arithmetic, sign transfer, condition reading, ODZ logic.
- `материалы подготоки\Бесплатные материалы для подготовки к ЕГЭ по информатике.md`: resource policy, Stepik/Poleakov/Thonny flow, code attempt-first rule.
- `материалы подготоки\теорвер пошагово.md`: targeted remediation example for probability double count.
- `материалы подготоки\Русский язык план и бесплатные материалы.md`: roadmap context only.

Only the Excel tracker is a canonical import source in v1. Markdown/Docx documents define requirements and future planning rules, not DB rows.

## 3. Actors

`STUDENT`: submits attempts and completes reviews. The student does not edit coaching logic, missions, score events, or review decisions.

`GUARDIAN` / `OPERATOR`: creates and edits missions, records score events, resolves manual reviews, marks review results, and checks audits. In v1 these roles are behaviorally equivalent.

Role separation in v1 is a product convention, not security enforcement. The current LAN deployment uses one shared `X-EGE-MENTOR-TOKEN`; anyone with that token can call protected endpoints. Per-role authorization is out of v1 scope until there is a real multi-user need.

`LLM reviewer`: bounded evaluator. It can score an attempt, classify an error, and produce feedback. It cannot move exam score, close topics, schedule reviews, or choose the next mission.

`TUTOR`: future role for hard-tail expert review. Not in v1 behavior.

## 4. Core Loop

The product loop is:

```text
plan -> mission -> independent attempt -> evidence -> review -> next mission
```

Invariants:

- Attempt first, AI second.
- Math: the student submits answer and reasoning/photo/text before any AI explanation.
- Code: the student writes and runs code locally first, preferably in Thonny, then submits code/answer for feedback.
- AI feedback is allowed only after an independent attempt.
- Frontend renders backend state and must not implement separate coaching rules.
- PostgreSQL is the canonical source of truth.
- Evidence is append-only. Manual review creates a new evidence record.

In v1, `plan` is human-owned. Guardian/operator reads the weekly plan, tracker, error journal and review queue, then creates missions manually. Automatic mission planning from errors/audits is future scope.

Manual mission creation is priority 1 product capability, not a later nice-to-have. Without it, the seeded starter missions run out and the core loop stops.

## 5. Entities

`student_profile`: the student in the family pilot.

`subject_track`: current and target exam score by subject. `current_score` is moved only by score events.

`topic`: a learning unit, often mapped to an EGE task number or type. Topic lifecycle is computed from missions, evidence and reviews; no stored topic status is required for v1. Implemented: a topic also carries an optional `phase`/`program_order` linking it to a program phase (see §17a).

`task`: a vetted item in the task bank — statement + `expected_answer` (+ optional `solution`), with `status` (`draft`/`approved`), provenance (`source`, `model_id`, `prompt_version`, `source_ref`) and an optional `topic`. Only `approved` tasks may be referenced by missions. A senior LLM may author tasks offline into `draft`; missions/grading never see unapproved tasks. The answer key is never exposed to the student.

`mission`: a concrete assignment to the student. A mission can represent one task, a small review block, or a daily practice set. The standard daily topic mission represents one practice set, usually 10 tasks, not 10 separate missions. A mission may reference a bank `task` (`task_id`); its statement and answer key then come from the task.

`attempt`: one submitted attempt. Append-only.

`evidence`: one review result for an attempt. Append-only and carries provenance: `model_id`, `prompt_version`, `rubric_version`.

`error_event`: one categorized mistake in the journal. Append-only.

`review_item`: spaced review card for +7/+30 repetition.

`score_event`: objective exam-like score signal: baseline, weekly full variant, exam-like control cut, or manual guardian score.

`clean_sheet_event`: imported aggregate clean-sheet baseline. Future aggregate clean-sheet observations require explicit guardian/operator input UI; live per-task clean-sheet is derived from code attempts.

`study_log_entry`: imported daily log row.

`audit_set`: future weekly cold control set. The table exists, but lifecycle is not product-supported until the audit use case is implemented.

## 6. Mission State

Supported v1 mission statuses:

- `ACTIVE`: visible in today's missions.
- `REPEAT`: visible in today's missions after a failed attempt or manual failed decision.
- `DONE`: mission completed by passed evidence or manual passed decision.

Target transitions:

```text
ACTIVE -> DONE     on evidence PASSED
ACTIVE -> REPEAT   on evidence FAILED
REPEAT -> DONE     on evidence PASSED
REPEAT -> REPEAT   on evidence FAILED
```

`NEEDS_MANUAL_REVIEW` does not change mission status.

`PLANNED` was removed (unused). `SKIPPED` is retained and used to retire duplicate missions during seed/dedup; it is not part of the student-facing flow and must not be exposed in operator UI as a transition target.

## 7. Evidence State

Evidence statuses:

- `PASSED`: attempt crossed the mission threshold or guardian accepted it.
- `FAILED`: attempt did not cross the threshold or guardian rejected it.
- `NEEDS_MANUAL_REVIEW`: attempt was saved, but automatic review is unsafe or unavailable.

Evidence is immutable. The only valid resolution of `NEEDS_MANUAL_REVIEW` is a new evidence record with `PASSED` or `FAILED` and `model_id="manual-review"`.

Effects:

- `PASSED` closes the mission and moves the topic into provisional review state.
- `FAILED` marks mission `REPEAT` and creates an `error_event` if `error_category != NONE`.
- `NEEDS_MANUAL_REVIEW` does not close mission, does not schedule reviews, does not move score, and does not create error events.

Manual decision with `NEEDS_MANUAL_REVIEW` as the target status is invalid and must return 400.

## 8. Review State

Review statuses:

- `DUE`: spaced review is waiting.
- `DONE`: review was passed.
- `BACK_TO_WORK`: review was failed and must create new work.

Target transitions:

```text
DUE -> DONE          if review passed
DUE -> BACK_TO_WORK  if review failed
BACK_TO_WORK -> consumed by creating a new ACTIVE mission for the same topic
```

`BACK_TO_WORK` must not be terminal. A failed review creates a new `ACTIVE` mission for the same `topic_id`, preserving history instead of reopening an old `DONE` mission.

Auto-created `BACK_TO_WORK` mission defaults:

- `student_id`: copied from the failed review item.
- `subject`: copied from the topic.
- `topic_id`: copied from the failed review item.
- `status`: `ACTIVE`.
- `ai_policy`: copied from the latest mission for the topic; if none exists, use `ATTEMPT_FIRST`.
- `threshold_percent`: copied from the latest mission for the topic; if none exists, use `80`.
- `due_date`: local today in `LOCAL_TIMEZONE`.
- `title`: `Повтор: {topic_title}` if topic title exists, otherwise `Повтор темы`.
- `instructions`: `2-3 холодные задачи по теме без ИИ и шпаргалки. Причина: провален возврат.`

If the failed review came from imported tracker data and there is no previous mission for the topic, these defaults are sufficient; the transition must not fail because of missing title/instructions.

## 9. Topic Lifecycle

Topic lifecycle is computed, not stored in v1.

Computed topic states:

- `open`: no recent passed mission for the topic.
- `in_work`: at least one active/repeat mission exists for the topic.
- `under_review`: a mission for the topic was passed and +7/+30 review items exist, but required reviews are not both done.
- `confirmed`: the topic has passed mission evidence and both +7/+30 reviews are done.
- `back_to_work`: latest review failed or an active mission was created after failed review.

Rules:

- One passed mission does not mean the topic is fully closed.
- Passed mission means provisional closure and schedules +7/+30 reviews.
- A topic is confirmed only after spaced review succeeds.
- Failed +7 or +30 review sends the topic back into work via a new mission.
- Cold weekly audits can override confidence: if a confirmed topic fails cold audit, it should produce a new mission or error-driven work item.

## 10. Daily Work Rules

From the June plan:

- Daily budget in summer is about 4 hours, 6 days per week, Sunday off.
- Daily blocks: profile math, informatics without code, programming, day closure.
- Day closure includes error journal and personal notes.
- A daily topic is considered closed when the student gets at least 8 correct out of 10.
- If below 8/10, the same topic repeats; a new topic should not start.
- It is better to close one topic firmly than to skim three topics halfway.

V1 decision: one daily topic closure unit is one mission representing the whole practice set. Do not model the 10 tasks as 10 separate missions.

Standard daily practice-set mission:

- `instructions` states the task count and source, for example `10 задач по теме ...`.
- Student submits one attempt for the set.
- Guardian/operator or reviewer records `tasks_total`, `tasks_correct`, and resulting `score_percent = tasks_correct / tasks_total * 100`.
- Default threshold is `80`, matching 8/10.
- If `tasks_correct >= 8` for `tasks_total = 10`, the evidence is `PASSED`.
- If below threshold, evidence is `FAILED`, the mission becomes `REPEAT`, and the next day keeps the same topic.

Until `tasks_total` and `tasks_correct` are first-class fields in the API/schema, they must be preserved in evidence feedback/details or study-log provenance. The next implementation wave should add first-class fields rather than leaving the raw counts as prose.

Single-task missions remain valid. For a single-task mission, use an explicit threshold appropriate to the task, usually `100` for exact-answer checks or manual review for complex reasoning.

Daily date boundary:

- Store attempt/evidence timestamps in UTC.
- Compute "today", daily closure, daily logs, due review visibility, and 8/10 grouping by `LOCAL_TIMEZONE`.
- A late-evening local attempt belongs to the local calendar day, even if UTC date has already changed.

## 11. Score Rules

`subject_tracks.current_score` represents the latest objective exam-score signal.

Sources that move `current_score`:

| Source | Moves `current_score` | Notes |
|---|---:|---|
| Baseline score event | yes | Initial 65/50 state. |
| Weekly full variant | yes | Objective timed exam-like result. |
| Exam-like control cut | yes | Timed result intended to estimate exam score. |
| Topic diagnostic check | no | Technique/topic checks such as sign transfer, ODZ, condition reading. |
| Manual guardian score event | yes | Explicit override or correction. |
| Daily attempt | no | Practice is not exam score. |
| Evidence `PASSED` | no | It closes mission/topic work, not exam score. |
| Review result | no | It confirms retention, not score. |

When multiple score events exist, `current_score` should reflect the newest event by `occurred_on`, not the last row written. Backfilled older events must not regress current score.

Terminology:

- `exam_variant`: full timed variant or close equivalent; moves `current_score`.
- `exam_like_slice`: timed control cut designed to estimate exam score; moves `current_score`.
- `topic_check`: diagnostic or targeted slice for a narrow skill; creates evidence/error events/review work, but does not move `current_score`.

The historical Slice 1-4 materials in the current corpus are mostly topic diagnostics. They should not automatically update `current_score` unless guardian explicitly records them as exam-like score events.

## 12. Clean-Sheet Rules

Clean-sheet is a leading indicator for programming independence.

| Attempt condition | Clean numerator | Total denominator |
|---|---:|---:|
| `CODE` + `CLEAN_SHEET` + `PASSED` | yes | yes |
| `CODE` + `CLEAN_SHEET` + `FAILED` | no | yes |
| `CODE` + `WITH_HINT` | no | yes |
| Non-code attempt | no | no |

Rules:

- Hinted code never improves clean-sheet ratio.
- If the student used AI, internet, a solution, or direct adult help before solving, the attempt is not clean-sheet.
- A clean-sheet code task in weekly audit is critical path. Failing it is more important than an ordinary single-task miss.
- Imported baseline `2/5 = 0.4` is epoch-0 history. Long-term dashboard should show both cumulative clean-sheet and recent-window clean-sheet, preferably last 30 days.

Live v1 source of clean-sheet data is code attempts. `clean_sheet_event` is not automatically appended during normal student work. New aggregate `clean_sheet_event` rows require a future guardian/operator aggregate-input UI; until then, do not build product behavior that assumes fresh aggregate rows exist.

## 13. Weekly Audit Rules

Purpose: detect familiar-task illusion.

Audit conditions:

- No AI.
- No internet.
- No phone.
- No crib sheet.
- Timed.
- Math on paper.
- Code in Thonny/local environment.
- Guardian checks by answer key; no expert grading required for v1.

Default weekly audit format from the corpus:

- Math: 90 minutes.
- Informatics: 60 minutes.
- One code task must be solved clean-sheet.
- Math target: at least 4 of 5 first tasks correct and at least one Part 2 task carried to correct answer.
- Informatics target: at least 3 of 4 correct, and the clean-sheet code task must be solved independently.

Audit results:

- Should create error events for misses.
- May create a score event only if the audit is explicitly marked as `exam_variant` or `exam_like_slice`.
- Topic diagnostics and narrow technique checks create evidence/error/review work, but do not move `current_score`.
- Must update clean-sheet observations for code tasks.
- Should feed next week's mission plan through the leading error category and failed topics.

`AuditSetORM` is currently a data structure without product lifecycle. Before implementation, define API/UI for creating, delivering, checking, and consuming an audit set.

## 14. LLM And Error Rules

LLM may:

- assign `score_percent`;
- classify `error_category`;
- produce `feedback`;
- produce `next_action`.

LLM must not:

- close topics;
- move `current_score`;
- schedule reviews;
- improve clean-sheet;
- choose the next mission directly.

If LLM is disabled, unavailable, or returns invalid schema, the attempt is saved as `NEEDS_MANUAL_REVIEW`.

Error categories used in dashboard and next-mission planning require regression fixtures. Golden examples from the corpus:

- Probability double count: used `P(A)` instead of `P(only A)` and counted intersection twice.
- Arithmetic transfer: from `2x - 1 = 9` got `2x = 8`.
- Sign transfer: moved terms without changing signs, got `-4` instead of `4`.
- Condition reading: solved correctly but returned the wrong requested root.
- ODZ logic: rejected all roots when only one root violated the denominator restriction.
- Code syntax: Python syntax/runtime mistake.
- Code algorithm: wrong loop, condition, aggregation, file parsing, or complexity.

Changing model, prompt, or rubric version must not happen silently. The golden examples should be replayed before trusting new classifications.

## 15. AI Policy

v1 supported behavior is `ATTEMPT_FIRST`.

Meaning:

- Student attempts first.
- AI or reviewer feedback happens only after submission.
- Reviewer output is evidence, not coaching authority.

`BLOCKED` and `ALLOWED_AFTER_ATTEMPT` were removed (unused) per `.claude/rules/simplicity.md`. `ATTEMPT_FIRST` is the only `AiPolicy`.

## 16. Import Mapping

Excel tracker mapping:

| Source sheet | Canonical records |
|---|---|
| `Дашборд` | subject tracks, baseline score signals |
| `Дневной лог` | study log entries |
| `Журнал ошибок` | error events |
| `Чистый лист` | clean-sheet events |
| `Повторение` | review items |
| `Варианты` | score events |

Importer requirements:

- Idempotent by `source_ref`.
- Preserve `source_file`, `source_sheet`, `source_row` where practical.
- Do not import non-canonical prose from Markdown into DB without an explicit mapping.
- Do not let informational dashboard rows overwrite subject score.
- Re-running import must not duplicate rows.

## 17. Admin Calendar Requirements

Admin calendar is operational context, not learning-state logic.

V1 decision: admin calendar remains an external checklist/documentation item. It is not a DB entity, not a mission source, and not part of topic progression. It may later become reminders, but that is future scope.

Hard reminders:

- August 2026: FIPI EGE 2027 demo appears; verify task numbering and topic mapping.
- Start of December 2026: final essay as EGE admission requirement.
- By February 1, 2027: submit EGE application through school for Russian, profile math, informatics.
- April-May 2027: confirm exam schedule, locations, and travel plan.

Monthly check:

- Review upcoming hard deadlines.
- Check that the `Повторение` tab / review queue is maintained.
- Check that school load is not consuming the preparation track.

External calibration:

- December 2026: external mock exam.
- March 2027: external mock exam.
- If external result is much lower than home variants, home conditions are too soft and must be tightened.

## 17a. Program Phases And Controller View

The prep program from `контроль` is modelled as fixed phase metadata in code (`app/domain/program.py`: key, label, date window, order), not a DB table. Each program `topic` carries an optional `phase`/`program_order`. June and July–August are seeded granularly (Slice 1/2/3); later phases (Sept–May) are coarse milestones without topics.

The controller view overlays the computed topic lifecycle (§9) on program topics, grouped by phase, with coverage (confirmed/in_progress/open/total), a phase percent, and per-topic progress by the task bank (`solved / tasks_in_bank`, `—` when the bank has no tasks for the topic). Diagnostic slices (срезы) are surfaced from `study_log_entry` so prior work is visible. The student never sees task answer keys.

## 17b. Implementation Status (2026-06-17)

Beyond the v1 baseline, the following is implemented: local LLM reviewer with provider switch (`llama_cpp`/`vllm`) using constrained decoding + fail-closed manual review; a golden replay gate for error-category classification; task bank with approval/provenance; computed topic lifecycle (§9) including failed-review → new ACTIVE mission (§8); program/controller progress view (§17a); срез diagnostics + per-topic progress; and the §11 newest-by-`occurred_on` score rule. Still open (P1): daily practice-set first-class `tasks_total`/`tasks_correct` (§10); guardian mission-create and score-event UI on the frontend (§19); golden error fixtures as in-suite regression.

## 18. Acceptance Tests

Each accepted state transition must have a regression test before or with implementation.

Existing tests cover:

- Seed creates 65/50/0.4.
- Passed attempt marks mission `DONE` and schedules +7/+30 reviews.
- Passed attempt does not update `current_score`.
- Failed attempt marks mission `REPEAT` and records error event.
- Hinted code does not improve clean-sheet ratio.
- Rule-based fallback returns `NEEDS_MANUAL_REVIEW`.
- Missing mission maps to 404.
- Tracker importer is idempotent.
- Dashboard importer does not overwrite score from informational rows.

Required next tests:

- Daily practice-set mission stores or preserves `tasks_total=10`, `tasks_correct=8`, and produces `score_percent=80`.
- Daily practice-set mission with `7/10` fails and remains/re-enters repeat work.
- Single-task mission can use a different explicit threshold without being forced into 8/10 behavior.
- Manual decision `PASSED` behaves like passed attempt.
- Manual decision `FAILED` behaves like failed attempt.
- Manual decision target `NEEDS_MANUAL_REVIEW` returns 400.
- `NEEDS_MANUAL_REVIEW` leaves mission/topic unchanged and schedules no reviews.
- Review pass marks review `DONE`.
- Review fail marks `BACK_TO_WORK` and creates a new `ACTIVE` mission for the same topic with the default fields specified in section 8.
- Topic computed state becomes `under_review` after passed mission.
- Topic computed state becomes `confirmed` after both +7 and +30 reviews are done.
- Topic computed state returns to `back_to_work` after failed review.
- Newer score event by `occurred_on` updates `current_score`.
- Older backfilled score event does not regress `current_score`.
- Topic diagnostic checks do not update `current_score`.
- Exam-like variants/control cuts do update `current_score`.
- Clean-sheet code passed improves numerator and denominator.
- Clean-sheet code failed improves denominator only.
- Hinted code improves denominator only.
- LLM schema failure creates `NEEDS_MANUAL_REVIEW`.
- Golden examples classify into expected error categories.
- Weekly audit with AI/internet/phone/crib sheet is not accepted as clean audit.
- Weekly audit failed clean-sheet code creates a critical programming signal.

## 19. Implementation Backlog From Requirements

Do these only after this requirements document is accepted as the source of truth.

Priority 1:

- Add guardian/operator mission create/edit UI or equivalent minimal workflow; v1 cannot depend on seed missions.
- Add daily practice-set scoring: preserve `tasks_total` and `tasks_correct`, with default 8/10 threshold behavior.
- Consume `BACK_TO_WORK` by creating a new `ACTIVE` mission for the same topic.
- Add computed topic lifecycle query.
- Add latest-by-date score event behavior.
- Add manual review transition tests.
- Add golden error-category fixtures from the corpus.

Priority 2:

- Add score-event UI for weekly variants and exam-like control cuts.
- Add weekly audit lifecycle: create, deliver, check, consume.
- Add recent-window clean-sheet metric.
- Add admin reminder surface.

Priority 3:

- Decide whether unsupported enum values should get behavior or be removed.
- Add Russian as a track only after a separate requirements pass.
- Import selected Markdown-derived planning structures only after explicit mapping is defined.
