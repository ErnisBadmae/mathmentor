# Product Decisions

## v1 scope

- Audience: family pilot.
- Subjects: profile mathematics and informatics.
- Interface: website first, Telegram bot for reminders and reports.
- Access: invite codes and roles.
- AI policy: independent attempt first; AI feedback only after the attempt.
- First production target: local LAN, protected by a shared API token.
- Russian is documented in source planning materials, but remains out of v1 product scope.

## Initial observed state

Imported from the local EGE materials:

- Target: 85/85 in June 2027.
- Current rough baseline: profile math 65, informatics 50.
- Programming clean-sheet ratio: 0.4.
- Current leading error types: arithmetic/sign transfer, ODZ logic, condition reading, probability double count.

## Coaching loop

A topic is not closed because time was spent. It is closed when evidence crosses the configured threshold. Closed topics are scheduled for spaced review at +7 and +30 days.

## Score policy

`subject_tracks.current_score` represents the latest objective score signal: weekly variant, slice, or manual score event. Daily missions and topic evidence do not change it. This keeps the dashboard from inventing exam-score progress from practice tasks.

## Review policy

The production reviewer is OpenAI-compatible. If LLM review is disabled, unavailable, or fails schema validation, the attempt is saved as `needs_manual_review` and does not close the topic. Manual review creates a new evidence record instead of mutating the raw evidence.
