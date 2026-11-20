# Product Decisions

Last updated: 2026-10-17

## v1 scope

- Audience: family pilot.
- Subjects: profile mathematics and informatics.
- Interface: website first, Telegram bot for reminders and reports.
- Access: invite codes and roles.
- AI policy: independent attempt first; AI feedback only after the attempt.
- First production target: local LAN, protected by a shared API token.
- Russian is documented in source planning materials, but remains out of v1 product scope.

## CISIA sample practice (2026-10-09)

2026-10-17: по просьбе ребёнка добавлены 10 вопросов Logic (21–30) из того же PDF.
В `/cisia` всего 30 задач, `/logic` открывает отдельную логическую очередь. Условия
сохранены как исходные PNG, источник/раздел/номер/страница указаны, проверка по ключу.
Математический состав `/timed` сохранён; логика не меняет темы, баллы и повторы ЕГЭ.

2026-10-16: по разрешению владельца после независимого ревью добавлена отдельная
тренировка `/timed`, 5 вопросов / 10 минут, изменение ответа до общего дедлайна,
ключ после завершения, восстановление из БД. Это учебный режим, без claims об
официальном экзаменационном тайминге и без влияния на ЕГЭ. Ранее назначенные вопросы
считаются знакомыми; результаты хранятся отдельно от evidence и пока не экспортируются.
Технический контракт: `!DOC/architecture/CISIA_TIMED_PRACTICE_V1.md`.

По прямому запросу ребёнка/владельца разрешена дополнительная математическая практика
по предоставленному English TOLC-I Sample Test (2021): первые 20 вопросов в `/cisia`.
Условие сохраняется изображением оригинала; явно показываются источник, номер и страница.
Оценка только по официальному A–E ключу, без LLM и без назначения причины ошибки
по выбранной букве. Валидная попытка завершает вопрос и сохраняет evidence 1/1 или 0/1.
Миссии без topic_id не закрывают темы ЕГЭ и не назначают их повторы; sample-задачи
исключены из обычных срезов. Score events ЕГЭ не создаются. Это учебный режим,
без экзаменационных штрафов; полноценный TOLC/CEnT-S трек не объявляется.

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

## Content & trust insights (running list — add to this, don't replace)

Собрано по опыту наполнения банка задач (сессии 2026-07-16/17). Каждый пункт —
устойчивое наблюдение, а не разовый факт; усиливать через повторное наблюдение
в следующих контентных сессиях, не переписывать.

- **Провенанс контента — актив доверия, не только внутренняя гигиена.** Каждая
  задача в банке несёт `source`/`source_url` (реальный прототип ФИПИ vs
  сконструированная агентом того же формата). `GET /tasks/bank-stats` (добавлен
  2026-07-17) впервые сделал этот состав видимым: ~74% математического банка
  прослеживается до реального источника. Большинство конкурентов (AI-тьюторы,
  генераторы задач) такой прозрачности не имеют. Это конкретный, демонстрируемый
  тьютору аргумент («у каждой задачи есть паспорт») — усиливает уже принятый
  тезис про trustworthy ledger, только применённый к контенту, а не только к
  intervention-outcome данным.
- **Anti-poison verification — то же самое, но для контента.** Ответ на задачу
  никогда не берётся из LLM/веб-источника напрямую — только независимый пересчёт
  (SymPy/координаты/численный перебор). Канонический пример: веб-поиск синтезировал
  правдоподобный, но математически неверный ответ на задачу про трапецию (35
  вместо 6√35). Конкуренты, генерирующие контент через LLM без независимой
  верификации, статистически имеют такой брак — просто невидимый, пока никто не
  перепроверил вручную. Держать это правило неукоснительно при любом контентном
  расширении банка.
- **Открытые PDF-сборники прототипов — легальный и дешёвый источник контента.**
  Прямой доступ к `ege.fipi.ru`/`sdamgia.ru` заблокирован (сеть/антибот), но
  публичные компиляции прототипов (например, MathStart) доступны и разбираются
  через `fitz`/PyMuPDF (метод и рабочая ссылка — в `ACTIVE_TASK.md`). Прямое
  попадание в тезис "content is hidden COGS at scale": наполнение банка почти не
  требует репетиторского времени. Стоит проверить, есть ли аналогичные открытые
  сборники для информатики и других предметов, когда встанет вопрос контентного
  долга там.
- **Retention-алерт — не только внутренний KPI, но и демо-фича для покупателя.**
  «1/3 активных дня к среде» в `student_overview` в этой сессии оказалось точным
  описанием реального поведения ученика, не витринной цифрой. Это прямое
  попадание в интервью-пробу «сколько учеников делают домашку между уроками без
  напоминания» (см. `TUTOR_INTERVIEWS.md`) — можно показывать тьютору не как
  вопрос, а как уже работающую фичу.
- **Лёгкий операционный долг: source-лейблы контента расползлись.** `agent`,
  `agent-advanced`, `agent-july-refill`, `corpus`, `corpus_llm` — по сути пять
  разных ярлыков для «сгенерировано агентом в разное время». Не блокер сейчас;
  при дальнейшем росте банка стоит свести к единой конвенции (`source` + дата/автор
  отдельным полем), иначе `bank_stats` будет всё труднее читать на глаз.

## Product direction (2026-07-13, Claude + Codex)

Перенесено из ACTIVE_TASK 2026-11-20 — долгоживущие решения, не текущая задача.


- **Positioning:** do not compete as a generic trainer, tutor CRM, or AI tutor. The
  product bet is a vertical EGE mentor operating system: verified evidence -> explicit
  intervention -> scheduled follow-up -> exam-like score outcome.
- **Moat:** dashboards, task banks, LLM feedback, and score forecasts are table stakes.
  The defensible asset is a trustworthy longitudinal intervention-to-outcome ledger plus
  a workflow that lets a tutor supervise more students without losing review quality.
- **External pilot gate:** do not invite unrelated students into the current runtime yet.
  The web app resolves `/students/current` to the first profile and uses one shared API
  token, so learner data is not isolated. Recruit tutor design partners/interviews now;
  give access to 2-3 external students only after a minimal identity/assignment boundary.
- **Measurement:** while the N=1 learner is ill, do not treat a timed cut as a baseline.
  Use the pause to dry-run mentor proactivity on existing evidence. Start with transparent
  trajectory status and confidence/insufficient-data labels; no ML score prediction before
  several comparable timed score events exist.
- **Visualization:** treat visuals as named interventions, not a content feature or moat.
  Prefer JSXGraph for reusable 2D geometry. GeoGebra 3D requires a commercial agreement
  for a paid product, so do not make it a commercial dependency without licensing review.
- **Next product slice:** close one observable loop end to end: repeated error/risk signal
  -> proposed action -> mentor approval -> mission delivery -> +7 review -> next timed
  score event. Record mentor time and intervention outcome alongside learner evidence.

### Agreed delta

- **Primary goal is explicit:** daughter >=85 on profile math by EGE-2027. Effort split:
  80-90% learner outcome, 10-20% tutor interviews / commercial hypothesis logging,
  0% payments/SaaS/multi-tenancy. Every feature passes the filter "does it add points
  or prove the loop works".
- **Mock date reserved: 2026-07-26** (first timed baseline, conditional on recovery).
  If moved, it may only be moved by fixing a new concrete date, never left open.
- **Now it is a wedge, not a moat:** the pilot proves the workflow (tutor/operator runs
  the loop and saves time), not the intervention-outcome dataset. Data moat is a
  multi-year story.
- **Mentor minutes are measured explicitly** via a manual journal (student | date | task |
  minutes | decision). DB timestamps are NOT a valid proxy for operator time.
- **Error category is never auto-derived from task type.** Answer-only errors stay
  `other/unclassified`; mentor gets a fast manual tag; auto-category allowed only when
  reasoning/code is present; intervention selector consumes confirmed actionable
  categories only. This is the prerequisite slice before wiring the proactive loop
  (`other` currently dominates top_errors).
- **External pilot isolation = one Docker stack per student** (own DB, token, compose
  project, ports, TG bot). No identity/multi-tenant code. Needs only port/env
  parametrization of docker-compose. Tutor complaints about tab-switching become the
  evidence for building an aggregated cockpit later.
- **Sequencing guard:** interviews (8-12, three segments: strong solo tutors, small
  teams, parent-operators) start now — script and outreach templates:
  `!DOC/operations/TUTOR_INTERVIEWS.md`; design-partner onboarding only AFTER the first
  closed intervention loop and a visible N=1 delta — concierge pilot is not a 10-20%
  effort item.
- **Commercial gating metric is student engagement, not tutor price sensitivity:**
  the product only creates value if students actually solve between lessons; weekly
  active days (already a first-class KPI) measures exactly this on N=1 today.
  Interview probe: "how many of your students do homework between lessons unprompted?"
- **Content is a hidden COGS at scale;** flip it: tutor brings own tasks via existing
  `add_task -> approve_task` pipeline = tutor lock-in. Interview probe: "where do your
  tasks come from?"
- **Fallback buyer hypothesis:** parent-operator (B2C) if tutors do not convert; product
  already fits it. Both models gate on minors' personal-data compliance before any
  external launch.
- **Market frame:** TAM ~8k productive profile-math tutors (rough), 300 paying = ~4%
  penetration (reachable), 1000 = ~12% (ambitious). Plan as a small profitable vertical
  SaaS at the lower bound, not the 3M MRR case.
- **Bank refill is in-scope now** (it is learner-outcome work, not commercial work):
  July math topics (экономика/стерео/планиметрия/параметр) and interval topics
  (Неравенства/ОДЗ) are still thin; `shortage` in `build_daily_queue` is the trigger.
  Answers must stay code-verified (anti-poison scripts), same as the June refill.
- **Channel split stands (decided earlier, unchanged):** TG = учебный канал ученика
  (daily part-1 drill, повторы, срезы, /ready); сайт = part 2, теория/визуализации и
  операторская/родительская витрина. New slices map onto this split; no re-decision needed.
