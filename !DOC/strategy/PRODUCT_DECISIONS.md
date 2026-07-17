# Product Decisions

Last updated: 2026-07-17

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
