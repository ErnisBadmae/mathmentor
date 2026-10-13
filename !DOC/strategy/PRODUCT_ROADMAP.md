# EGE Mentor product roadmap

Статус: active product strategy  
Обновлено: 2026-08-13  
Владелец продуктовых решений: Эрнис

Этот файл хранит только развитие EGE Mentor. Личная стратегия, карьерный deadline и
распределение внимания между проектами находятся в `../../../PERSONAL_STRATEGY.md`.
Текущий implementation slice и его статус находятся в
`../operations/ACTIVE_TASK.md`.

## Product outcome

Главная цель до ЕГЭ-2027 - помочь Ульяне получить не менее 85 баллов по профильной
математике. Продукт подчинён учебному результату:

- независимая попытка до подсказки;
- честный evidence и human review;
- целевая intervention по подтверждённой ошибке;
- delayed review на новой задаче;
- сопоставимые timed mocks.

Ценность продукта - замкнутый проверяемый цикл:

```text
attempt -> deterministic check -> confirmed error -> intervention -> delayed review -> score event
```

## Evidence-gated horizons

### G1. Валидный baseline и первый закрытый цикл, N=1

Exit criteria:

- есть валидный score event из timed mock;
- минимум одна подтверждённая ошибка связана с intervention и review на +7;
- видны weekly active days;
- operator minutes записаны явно, а не вычислены из DB timestamps;
- результат можно восстановить по provenance.

До закрытия G1 новые продуктовые направления не открываются.

### G2. Доказанная динамика до декабря 2026, N=1

Exit criteria:

- 4-5 сопоставимых ежемесячных mocks с видимой динамикой;
- ориентир на декабрь по профильной математике - не ниже 75;
- задания второй части проходят human-reviewed evidence path;
- daily loop работает без постоянного ручного принуждения;
- измерены engagement и стоимость работы взрослого.

Нельзя строить численный ML-прогноз балла по sparse N=1 данным.

### G3. Проверка workflow с design-partner tutor

Открывается только после закрытого N=1 цикла и видимой учебной динамики.

- один преподаватель;
- 2-3 ученика;
- 4-6 недель;
- отдельный изолированный Docker stack на ученика;
- измеряются active days, действия преподавателя по brief, mentor minutes, onboarding
  content cost и willingness to continue or pay.

Shared identity, tenancy и общий tutor cockpit не строятся для concierge pilot.

### G4. Выбор продуктовой формы

После ЕГЭ-2027 или эквивалентно сильных доказательств выбрать tutor B2B2C или
parent-operator B2C по фактическому использованию и willingness to pay. Только тогда
рассматривать payments, public onboarding, multi-tenancy, другие предметы и content
marketplace.

## Development lanes

Это порядок продуктовых контуров, а не параллельный backlog. `ACTIVE_TASK.md` выбирает
из него только ближайший доказательный срез.

### L1. Ground truth и engagement

- сопоставимые timed mocks без AI, интернета, телефона и подсказок;
- экзаменационный прогресс меняется только через `record_score_event`;
- показываются фактический score, gap и insufficient-data, без прогноза;
- weekly active days являются learner и adoption сигналом.

### L2. Подтверждённая классификация ошибок

- answer-only miss остаётся `other/unclassified` до human confirmation;
- task type не подменяет причину ошибки;
- intervention queue использует только подтверждённые actionable categories;
- provenance и append-only evidence обязательны.

### L3. Human-gated intervention

- система предлагает intervention и объясняет причину;
- mentor подтверждает действие до создания mission или note;
- signal, action, mission, +7 review и score event связаны source references;
- acceptance - минимум один реальный полностью закрытый цикл и записанное время.

### L4. Part 2 evidence

- ученик решает на бумаге до AI;
- модель только структурирует решение;
- mentor утверждает verdict;
- acceptance - 5-10 реальных разобранных решений с устойчивой ценой review.

### L5. Visual и content interventions

- визуал добавляется под наблюдаемую ошибку, а transfer проверяется позже без визуала;
- не строится generic visual engine;
- задачи добавляются только при измеренном дефиците и хранят provenance;
- content остаётся будущим tutor-supplied input через approve path.

## Product non-goals

- generic AI tutor или autonomous router;
- public SaaS и payments до G4;
- внешний ученик до G3;
- content-volume race с публичными банками;
- voice, Qdrant, Neo4j, CDC и LangGraph без наблюдаемой потребности;
- общий runtime или shared library с EnglishFriend;
- новая инфраструктура ради изучения технологии.

## Правило изменения roadmap

Изменение горизонта требует нового evidence, решения владельца и записи в
`PRODUCT_DECISIONS.md`. Реализация не может сама по себе объявить gate закрытым.
