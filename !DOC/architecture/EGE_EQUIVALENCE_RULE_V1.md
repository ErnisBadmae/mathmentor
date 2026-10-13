# EGE task equivalence rule v1

Rule id: `ege-equivalence-v1`
Status: **draft — requires the tutor's approval before any real cycle is measured**
Consumed by: `backend/scripts/export_measurement_cycles.py`
Contract: `../../../measurement/RECORD_CONTRACT_V0.md`

## Why this document exists

The measurement instrument asks whether the learner solved an **unseen equivalent
task** days after training. Everything rests on the word *equivalent*. The
instrument records equivalence evidence; it does not invent it. This document is
the invented part, and it is a human decision, not a heuristic.

## The rule

> Two EGE tasks are equivalent for measurement when all of the following hold:
>
> 1. same `subject`;
> 2. same `topic_id`;
> 3. same official `task_number` (the EGE position number);
> 4. both are `APPROVED` bank tasks;
> 5. the missions carrying them declare the same `threshold_percent`;
> 6. they are different `task_id`s;
> 7. neither was attempted by this learner before its phase.

Rationale for (3): within one EGE task number the official format, the scoring
scheme and the difficulty band are fixed by the exam itself. Across numbers they
are not — task 10 and task 15 of profile mathematics are not interchangeable even
inside one topic. The exam gives us an externally defined difficulty band for
free; nothing else in this product does.

The exporter writes the rule id into every record:

```text
task_family = "ege-equivalence-v1:{subject}:{topic_id}:{task_number}"
```

A cycle whose phases disagree on any component comes out `not_equivalent` in the
report. It is counted, not silently dropped.

## Phase mapping in this product

| Contract phase | EGE reality |
| --- | --- |
| `baseline` | the learner's **first** attempt on the topic — the product rule is attempt first, AI second, so the first attempt is cold with respect to this system's instruction |
| `immediate` | the attempt whose evidence **closed** the topic and scheduled the review cards |
| `delayed_transfer` | the review drill, `mission.source_ref = daily:review:<review_id>`, which the daily builder assembles from a **fresh, never-assigned** task of the topic |

One cycle = one review card. `cycle_id = "ege:<review_id>"`. The +7 and +30 cards
of the same evidence produce two cycles sharing a baseline and an immediate; only
+7 is inside the primary window.

## What v1 deliberately does not claim

**`topic_check` is not used as a baseline in v1.** The slice path
(`LearningService.record_slice`) cannot satisfy the exporter obligations, for
three reasons in the code rather than in opinion:

1. `study_log_entries` has **no `topic_id`**. The competency link is the string
   `f"Срез — {label}"`, and `label` falls back to a subject name whenever the
   slice spans more than one topic. Obligation 4 — same competency — cannot be
   proven, only guessed from a formatted label.
2. A slice item carries **no threshold and no attempt mode**. Independence is
   therefore unprovable, and the instrument's mandatory fail-closed rule turns
   every such cycle into `incomplete / independence_unknown`.
3. A slice item is graded by `answer_is_correct` plus LLM equivalence; a mission
   is graded by score against `threshold_percent`. These are two instruments, and
   declaring them comparable is the tutor's call, not the exporter's.

Additionally `study_log_entries.details_json` holds answer text and feedback, so
the export path must never touch that table at all.

If the tutor later declares slice grading comparable to mission grading, that
becomes rule v2 and requires a `topic_id` on the slice record first.

## Known limitations, stated rather than hidden

- **`immediate` may reuse the baseline task.** A failed mission is repeated via
  `mark_repeat` on the same mission, so the closing attempt can be on the task the
  learner already saw. This inflates `immediate_gain` and therefore deflates
  `retention_ratio`. It does **not** affect IDTR, which reads only the delayed
  attempt. The exporter marks such phases `previously_exposed`, and the instrument
  now disqualifies a cycle exposed at any phase.
- **"Cold" means cold to this system.** A first attempt on a topic is not proof
  that the learner never met the material at school. IDTR measures retained
  transfer within the loop, not absolute novelty.
- **No critical-error concept exists in EGE today.** The exporter's
  `CRITICAL_ERROR_CATEGORIES` is empty, so `critical_error` is always `false` by
  declaration. When the tutor names critical categories — a wrong answer that
  would cost the whole task in the exam — the set is populated and history
  reinterprets itself from the same data.
- **Mentor minutes are never exported.** `AGENTS.md` forbids inferring operator
  time from database timestamps, so the field stays `null` until the manual
  operator journal supplies it.
- **Only one attempt per drill counts.** A retried review drill is not one
  independent measurement; the exporter skips it as `drill_multiple_attempts`.

## What the tutor is being asked to approve

1. Is the same `task_number` the right equivalence band, or is topic-level
   equivalence acceptable when a topic has too few tasks per number? Relaxing this
   is the single change most likely to move the cycle count from "too few" to
   "enough" — and the single change most likely to make the number meaningless.
2. Which `ErrorCategory` values, if any, are critical.
3. Whether `threshold_percent` differences between an old and a new mission should
   block a cycle, or whether a declared common threshold applies.

Until 1-3 are answered, the exporter runs with the strict rule above. A small
number of provable cycles under a strict rule is an honest result; a large number
under an invented rule is not.

## Version history

- **v1** — this document. Strict task-number equivalence, mission-based baseline,
  slice path excluded. Not yet tutor-approved.
