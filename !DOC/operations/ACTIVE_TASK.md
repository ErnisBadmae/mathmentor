# Active Task

## 2026-10-13 — независимое ревью режима с таймером

Владелец согласовал идею отдельного режима с общим таймером и попросил короткий
промпт независимому архитектору. Промпт:
`!DOC/architecture/CISIA_TIMED_PRACTICE_REVIEW_PROMPT.md`.
Он запрашивает минимальное решение, проверку дедлайна/восстановления/повторных
callback, необходимые изменения схемы и 5 сценариев приёмки. Точный экзамен
и официальные лимиты пока не подтверждены; 5 вопросов / 10 минут — пример
учебной настройки. Реализация таймера пока не начиналась.

По запросу владельца накопленные изменения разложены на смысловые локальные коммиты:
правила агентов/roadmap; надёжность дневной очереди и формат ответов; общий Telegram
proxy; read-only экспорт измерений; CISIA; этот промпт и рабочие журналы.
Проверки 2026-10-13: 158 backend tests прошли в основном прогоне, ещё 2 теста CLI
экспорта прошли с отдельной временной папкой после ошибки доступа к системной temp;
всего 160 passed. Frontend build прошёл. Следующий шаг — независимое ревью по промпту
и уточнение экзамена перед реализацией.

## 2026-10-09 — возобновление тренировок и CISIA

Запрос владельца: ребёнок просит практику по `data/CISIA/tolc-i-sinavi-ornek-sorulari.pdf`.
Подготовлены 50 ссылок на исходные задания и 50 официальных ответов; математический
PDF (20 заданий) выделен без ключа. Формулы сохраняются исходными PDF-страницами,
текстовый слой используется только для поиска. Подробности: `data/CISIA/README.md`.
По запросу владельца 20 математических вопросов импортированы в учебную БД,
одобрены и доступны в `/cisia` / «CISIA · методичка». Условия — PNG из оригинала,
источник/номер/страница — в подписи, выбор A–E — кнопками или латинской буквой.
Оценка по официальному ключу, без LLM; валидный ответ завершает вопрос и сохраняет
evidence 1/1 либо 0/1. Невалидный ввод не создаёт failed evidence. Повторный импорт
создал 0 миссий; ранее созданные 20 сохранены.
English TOLC заменён CEnT-S с ноября 2025; старый образец не считать текущим пробником.

Blocker Telegram устранён: старый прокси вызывал `ProxyConnectionError` при
`set_my_commands`. Полученный от владельца новый HTTP-прокси проверен и сохранён
в каноническом `../!LOCAL/telegram-proxy.env`; пересоздан только сервис `bot`.
`telegram_getme_health.py` — OK, контейнер `healthy`. Общий оператор:
`../scripts/telegram_proxy.ps1`, решение: `../!DOC/adr/ADR-0002-telegram-proxy-registry.md`.
Миссии CISIA без topic_id не закрывают темы ЕГЭ и не создают их повторы или score events;
в обычных срезах найдено 0 задач CISIA. Следующий срез — реальная самостоятельная
тренировка ребёнка и разбор наблюдаемых ошибок. Остальные разделы и экзаменационная
цель (вуз/экзамен/язык) пока не уточнены. Сообщения ребёнку вручную не отправлялись.

Проверки: 73 backend tests (CISIA, drill, daily queue, slices, task bank) прошли локально
и в новом Docker-образе; ruff новых модулей прошёл. Frontend build прошёл ранее на той
же ревизии frontend; повтор не нужен. API и бот пересобраны/пересозданы, getMe — OK,
бот healthy. Живая очередь: номера 1–20, все PNG доступны, максимальная подпись 373 символа.
Предыдущие незакоммиченные изменения сохранены. Повторяемый импорт:
`docker compose exec -T api python -m scripts.import_cisia --apply`.

Проверка фактической выдачи 2026-10-09: `/cisia` зарегистрирована в Telegram;
обычная очередь «Сегодня» содержит 5 старых review-миссий от 16–18 августа
(производная/векторы/делители/экстремумы). Неотправленных заметок нет. Пуш 16:00
смотрит только на новые filled, поэтому при уже полной открытой очереди пишет
«Новых задач на сегодня нет». Владелец выбирает: основной CISIA по 5 вопросов
либо отдельный CISIA вместе с обычным дриллом; действующие очереди пока сохранены.

Last updated: 2026-10-13

## grounded-judge-gate как зависимость: `totals` в сборщике дня (2026-08-14)

Пакет опубликован на PyPI (0.3.0, MIT, требует Python >=3.12, одна зависимость `pyyaml`).
Владелец проверил не по ответу twine, а установкой в чистое окружение: wheel 23437 B,
sdist 29421 B, `py.typed` есть, импорт поднимается из установленного пакета.

**Что взяли и что сознательно не взяли.**

- Взяли **только** `judge_gate.totals` — доменно-независимую проверку покрытия прогона.
  Её докстринг прямо приглашает второго вызывающего: «anything that routes work into
  named branches and records named failure reasons is another».
- **Не взяли** `judge_gate.authority` / `normalize` для оценки ответов: это был бы регресс.
  Библиотечный `normalize` не знает про разряды числа (`7.776` → 7776 — инцидент, на
  котором ученица теряла балл), про информационные единицы (`768 Кбайт` → у него `None`,
  то есть уход к LLM вместо детерминированного accept), про интервалы и про
  представимость эталона в бланке. Направление зависимости здесь обратное: правила
  родились в egeMentor.

**Куда подключено.** `build_daily_queue` возвращает третье поле `coverage`. Контракт
`DAILY_COVERAGE` объявляет словарь исходов одного слота: маршруты `drill`/`unfilled`,
причина `no_fresh_task` с потолком 0 — осознанно написанная строка «слот, который ребёнок
не получил, приемлемым не считается». Наблюдения строятся по слотам бюджета, а не по
кандидатам: при доборе несколько shortage могут быть поглощены и день всё равно полон.

Окно измерения соблюдено (урок из статьи №2 про пол, применённый к крошечной пачке): при
`budget <= 0` контракт не проверяется — дню без бюджета нечего покрывать.

Нарушение **докладывается, а не бросается**: уронить сборку дня значит оставить ребёнка
вообще без задач, что хуже короткого дня. В боте дефицит остался `warning`, а нарушение
покрытия пишется `logger.error` — раньше недобранный день был неотличим от нормального,
бот бодро писал «Сегодня 2 задач(и) — вперёд!».

**Честно о том, что это даёт.** Сегодня сохранение выполняется по построению: считать
нечему теряться. Ценность в другом — это ловушка ровно на тот класс регресса, который уже
случился 10 августа (слот, ушедший в `continue` без учёта), плюс жёсткая ошибка
`TotalsContractError` на опечатке в имени маршрута или причины: иначе целая ветка тихо
перестала бы считаться. Это по-прежнему наблюдаемость с объявленным словарём, а не
контроль: короткий день пишет ERROR в лог, но никого не будит.

**Проверка.** `pytest tests/` → 294 passed (те же два предсуществующих падения);
`import-linter` — контракты слоёв целы (внешний пакет их не нарушает); ruff по изменённым
файлам без новых замечаний. Новые тесты: короткий день даёт нарушение, полный — нет,
опечатка в маршруте падает `TotalsContractError`. **Сборка контейнера — независимое
подтверждение публикации**: `docker compose build api` скачал `grounded_judge_gate-0.3.0-py3-none-any.whl`
с PyPI в чистый образ и поставил вместе с `pyyaml`. Сервисы подняты, бот `healthy`.
Живой прогон: день уже собран пушем на 5 задач, `budget=0` → `coverage=[]` (окно
измерения отработало верно). В очереди появилось «Кодирование изображений и звука» —
6 задач, добавленных 13 августа, разблокировали этот повтор.

**Для статьи.** Теперь утверждение «доменно-независимый модуль нашёл второго потребителя в
системе, для которой не проектировался» проверяемо, а не декларативно. Второй экземпляр
того же класса дефекта (10 августа) описан в записи ниже — он ценнее самой зависимости:
это другая предметная область и другой автор решений.

## Задача без записываемого ответа → ложный провал (2026-08-13)

Триггер: проверка активности. 11 августа ученица впервые сделала полную пятёрку за ~45 мин
(в т.ч. две новые темы — прямое подтверждение, что фикс планировщика от 10.08 работает).
Одна задача засчитана провалом — разбор показал, что виновата задача, а не ученица.

**Что произошло.** Задача части 1 «в коробке 30 шаров: 12 красных, 8 синих, 10 зелёных»
с эталоном `2/3` (seed-корпус `corpus:probability:task-a`, `source=corpus_llm`). Ученица
ответила `0,667` — рассуждение и число верны. `answer_is_correct` честно вернул False:
`Fraction("0.667") != Fraction(2,3)`. Правильного ответа у задачи не было **в принципе**:
2/3 не записывается в бланк ЕГЭ ни с какой точностью. На реальном ЕГЭ такой задачи быть
не может — числа подбираются под конечную десятичную дробь.

Отдельный ущерб: у seed-задачи в поле `error_category` захардкожена
`PROBABILITY_DOUBLE_COUNT`, поэтому любой провал на ней помечается «двойным счётом»
независимо от того, что произошло. Категория поднялась до 6 и стала второй по частоте
«проблемой» ученицы — при том, что вероятность закрыта ещё в июне (5/5). Журнал ошибок,
ради достоверности которого продукт и существует, набирал ложный сигнал.

**Решение — чинить контент, а не грейдер.** Ослабить `answer_is_correct` до
«приблизительно равно» означало бы открыть дорогу ложным зачётам; строгое сравнение
оставлено как есть.

- `domain/policies.py`: `answer_fits_exam_blank(answer)` — ответ записывается в бланк,
  если это целое или КОНЕЧНАЯ десятичная дробь (знаменатель несократимой дроби вида
  2^a·5^b). Нечисловые ответы (интервалы, «768 Кбайт», текст) не трогает — у них свой формат.
- `approve_task` — фейл-клоузд гейт. Одобрение выбрано как место проверки потому, что это
  **единственный шов, через который контент попадает к ученику**, независимо от источника
  (seed, corpus_llm, генератор, ФИПИ, MCP `add_task`). Темы части 2 исключены: там ответ
  бывает символьным (`12√13/13`) и проверяется человеком.
- `scripts/audit_task_bank.py` — тот же предикат по уже одобренному банку (гейт задним
  числом ничего не перепроверит). Код возврата 1 при находках, годится для CI.
- Данные: обе негодные задачи получили корректные числа (`0,6` и `0,375`) в seed и в живой
  БД; ложная ошибка снята (`confirmed_category=NONE`,
  `category_confirmation_source=operator:bad-task-2026-08-13`); карточка повтора по
  вероятности возвращена из `BACK_TO_WORK` в `DONE`.

**Проверка.** `pytest tests/` → 292 passed (те же два предсуществующих падения).
Новые тесты: `approve_task` отклоняет `2/3` и оставляет задачу в DRAFT; принимает `3/8`
(записывается как 0,375 — важна представимость, а не запись дробью). Аудит банка:
394 из 394 чисто. `docker compose up -d --build api bot`. Ребёнку отправлено объяснение
(`delivered_to_telegram: 1`).

**Наблюдение, не закрытое кодом.** LLM-ревьюер в фидбеке написал «Вероятность найдена
верно» и при этом выставил статус FAILED и категорию ошибки. Расхождение между текстом
фидбека и вердиктом — сигнал, который сейчас никем не ловится: он молча становится записью
в журнале ошибок. Кандидат на эскалацию к человеку вместо тихой записи.


## Планировщик дня: слот сгорал на shortage, новые темы не проходили (2026-08-10)

Триггер: ребёнок в переписке — «дриллы те же почему-то всё ещё» и «в последний раз вообще
одна задача была, после решения он написал „на сегодня больше нет“». Пополнение банка
на +84 задачи (2026-07-30) жалобу не сняло — потому что упор был не в банк, а в планировщик.

**Диагноз (подтверждён данными, не догадка).** На 2026-08-07: 321 APPROVED задача в банке,
18 просроченных повторов, а до ребёнка доходило 2-3 задачи из 5.

- **Слот сгорал на shortage.** В `build_daily_queue` кандидаты обрезались по бюджету ДО
  похода в БД (`select_daily_queue(...)[:budget]`), и если под кандидата не находилось
  свежей задачи — слот уходил в `shortage` и терялся: `continue` без добора.
  Два кандидата были неустранимо «сухими» и, будучи самыми старыми, вставали в очередь
  первыми каждый день:
  - «Логарифмы» (тема-призрак из Excel-трекера, `tasks_in_bank = 0`), повтор с 2026-07-10;
  - «Кодирование изображений и звука» — в банке 1 задача, уже назначенная → `fresh = 0`.
- **Новые темы не попадали в очередь никогда.** `select_daily_queue` возвращал
  `[*due, *back_to_work, *new][:budget]`; просроченных повторов (18) всегда больше бюджета
  (5), поэтому хвост `new_topics` не достигался в принципе. Плюс темы с повтором отдельно
  вычёркиваются из `new_refs`. Повторы отсортированы по `due_date` → ребёнок изо дня в день
  видел один и тот же набор ТЕМ (задачи внутри темы при этом свежие — `exclude_assigned_to`
  работает корректно). Её «те же дриллы» — про темы, наблюдение точное.
- **10 зависших миссий** (ACTIVE/REPEAT с 16-18 июня и 08 июля, не `daily:`) в бот не
  попадали, но держали свои темы в `in_work`, из-за чего те не считались доступными как новые.

**Правки.**

- `domain/policies.py`: `select_daily_queue` теперь возвращает ВЕСЬ упорядоченный список
  кандидатов (длиннее бюджета) — обрезание перенесено в вызывающего, который знает, под кого
  реально нашлась задача. Добавлен `DAILY_NEW_TOPIC_QUOTA = 1`: один слот бюджета
  резервируется под новую тему, иначе длинный хвост повторов запирает их навсегда.
  Формула бюджета вынесена в `daily_budget(open_count, limit)` — чтобы не дублировать её
  в двух модулях.
- `application/use_cases.py`: цикл идёт по полному списку кандидатов и останавливается по
  `len(filled) >= budget`; кандидат без свежей задачи по-прежнему попадает в `shortage`,
  но его слот добирается следующим.
- Данные: закрыт мёртвый повтор «Логарифмы» (единственная DUE-карточка на теме с пустым
  банком), сняты в `SKIPPED` 10 зависших не-daily миссий старше 14 дней.

**Проверка.** `pytest tests/` → 290 passed; падают только два предсуществующих и не
связанных с правкой (`test_student_simulation` — кодировка вывода симулятора;
`test_measurement_export` — Permission, файл ещё не в гите), оба воспроизведены на
застэшенных правках. Новые тесты: добор слота вместо потери (регресс из живого прогона) и
проход новой темы сквозь хвост из 18 повторов. Живьё: `docker compose up -d --build api bot`,
пересборка дня исправленным кодом → очередь из 5 задач, впервые с новыми темами
(«Применение производной: экстремумы», «Делители числа (Задание 25)») рядом с повторами.
09 августа ребёнок решил задачу по неравенствам верно.

**Пополнение банка (тот же день).**

- `generate_tasks.py --count 6 --seed 11 --approve` по всем 14 шаблонным темам → **+84**.
- **+6 задач в «Кодирование изображений и звука»** — тема, из-за которой сгорал слот
  (в банке была 1 задача, уже назначенная). Составлены вручную, ответ посчитан кодом
  (прямые: объём изображения/звука; обратные: по объёму найти палитру и длительность),
  каждая прошла `answer_is_correct(ans, ans)` до вставки, формат ответа — как у seed-задачи
  темы (`'768 Кбайт'`). Генератор эту тему по-прежнему не покрывает; при желании — новый
  шаблон в `TEMPLATES` по образцу вставленных шести. Повтор по теме теперь закрываем.

**Запрос ребёнка → следующая задача.** Хочет кнопку «дай ещё похожую» с генерацией в
реалтайме после непонятной задачи. Реализуемо без нарушения анти-poison: шаблоны
`generate_tasks.py` уже считают ответ кодом и самопроверяются, LLM в контуре нет — нужен
вызов шаблона по `topic_id` в обработчике кнопки (рядом с существующим `serve_more_from_topic`),
с фолбэком на банк, если шаблона для темы нет. Ребёнку это обещано именно в такой
формулировке («задачу придумывает не нейросеть, а шаблон; ответ считается кодом»), сроки
не назывались.

**Хвост.**

- MCP-сервер в сессии работал на коде, поднятом до правки — его вызовы `build_daily_queue`
  до перезапуска шли по старой логике. При проверках через MCP это надо держать в голове.
- Легаси-темы с пустым банком («Логарифм. Уравнение 1/2», «Логарифмы: разность») остаются
  в программе — карточек повторов на них нет, но при появлении они дадут ту же картину.
- Правки не закоммичены.

## Telegram proxy recovery (2026-08-04)

- The bot entered `Restarting (1)` because its eight-day-old container still held the old
  proxy `45.153.162.248:50100`, which now refuses connections.
- The host proxy had already changed to `http://50.114.27.115:50100`; host-side probes from
  the managed shell were blocked, but the Docker runtime can reach it.
- Recreated only `bot` with `docker compose up -d --force-recreate bot`, which refreshed
  its environment without touching API/Postgres/web or sending a learner message.
- Verified across two health intervals: `Up (healthy)`, `restarts=0`, no fresh errors.
  The healthcheck runs `telegram_getme_health.py`, so this confirms Telegram `getMe`.

## Ритм + пополнение банка: пинок ребёнку + генератор + ФИПИ-зеркало (2026-07-30)

Триггер: родитель попросил проверить активность (`student_overview`/`attempt_history` через
MCP — училась 28 июля, 29-го ещё не заходила, `retention.active_days=1/3`), затем ребёнок
пожаловался, что в срезе повторяются задачи.

- **Пополнение банка генератором.** Одобрены 3 старых зависших DRAFT (степени/корни, из
  прошлой сессии) + прогнан `scripts/generate_tasks.py --count 6 --seed 3 --approve` по
  всем 14 шаблонным темам сразу (без `--from-signal`, т.к. `topic_demand` пока пуст —
  сигнал ещё не набрался живыми тапами кнопки «Ещё по теме») → **+84 новых APPROVED
  задачи**, `bank-stats` актуализирован.
- **Мягкий пинок в TG** через `mcp__ege__publish_feedback` (`delivered_to_telegram: 1`):
  благодарность за сигнал о повторах → факт, что банк уже пополнен → короткий разбор
  вчерашней ошибки (производная физ. смысл: перепутала s(t) и s'(t)) без давления →
  явное разрешение жать «⏭ Пропустить», если нет настроя.
- **Повтор метода «ФИПИ через зеркало» (2026-07-17).** PDF-сборник MathStart
  передекачан (URL из прошлой сессии, старый временный файл не пережил сессию), текст
  переизвлечён через `fitz` (expert-agent `venv_312`). Посчитаны approved-задачи по темам
  — самые тонкие: часть-2 темы (`Задача 13: отбор корней на отрезке` — было 3! —,
  параметр №18, планиметрия №17, стереометрия №14), т.к. генератор их принципиально не
  берёт (нужны фигуры/рассуждение, не шаблон).
  Добавлено 6 новых реальных прототипов, каждый — независимо проверен кодом
  (не «на глаз»): 3× тригонометрия-отбор-корней (13.1–13.3, sympy `solveset` +
  численная сверка на интервале), 1× параметр (18.1, гибрид «алгебра + независимая
  численная проверка количества корней по плотной сетке для ~20 значений `a`» — параметр
  органически самый рискованный тип для ручной ошибки), 1× планиметрия (17.2,
  координаты в sympy), 1× стереометрия (14.1, координаты в sympy). Все — `source=
  "mathstart-fipi-bank"`, честный `source_url` с номером задачи и страницей PDF (не
  выдуманный), уникальный на задачу (см. гочу source_ref-дедупа от 2026-07-17).
  Итог по тонким темам: «Задача 13: отбор корней» 3→6, параметр №18 6→7, планиметрия
  №17 8→9, стереометрия №14 8→9.
- Verification: каждая новая FIPI-задача проверена программно (sympy/численно), не
  только вручную — см. скрипты в scratchpad сессии (`solve_13.py`, `verify_18_1.py`,
  `verify_17_2.py`, `verify_14_1.py`), не закоммичены (одноразовые, не часть репо).
  Генератор: `+6` тестов не требовалось (код не менялся, только прогон существующего
  CLI). MCP `add_task`/`approve_task` подтвердили `status=approved` на все 6+3+84.
- **Хвост:** в PDF-сборнике по каждой части-2 теме остаётся 30+ неиспользованных
  прототипов — метод воспроизводим, можно продолжать точечно по мере утончения банка
  (`bank-stats` на сайте/`topic_demand` в MCP — сигнал, что доливать). Параметр — самый
  трудоёмкий тип для этого метода (нужна и алгебра, и численная защита от ошибки),
  закладывать на него больше времени, чем на прочие part-2 темы.

## On-demand практика: «ещё по теме» + сигнал спроса + генератор (2026-07-27, ЗАДЕПЛОЕНО)

По запросу ребёнка («накидай задач той же темы, другого типа/сложности», в срезе повторилась
задача). Три куска, замыкающие цикл, где непроверенное в реалтайм не уходит никогда. Полный
план: `~/.claude/plans/toasty-shimmying-bunny.md`.

- **Кусок 1 — сигнал спроса.** Новая таблица `topic_requests` (миграция `a9b0c1d2e3f4`,
  применена live): `student_id`, `topic_id`, `outcome` (`served`|`shortage`), `created_at`.
  `TopicRequestSqlRepository.add`/`demand_by_topic(days)` (агрегат served/shortage по темам,
  джойн к темам за названием — сигналы с `topic_id=None` в агрегат не попадают by design).
  MCP read-tool `topic_demand` — оператор/агент видит, чего не хватает.
- **Кусок 2 — очередь из банка + кнопка.** `LearningService.serve_more_from_topic` (общее
  ядро `_topic_drill_from_pool` с `self_add_topic_mission`, но БЕЗ гейта open-today и БЕЗ
  требования state==OPEN — тема активно дриллится; валидация только «не manual-review +
  фаза началась»). Пишет сигнал в обе ветки (served/shortage). Бот: кнопка «🔁 Ещё по этой
  теме» на сообщении-вердикте (`_more_keyboard`, callback `topics:more:<topic_id>`,
  `topic_id` теперь в возврате `submit_attempt`), хендлер `_on_topics_more` подаёт свежую
  задачу сразу; shortage → дружелюбный alert.
- **Кусок 3 — шаблонный генератор.** `backend/scripts/generate_tasks.py`: реестр
  `TEMPLATES` (14 тем — вся вычислимая часть 1: степени/корни, логарифмы, простейшие
  уравнения, проценты, вероятность, векторы, производная геом/физ, неравенства +
  информатика: логика, комбинаторика, делители, Python арифметика/for). Ответ считается
  кодом + внутренний `assert`; формат-guard `answer_is_correct(ans,ans)` (+
  `parse_interval_answer` для интервалов) перед вставкой, fail-closed. Вставка DRAFT через
  `add_task` (`source="generated"`), дедуп по контент-хешу `gen:<slug>:<sha1[:12]>`.
  CLI: `--topic/--count/--from-signal/--approve`. Офлайн, вне request-пути.
- **Грейдинг/отчёты source-agnostic** — сгенерённая-и-одобренная задача течёт в
  evidence/журнал/`weekly_digest` через обычный `submit_attempt`, без спец-обвязки.
- Verification: `pytest` 258 passed (было 247, +11); ruff по изменённым чист; миграция
  upgrade/downgrade/upgrade чисто; генератор live дал 3 DRAFT по степеням; release_smoke
  GREEN (head `a9b0c1d2e3f4`); telegram runtime smoke GREEN. ВЫКАЧЕНО:
  `docker compose up -d --build api bot` + `alembic upgrade head` в контейнере + `restart web`.
- **Хвост / чтобы реально заработало для ребёнка:**
  (1) кнопка «ещё» уже живая и отдаёт из существующего банка; (2) чтобы генератор реально
  пополнял — прогнать `python -m scripts.generate_tasks --from-signal --approve` (ночью или
  вручную), пока это ручной шаг, не в cron; (3) сейчас в live висят 3 сгенерённых DRAFT по
  степеням (не одобрены — ребёнку не видны) + 1 тестовый сигнал с `topic_id=None`; можно
  одобрить драфты через MCP `approve_task` или удалить; (4) реального тапа кнопки в живом
  чате ещё не было — проверено тестами+смоками; (5) генератор пока НЕ в night-queue — решить,
  добавлять ли.

## Надёжность стека + уведомления (2026-07-23, ЗАДЕПЛОЕНО)

## Надёжность стека + уведомления (2026-07-23, ЗАДЕПЛОЕНО)

- **Инцидент:** ребёнок пожаловался, что бот не работает. Причина — весь стек
  (`postgres`/`web`/`bot`), кроме `api`, простоял 2 дня после сна/перезагрузки хоста:
  `restart: unless-stopped` в `docker-compose.yml` стоял только у `bot`, у остальных
  трёх сервисов не было вообще никакой restart-политики. **Исправлено**: добавлен
  `restart: unless-stopped` всем четырём сервисам. Это системная дыра, которая тихо
  ломала бы и новые уведомления ниже — стоит иметь в виду при любом будущем
  разборе «бот молчит».
- **Уведомления (по запросу родителя+ребёнка):** согласились, что напоминаний в TG
  достаточно (замену на блокировку экрана/OS-level parental control сознательно не
  делаем — не в этом стеке, отдельная инженерная поверхность, обсуждали и отложили).
  1. Дневной пуш (`telegram_push_time`, default 16:00) переформулирован на
     побуждающий текст + теперь дополнительно напоминает про срез, если
     `days_since_last_diagnostic >= telegram_slice_reminder_days` (default 4 дня).
  2. Новый цикл `_followup_reminders`: если после пуша ученица не начинала (нет
     попытки сегодня) и дневная очередь не пуста — повторяет напоминание каждые
     `telegram_reminder_repeat_hours` (default 2ч) вплоть до
     `telegram_reminder_cutoff_time` (default 21:00), останавливается сама, как
     только появляется первая попытка за день.
  3. Новый цикл `_parent_evening_summary` в `telegram_parent_summary_time` (default
     21:00, тот же час, что cutoff): пуш в `telegram_parent_chat_id` — занималась ли
     сегодня, сколько дневных миссий ещё открыто, давно ли был срез.
     `TELEGRAM_PARENT_CHAT_ID` уже был задан в `.env` — фича включилась сразу после
     деплоя, ничего дополнительно настраивать не нужно.
- Backend: `LearningService.days_since_last_diagnostic`/`daily_activity_summary`
  (`use_cases.py`) — маленькие read-only агрегаты поверх уже существующих
  `list_diagnostics`/`list_attempt_history`/`list_daily_drill`, ничего нового в БД.
  5 новых полей в `config.py` (`telegram_reminder_repeat_hours`,
  `telegram_reminder_cutoff_time`, `telegram_slice_reminder_days`,
  `telegram_parent_summary_time`), все с дефолтами — без `.env` работает из коробки.
- Verification: `pytest` 247 passed (было 241, +6); ruff по изменённым файлам без
  новых замечаний. ВЫКАЧЕНО: `docker compose up -d --build api bot` + `restart web`
  (тот же кэш DNS на старый IP api, что и в прошлый раз — теперь это известный
  ритуал после пересборки `api`). `telegram_bot_runtime_smoke.py` GREEN.
- Хвост: живого тапа/реального цикла напоминаний в проде ещё не видели (сработает
  сегодня в 16:00/21:00 по МСК первый раз) — проверить эффект в следующие пару дней.
  Циклы `_followup_reminders`/`_parent_evening_summary` не покрыты loop-таймингом в
  тестах (только их однократная логика — `daily_activity_summary`,
  `_parent_summary_text`, `_run_daily_push`) — та же осознанная граница, что уже
  была у исходного `_morning_push` до этой сессии.

## TG: skip-кнопка + самостоятельный выбор темы (2026-07-17, ЗАДЕПЛОЕНО)

- По запросу ребёнка: (1) кнопка «⏭ Пропустить» на сообщении с дневным заданием —
  переиспользует уже протестированную семантику текстовой `/skip` (задание остаётся
  `ACTIVE`, откладывается в рамках сессии бота), просто добавлен `reply_markup` и
  callback `today:skip:<mission_id>`; (2) команда/кнопка `/topics` («➕ Своя тема») —
  ученица сама выбирает тему части 1 своего трека и получает свежую задачу в
  «Сегодня» вне бюджета `build_daily_queue` (тот учтёт её как carry-over назавтра
  через уже существующий механизм open-count, специального кода не потребовалось).
- Product-решения (обсуждены и зафиксированы перед реализацией): self-pick ограничен
  темами части 1 (тот же фильтр, что `/ready` — part-2/manual-review темы недоступны,
  им нужна ручная проверка на сайте); пререквизиты (`PREREQUISITES`,
  `backend/app/domain/prerequisites.py`) уважаются — это не декларация, а
  автоматическая проверка по факту решённой базовой задачи (`solved_count > 0`),
  поэтому ничего специально отмечать не нужно и риска «забыла отметить» нет.
- Backend: `LearningService.list_self_pick_candidates`/`self_add_topic_mission`
  (`use_cases.py`) — переиспользуют `list_approved_for_topic`, `prerequisites_met`,
  `_requires_manual_review_path`, `_phase_started` (те же примитивы, что
  `build_daily_queue`/`list_theory_ready_candidates`). Новая миссия помечается
  `source_ref=daily:self:<topic_id>` — тоже `daily:`-префикс, поэтому весь
  остальной дрилл-конвейер видит её как обычную дневную миссию без доп. кода.
  `describe_pick` получил ветку `kind="self_pick"`.
  Bot: `_daily_task_keyboard`, `_skip_daily_task` (общий хелпер для текстовой
  `/skip` и кнопки), `_on_today_skip`, `_topics_keyboard`, `_on_topics`,
  `_on_topics_pick` — по образцу уже существующего `/ready`.
- Никаких миграций/новых MCP-инструментов/фронтенд-изменений — фича целиком в TG
  (канал части 1), схема БД не менялась (`missions.topic_id`/`source_ref` уже были).
- Verification: `pytest tests/test_daily_queue.py tests/test_bot.py` — 23+34 passed
  (было 23/28, +6/+6 новых); полный backend `pytest` 241 passed (было 228); ruff по
  изменённым файлам — новых замечаний нет (весь список E501 — старый долг на
  нетронутых строках). ВЫКАЧЕНО: `docker compose up -d --build api bot` + `restart web`
  (nginx держал закешированный DNS на старый IP api-контейнера — 502 до рестарта
  web). `telegram_bot_runtime_smoke.py` GREEN (`@egemathandinformbot`, без polling
  errors), `release_smoke.py` GREEN (health/миграции на head `f7a8b9c0d1e2`/getMe/
  живой judge).
- Хвост: живая проверка тапом в реальном Telegram-чате ещё не сделана (только
  через тесты + release smoke) — попросить ребёнка попробовать `/today` (кнопка
  skip) и `/topics` при следующем заходе, посмотреть на реальную реакцию.

## Рабочая связка: реальные прототипы ФИПИ через PDF + PyMuPDF (2026-07-17)

**Проблема:** нужен контент из открытого банка ФИПИ (учебная обратная связь: летний
срез ~80% задач из банка). Прямой доступ невозможен: `ege.fipi.ru` не открывается в
этой сети (тот же барьер, что у Cloudflare Tunnel); `sdamgia.ru` активно блокирует ботов
(`print`-версия задачи -> `403 Forbidden`, полный тест требует авторизации). `pdftotext`
(Git-бандл) на официальных PDF-сборниках прототипов **ломает буквы точек фигур** —
геометрические условия выходят с `` вместо `A`, `B`, `M`... — потому что эти буквы
закодированы в PDF как Unicode-блок Mathematical Alphanumeric Symbols (курсивные
математические литеры, не обычная латиница), а `pdftotext` их не резолвит.

**Решение:** в `C:\Users\badmaev_es\develop\expert-agent\venv_312` уже стоят `PyMuPDF`
(`fitz`), `pdfplumber`, `docling` (используются в expert-agent для DIP/Document
Intelligence). `fitz` разбирает эту кодировку корректно — текст выходит чистым.
Рабочий пайплайн:
1. Скачать открытый PDF-сборник прототипов (легитимный, публичный — не сам fipi.ru):
   `https://down.ctege.info/ege/2026/proba/matem2026profi-bank-fipi.pdf` (сборник
   MathStart, ~924 задачи / 468 прототипов / 374 страницы, обновляется по годам).
2. Извлечь текст: `"C:\Users\badmaev_es\develop\expert-agent\venv_312\Scripts\python.exe"`
   + `fitz.open(path)` + `page.get_text()` по всем страницам в один `.txt` (UTF-8).
   НЕ использовать `pdftotext` для этого PDF (буквы точек побьются).
3. В файле условия сборника даны БЕЗ ответов (сама постраничная разметка "Ответ:"
   пустая — платный/интерактивный элемент оригинала, в статике его нет). Ответ на
   каждую задачу нужно вычислить и перепроверить самому (SymPy/координатная геометрия
   для стерео/планиметрии, численный перебор для параметра) — тот же анти-poison
   принцип, что и в июньском наполнении банка (`gen_math.py`).
4. Заносить в банк через `add_task` с `source="mathstart-fipi-bank"`,
   `source_url="<ссылка на PDF> (задача <номер>, стр. <N>)"` — честная, рабочая ссылка
   на реальный источник (не выдуманная). `source_url` уникален и служит `source_ref`
   (unique constraint) — **при парном добавлении задач НЕ давать двум разным задачам
   одинаковый `source_url`**, иначе вторая вставка тихо схлопнется в первую (тот же
   `id` вернётся дважды, задача потеряется без ошибки — наступил на это 2026-07-16).

**Сделано этим методом (2026-07-17):** 4 реальные задачи ФИПИ (14.6 стерео, 17.3/17.7
планиметрия, 18.2 параметр) + ранее 5 сконструированных агентом той же формы
(`source="agent"`, честно помечены как не-прототипы). Банк по трём тонким темам вырос
3->6 / 3->7 / 3->6 задач. Метод применим ко всем темам part-2 (стерео №14, планиметрия
№17, параметр №18) — в сборнике по 40+ прототипов на тему, использована малая часть.

## Product direction review (2026-07-13)

The bounded L2a implementation in
`!DOC/operations/CODEX_L2_CONFIRMED_ERROR_TAG.md` was accepted, committed as `939bf53`,
deployed, and live DB head is `f7a8b9c0d1e2`. Confirm only two reviewed `other` events:
`00000000-0000-0000-0000-000000006102 -> arithmetic` and
`9c7de792-31e0-4064-99b1-0db672ad5c74 -> unknown_method`; leave the other five
unclassified. Event `74f3e876-25af-45e3-80f2-05ab38d4e519` is a confirmed grader false
failure, not a learner error. Execute
`!DOC/operations/CODEX_GRADER_DECLARED_ANSWER.md` before specifying L3.

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

### Agreed delta (Claude + Codex, 2026-07-13)

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

## Platform-devkit pilot (Phase C, 2026-07-13)

- **Status:** completed locally; repo-level docs tooling now uses
  `platform-devkit` through a compatibility shim.
- **Done:** `platform-devkit` editable-installed into root `venv`;
  `scripts/docs_maintenance.py` delegates to `platform_devkit`.
- **Local overrides:** `.claude/rules/simplicity.md` is not force-synced because
  egeMentor adds a project-specific Russian-dialogue rule.
- **Verified:** shim `--version` works; `platform-docs audit` runs with only
  pre-existing doc-size/session-log warnings; `platform-encoding-guard --check`
  clean; backend pytest 210 passed; ruff clean on the touched test file.
- **Next:** decide whether egeMentor should add a real `.pre-commit-config.yaml`
  later; do not force-sync local `.claude/rules/simplicity.md` unless the shared
  preset learns project-specific overrides.

> Кросс-проектная стратегия (verifiable-AI рамка, роли Claude/Codex/Qwen, ege-трек
> proven-delta в общей картине): канонический док — `expert-agent/!DOC/STRATEGY.md`.

## Current Snapshot (2026-07-10, deterministic planner MVP: prereq-gate + explanation)

- Реализовано (Claude): детерминированный learning planner MVP поверх существующего
  `build_daily_queue` — БЕЗ Дейкстры, weighted-frontier, LearningPlanner-класса, goal-входа и
  миграций. Оценка идеи Кодекса: Дейкстра — неверный инструмент (задача не shortest-path, а
  prerequisite-closure); weighted-scoring тоже преждевременен — это по сути замороженная
  error-intervention логика, тюнить не на чем (N=1). Ценные 20% (ворота + объяснение) едут дёшево,
  weighted-80% отложено до weekly-review данных и подключится через готовый `select_intervention_queue`.
- Что добавлено (~40 строк чистого domain, без БД):
  - `domain/prerequisites.py`: статичная карта `PREREQUISITES` (4 defensible-ребра внутри Части 1 на
    реальных названиях тем) + чистый предикат `prerequisites_met`.
  - `domain/policies.py`: чистый презентер `describe_pick(reason)` — строка «почему» для оператора/агента.
  - `application/use_cases.py` `build_daily_queue`: посчитан `passed_titles` (темы с `solved_count>0`),
    добавлен один gate-предикат в фильтр новых тем, к каждому пику прицеплены структурный `reason` (данные)
    и строка `why`. `select_daily_queue` (инвариантная функция) НЕ тронут — `reason` едет сквозь неё как
    лишний ключ dict.
- «Проблема 3 потребителей» решена архитектурно: domain отдаёт ОДИН структурный `reason` (узкий
  интерфейс), сверху N тонких форматтеров. В MVP реализован только один (`describe_pick`, оператор/агент).
  Детский и родительский тексты — будущие форматтеры над тем же dict; domain при их добавлении не меняется.
  Детский текст обязан вести «от достижения, а не от дефицита» (правило снижения тревоги от 25.06).
  LLM ни в одном форматтере: объяснение = честный след выбора (ложится в verifiable-AI линию).
- Инварианты целы: due→back_to_work→new, open-count в лимит, идемпотентный `source_ref`,
  manual-review темы вне авто-дрилла, phase/ready_mode, LLM не выбирает тему. Ворота применяются и в
  ready-mode (общий фильтр).
- Verification: targeted pytest `17 passed` (13 старых + 4 новых), full backend `210 passed`
  (было 206, +4), ruff по затронутым файлам с `--ignore E501` clean, import-linter `2 kept, 0 broken`
  («domain is pure» держится). Живое наблюдение на реальном seed: пара «Вычисления: логарифмы…» (база) →
  «Простейшие уравнения…» (зависимая) — до закрытия базы зависимая в очередь не попадает; после сдачи
  базы появляется, `why` называет закрытый пререквизит. НЕ задеплоено (deploy — отдельный шаг).
- Хвост: (1) решить, писать ли ADR и где (каталога `!DOC/adr/` пока нет — заводить схему не стал под
  Simplicity First); (2) когда фича подтвердится — детский форматтер `why` в утренний пуш TG и
  родительский в mentor-note/дашборд; (3) прокинуть `why` в `mentor_brief`/операторский дашборд как
  первый видимый потребитель; (4) при желании расширить `PREREQUISITES` за пределы 4 рёбер.

## Current Snapshot (2026-07-09, MCP context + no-domain publishing)

- Реализовано (Codex): компактный первый слой для MCP — `mentor_brief(student_id, days=14)`.
  Это не замена истории: сырые попытки, ошибки, ревью и программа остаются в Postgres и доступны
  через drill-down tools (`attempt_history`, `program_progress`, `error_journal`, `reviews`,
  `manual_reviews`, `topic_theory`). В `mentor_brief` намеренно не попадают полные `answer_text`
  и `code_text`, чтобы не раздувать контекст агента при первом чтении.
- Бизнес-логика оставлена простой: без pgvector/Qdrant/нового слоя памяти. Векторный поиск имеет смысл
  добавить позже только для задачи "найди похожие прошлые ошибки/задачи"; для текущей mentor-сводки
  достаточно детерминированной агрегации из Postgres.
- MCP: добавлен tool `mentor_brief`; после перезапуска MCP-клиента он должен стать первым read-tool
  перед глубокими запросами. Ручной запуск `python -m app.adapters.mcp.server` в отдельном терминале
  сам по себе не подключает Codex/Claude — stdio-сервер должен быть запущен MCP-клиентом.
- Публикация сайта: добавлен runbook `!DOC/operations/PUBLISHING_SITE.md`. Домен покупать не обязательно.
  Рекомендуемый no-domain путь для семьи — Tailscale Serve (`https://<machine>.<tailnet>.ts.net`);
  временный публичный путь — Cloudflare Quick Tunnel; стабильный публичный путь позже — Cloudflare
  Tunnel + Access и домен.
- Frontend/public mode: добавлен `VITE_OPERATOR_MODE_AVAILABLE`. При `false` операторский toggle
  скрывается, а `/operator` не показывает операторскую поверхность. `docker-compose.yml` и
  `frontend/Dockerfile` прокидывают этот build arg; `.env.example` документирует флаг и
  `PUBLIC_FRONTEND_BASE_URL`.
- Публикация начата live (2026-07-09): Cloudflare Quick Tunnel через Docker выдал
  `trycloudflare.com` URL, но не смог установить соединение — в сети заблокирован outbound к
  Cloudflare Tunnel edge (`7844`, QUIC/TCP). Установлен Tailscale `1.98.8`; host уже авторизован
  в tailnet как `100.113.226.52`. Tailscale Serve config из CLI зависает в этом Windows-окружении,
  поэтому текущий рабочий no-domain URL: `http://100.113.226.52:8088`.
- Runtime update: локальный `.env` переключён на
  `PUBLIC_FRONTEND_BASE_URL=http://100.113.226.52:8088` и `VITE_OPERATOR_MODE_AVAILABLE=false`;
  `web` пересобран, `bot` перезапущен и видит эти env values. Доступность проверена:
  `curl http://100.113.226.52:8088/api/health` → `{"status":"healthy"}`; release smoke GREEN.
- Verification: targeted pytest `26 passed`; full backend pytest `206 passed`; frontend
  `npm.cmd run build` OK; ruff по затронутым файлам с `--ignore E501` clean. Широкий ruff всё ещё
  падает на 4 старые E501 в `mcp/server.py` и `use_cases.py`, не связанные с этим слайсом.
- Хвост: устройство ученицы должно быть в том же Tailscale tailnet; тогда ссылка
  `http://100.113.226.52:8088` откроется. Остановить вручную запущенный MCP terminal (`Ctrl+C`) и
  перезапустить MCP-клиент/Codex/Claude, чтобы новый tool contract загрузился.
- Добавлена инструкция для ученицы: `!DOC/operations/STUDENT_SITE_ACCESS.md` — куда нажимать в
  Tailscale, какие ссылки открывать (`/program`, `/daily`, `/slice`, `/review`, визуализация по
  векторам) и что написать родителю, если сайт не открывается.
- Security hardening после публикации: `docker-compose.yml` теперь биндует `api` и `postgres`
  только на `127.0.0.1`; внешней/tailnet-точкой остаётся только `web` на `8088`. Проверено:
  `curl http://100.113.226.52:8088/api/health` OK, release smoke GREEN.

## Current Snapshot (2026-07-09, visual feedback hardening)

- Реализовано (Codex): минимальный hardening по реальной обратной связи ученицы “визуализация не открывается”
  и по текущему дриллу “Векторы — скалярное произведение”.
- Telegram: прямой URL на `/theory/<topic_id>` теперь отправляется только если `PUBLIC_FRONTEND_BASE_URL`
  выглядит публичным. Для `localhost`, `.local`, loopback/link-local/private IP (`192.168.x.x`) бот пишет
  коротко: `Визуализация есть на сайте: «Программа» → эта тема.` Это убирает битые LAN-ссылки у ученицы.
- Telegram UX: `_task_text` больше не добавляет общий хвост “кратко распиши ход...” поверх уже заданных
  `instructions`, поэтому дриллы формата “отправь ответ числом” не получают противоречивую вторую инструкцию.
- Content/frontend: в seed добавлена approved concept card `Скалярное произведение в координатах`
  (`vector_dot_product`) для темы `Векторы`; frontend `/theory/:topicId` получил простой SVG-рендер
  формулы `a·b = x1·x2 + y1·y2`. Сортировка карточек теперь по title, поэтому scalar-product карточка
  идёт первой, без новой skill-tag модели.
- Verification: targeted pytest `28 passed`; full backend pytest `205 passed`; frontend `npm.cmd run build` OK;
  targeted ruff по `bot.py`/bot+theory tests clean; release smoke GREEN.
- ВЫКАЧЕНО live (2026-07-09): `docker compose up -d --build api`, `alembic upgrade head`,
  `python scripts/seed.py`, `docker compose up -d --build bot web`. Live API по векторам отдаёт две карточки
  (`vector_dot_product`, `vector_2d`), live bot-text не содержит `192.168`, web `/theory/...5012` отдаёт 200.
- Хвост: reconnect ege-MCP. Текущий MCP-процесс всё ещё держит старый контракт: `topic_theory` tool не виден,
  а `program_progress` не отдаёт `visual_ready`, несмотря на обновлённые live API/bot/web. После reconnect проверить
  `program_progress`/`topic_theory`.

## Current Snapshot (2026-07-08, visual concept cards v1)

- Реализовано (Codex): безопасные визуальные concept cards до попытки, отдельно от `/ready`
  (`theory_ready` = ученик отметил теорию изученной; `visual_ready` = по теме есть approved
  визуальная карточка). Содержимое не содержит ключей ответов и не является task-specific
  разбором.
- Backend: новая таблица `theory_cards` (alembic `e6f7a8b9c0d1`), репозиторий/порт
  `theory_cards`, `LearningService.list_topic_theory`, API `GET /topics/{topic_id}/theory`,
  `visual_ready` в `program_progress`, mission payload и slice draw payload. MCP получил read-tool
  `topic_theory(topic_id)`; `program_progress` автоматически отдаёт `visual_ready`.
- Content seed: approved карточки для двух тем из реального запроса ученицы:
  `Векторы` (`vector_2d`) и `Производная: геометрический смысл` (`derivative_tangent`).
- Telegram/site: `/today` и `/slice` добавляют ссылку `PUBLIC_FRONTEND_BASE_URL/theory/<topic_id>`
  при `visual_ready`; сайт получил маршрут `/theory/:topicId` с локальными SVG-рендерами,
  ссылки из «Программы», «Сегодня» и «Среза».
- Verification: backend pytest `204 passed`; frontend `npm.cmd run build` OK; Docker web build OK;
  release smoke GREEN; ruff clean на новом `backend/tests/test_theory_cards.py`. Широкий ruff по
  старым изменённым backend-файлам всё ещё шумит существующими B008/E501 в routes/seed/use_cases,
  не связанными с этим слайсом.
- ВЫКАЧЕНО live (2026-07-08): `docker compose up -d --build api`, `alembic upgrade head`
  (`e6f7a8b9c0d1`), `python scripts/seed.py`, затем `docker compose up -d --build bot web`.
  Контейнеры running/healthy; `/theory/00000000-0000-0000-0000-000000005012` отдаёт 200;
  live service check показал `visual_ready=True` для `Векторы` и `Производная: геометрический смысл`.
- Хвост: reconnect ege-MCP. Текущий MCP-процесс в этой сессии держит старый код: `topic_theory`
  tool не виден, а `program_progress` ещё не отдаёт `visual_ready`. После reconnect проверить MCP
  `program_progress` + `topic_theory`.

## Current Snapshot (2026-07-07, /ready: теория изучена → приоритет очереди)

- Реализовано (Claude): отметка ученика «/ready — теорию изучила, готова решать» как
  сигнал приоритета сборщика дня. Выведено из реального случая: очередь пуста, ребёнок
  просит векторы/движение (июньская фаза — сборщик их не видел), а июльская фаза могла
  выдать стерео/параметр против её просьбы.
- Механика: `topics.theory_ready_at` (миграция `d5a6b7c8e9f0`); правило в
  `build_daily_queue` — есть хоть одна отметка → новые дриллы ТОЛЬКО по отмеченным темам
  любой начавшейся фазы, неотмеченные темы текущей фазы придерживаются; нет отметок —
  прежнее поведение. Отметка — сигнал приоритета, НЕ evidence (закрытие тем не меняется).
- TG: команда `/ready` + кнопка в меню («📖 Готова к новым темам»), inline-toggle тем,
  manual-path темы (стерео/параметр/№13–18) в кандидаты не попадают. `theory_ready`
  прокинут в `program_progress` (API/MCP) для бейджа на «Программе».
- Verification: backend pytest `198 passed`; ruff по затронутым файлам чист.
- ВЫКАЧЕНО live (2026-07-08): `alembic upgrade head` (`d5a6b7c8e9f0`, theory_ready_at)
  применён к БД; `docker compose up -d --build api bot web`. api/bot `healthy`, `/program`
  отдаёт `theory_ready`, runtime-smoke GREEN.
- Три UI-задачи (были «Кодексу») СДЕЛАНЫ Claude 2026-07-08 (pytest 198, tsc/ruff чист):
  1. TG пустая очередь → «На сегодня всё сделано ✅ Новая порция — завтра утром» (тест обновлён).
  2. TG `/progress`: карта фазы — «📚 Фаза «label» (дд.мм–дд.мм)», «Закрыто X из Y · в работе
     · на повторении», «Дальше: …» (до 3 открытых тем).
  3. Сайт «Программа»: бейдж «📖 теория изучена»; `theory_ready` добавлен в `ProgramTopicOut`
     (pydantic его резал), TS-тип и CSS `badge--ready`.
- Хвост: переподключить ege-MCP (держит код до `telegram_send`), затем live-проверить
  MCP `publish_feedback`→ТГ, `/send` из родительского чата, `/ready`-тоггл + бейдж.

## Current Snapshot (2026-07-04, AI-judge calibration baseline)

- New instrument: `backend/scripts/calibrate_ai_judge.py` (+5 tests) — offline-replay
  калибровка `LlmShortAnswerJudge` против детерминированного exact-авторитета по протоколу
  expert-agent ADR-013 (kappa-математика скопирована оттуда, VERSION 1.0). Exit non-zero
  при judge-failure-rate > 10% → готов как weekly night-runner task (no-prompt acceptance).
- Baseline (25 unique triples / 27 attempts, judge failures 0):
  - raw judge vs raw exact: agreement 0.36, kappa 0.04 — низкий ПО ДИЗАЙНУ: почти все
    ответы формата «покажи ход», raw exact совпал лишь на 1/25; судья и существует для
    этого разрыва.
  - guardrail-декомпозиция: из 16 judge-«спасений» **14 заземлены** extracted-ответом
    (прод принял бы законно), **2 opinion-only — прод отверг бы** (fail-closed held);
    false negatives 0 (судья не бракует верное).
  - продуктовые находки: (a) unit-синонимы «768 кб» vs «768 Кбайт» — exact промахивается
    на верном ответе → кандидат в `normalize_answer`; (b) code-задачи с описательным
    эталоном структурно не подходят short-answer политике — зона MANUAL_GATE, не exact.
- Next:
  1. Human_verdict по 14 grounded-спасениям в `backend/data/ai_judge_disagreements.jsonl`
     (~10 мин, поле `human_verdict: judge_right | exact_right` прямо в файле).
  2. Добавить `calibrate_ai_judge.py` в weekly night queue (перезапуск по мере роста данных).
  3. Малый slice: unit-синонимы (кб/Кбайт/КБ) в `normalize_answer` + тесты (Codex/Qwen класс).
- Codex follow-up 2026-07-04:
  - `backend/scripts/night_runner.py` синхронизирован с каноном expert-agent v1.1:
    VERSION=1.1, `.env` копируется из корня репо в worktree, acceptance/executor пишут
    full-log в `logs/<task>/`, отчёт показывает хвост `LOG_TAIL_CHARS=3000`; ege-пути и
    `C:\tmp\egeMentor-qwen-runs` сохранены.
  - `normalize_answer` теперь сводит синонимы единиц информации: `кб|кбайт|kb`,
    `мб|мбайт|mb`, `гб|гбайт|gb`; одиночная `б` не нормализуется.
  - Weekly queue получила no-prompt gate `T-calibrate-ai-judge` с acceptance
    `backend/scripts/calibrate_ai_judge.py --max-failure-rate 0.1` и `files_allowed`
    только для `data/ai_judge_disagreements.jsonl`.
  - Проверка baseline rerun: кодовый exact-case `answer_is_correct("768 кб", "768 Кбайт")`
    исправлен тестами, но live calibration rerun 2026-07-04 не дал валидной дельты:
    LLM endpoint из `.env` (`http://192.168.0.18:8000/v1`) недоступен, judge returned
    None 25/25 (`failure_rate=1.0`, rc=1). Дополнительно текущая replay-тройка в БД
    содержит полный текст решения, начинающийся с `768 кб, ...`, поэтому raw exact
    остаётся `False` без отдельного извлечения финального ответа.
  - Import-linter package B 2026-07-05: backend получил два layering-контракта в
    `backend/pyproject.toml` (`app.domain` не импортирует `app.infrastructure /
    app.adapters / app.application`; `app.application` не импортирует `app.adapters`),
    `import-linter` добавлен в `dev`, weekly queue получила `T-lint-imports`.
    Под эти контракты кодовых нарушений нет; `importlinter`/`grimp` пришлось посадить в
    локальную `.venv312` копированием из соседней venv, потому что `pip install -e .[dev]`
    упёрся в сетевой/proxy deny.

- Codex follow-up 2026-07-06:
  - Closed Qwen backend findings from the night run: part-2 #13 seed now uses the math topic
    `Задача 13: тригонометрическое уравнение`, and part-2 manual-gate missions take `topic_id`
    from their linked task to prevent task/mission drift.
  - Manual-gate lifecycle is covered through submit -> manual-review queue -> manual PASSED ->
    mission DONE -> +7/+30 reviews; resolved manual-review evidence no longer stays visible in
    the pending queue.
  - Added pure `select_intervention_queue(...)` with repeated actionable category count >=2 and
    `none`/`other` ignored. It is intentionally not wired while the deterministic intervention
    rule remains frozen.
  - Weekly `T-lint-imports` command now invokes `importlinter.cli`.
- Ops follow-up 2026-07-07:
  - Telegram bot polling recovered by restarting only `bot` after repeated proxy/update failures.
    Direct Telegram access from the container still times out, so the configured proxy remains required.
    Fresh logs stayed clean after restart and `getMe` via proxy returned OK.
  - Daily-mission recovery applied live through the MCP server: due review cards through
    2026-07-07 were marked passed, 5 stale open `daily:` missions were closed with
    `operator-recovery` evidence, and 4 accidental part-2 daily drills were retired as
    `skipped`.
  - MCP now has narrow operator tools for this class of recovery:
    `operator_close_daily_missions` and `operator_skip_daily_missions`. `build_daily_queue`
    now excludes current part-2/manual-review topics from auto daily drills.
  - Regression guard added: bot now has an in-process polling-failure watchdog, a Docker healthcheck
    for Telegram `getMe`, and a host-side `telegram_bot_runtime_smoke.py` for service/log/getMe checks.
    Live `api`/`bot` were rebuilt/recreated; Compose reports `bot` as `healthy`, release smoke is GREEN,
    and runtime smoke is GREEN.
  - Local service stack check: `docker compose up -d` confirmed `postgres`, `api`, `web`, and `bot`
    running; API health returned `healthy`, Docker web answered on 8088, and Vite dev frontend is
    running through scheduled task `egeMentorFrontendDev` at 5174.
  - Live Telegram slice check via MCP: the bot did process the learner's percent-slice answer and
    returned a verdict, but in-progress slice answers are held in the bot's `_srez` session and only
    persist via `record_slice` after the final task. MCP should show the completed slice in
    `diagnostics` / `weekly_digest`, not as individual `attempt_history` rows.

- Notes delivery unified 2026-07-07:
  - New `app/infrastructure/telegram_send.py` `deliver_pending_notes(...)` is the single delivery
    function (sync urllib+proxy, no aiogram, self-contained). Wired into MCP `publish_feedback`
    (instant, hard-fail), API `publish_mentor_note` (web operator form, HTTP 502 on delivery fail),
    and the bot morning push (now calls it via `asyncio.to_thread`; old aiogram
    `_deliver_mentor_notes`/`_notify_parent`/`_split_for_telegram` removed).
  - Parent manual TG channel: bot command `/send <text>` (parent chat only) publishes + delivers.
  - Frontend token gate removed (`App.tsx`) and `.env` `API_SHARED_TOKEN` blanked (temporary).
  - Verify: pytest 191 passed. NOT live yet — needs `docker compose up -d --build api bot` and an
    MCP server reconnect (running MCP holds pre-change code).
- Goal: execute the proven-delta strategy with verified small steps: monthly timed score events, weekly error-to-intervention review, part-2 manual-gated evidence, targeted content depth, and Qwen only as a bounded read-only/mechanical executor.
- Status: latest completed live nightly batch `C:\tmp\egeMentor-qwen-runs\2026-07-03\report-093450.md` is 4/4 GREEN. The part-2 text-only manual-gate slice is committed as `4294d09`; the MANUAL_GATE real-reviewer regression and sandbox simulator case are committed as `34e1f75` and verified by live Qwen. Retention KPI v1 is implemented locally: dashboard exposes weekly active days and a Wednesday risk alert.
- Current operating rules:
  - keep `current_score` tied to timed score events, not daily attempts;
  - start error intervention manually via `error_journal` + `publish_feedback`;
  - keep deterministic repeated-error intervention frozen until 2-3 weeks of observed weekly-review data;
  - keep Qwen as bounded read-only/mechanical QA: nightly synthetic QA + post-change reports, no content, no write-path, no senior MCP.
  - retention is a first-class operating signal: by Wednesday, fewer than 3 active days is an operator-facing dashboard risk.
- Triage of nightly batch 093450:
  - accepted: sandbox `manual_gate_text_solution`, sandbox MCP contract, error-intervention readiness, and part-2 post-change checks are GREEN;
  - no urgent code: suggested sandbox expansions (attempt-mode comparison, threshold close, error-category journal propagation) are useful later but not blockers;
  - future blocker before deterministic intervention: slice/srez errors currently land as `other`, and `other` already dominates `top_errors` (6); add a small Codex slice to categorize srez errors before using `top_error_category` for routing;
  - note for later operator work: when mission-create/edit UX grows part-2 support, guard against accidentally creating `part2:text:*` missions with `ATTEMPT_FIRST`;
  - skip/low: `publish_feedback` weekly dedup test, Part2Page empty-state/filter test, task 4071 wording check before first real part-2 session.
- Next:
  1. Commit the retention KPI v1 slice.
  2. Schedule/record the first July timed mini-mock as the score baseline.
  3. Start the weekly mentor review from `error_journal` and recent attempts.
  4. Deploy/reseed live data if the new #13/#15 manual-gate missions should affect the learner now.

## Current Snapshot (2026-07-03)

- Goal: execute the proven-delta strategy with verified small steps: monthly timed score events, weekly error-to-intervention review, part-2 manual-gated evidence, targeted content depth, and Qwen only as a bounded read-only/mechanical executor.
- Status: strategy accepted; canonical plan is aligned from the old LAN/scaffold next-plan to the three-horizon proven-delta plan. Latest completed live nightly batch `C:\tmp\egeMentor-qwen-runs\2026-07-02\report-235647.md` is 4/4 GREEN (plumbing, sandbox contract, error-intervention readiness, part-2 post-change QA). Score-spine visibility is implemented and committed in `edcaa70`. Qwen follow-up gate fix is committed in `9c4ad0b`. Night queue is now split: nightly core stays compact; broad surface reports moved to `backend/scripts/night_queue_weekly.json`. The first part-2 text-only manual-gate slice for #13/#15 is committed as `4294d09`; the follow-up MANUAL_GATE real-reviewer regression and sandbox simulator case are implemented locally.
- Current operating rules:
  - do not scale infrastructure or multi-student support until an N=1 delta is visible;
  - keep `current_score` tied to score events from timed mocks, not daily attempts;
  - start error intervention manually via `error_journal` + `publish_feedback`, then add a simple deterministic queue rule only after observed repetition;
  - use Qwen through `backend/scripts/night_runner.py` for read-only reports, smoke checks, and mechanical edits with machine gates.
- Current Qwen report triage:
  - done: timed mock score history is visible (`list_score_events` + dashboard trend + weekly digest score block);
  - done from latest report: sandbox MCP boundary is safe; no senior mentor MCP write tools in Qwen prompts;
  - fixed after latest report: score-spine Qwen acceptance no longer depends on missing frontend `node_modules`; added regression coverage that `topic_check` score events do not move `current_score`;
  - queue freshness finding implemented: nightly keeps plumbing + sandbox/error-intervention/part2; visualization, slice/review, Telegram, bank coverage, analytics, release-smoke, and score-spine postchange are weekly/change-triggered;
  - keep Qwen out of senior mentor MCP and real student-state write tools; sandbox MCP only exposes deterministic synthetic simulation;
  - process first: start weekly `error_journal` review and publish feedback manually before coding intervention routing;
  - part 2 first slice implemented: text-only submitted solution with manual verdict gate for #13/#15 before photo/OCR UX;
  - part 2 follow-up implemented: MANUAL_GATE is regression-tested through `RuleBasedReviewer`, and sandbox `run_student_simulation()` includes `manual_gate_text_solution`;
  - low-priority test gaps: bar-chart correct-answer simulator case, double-PASS review idempotency, slice/daily duplicate guard, extra Telegram callback/media/streak tests.
- Triage of nightly batch 235647 (2026-07-03):
  - done locally: MANUAL_GATE fail-closed regression through the real reviewer path + sandbox simulator `manual_gate` case so nightly QA guards the part-2 invariant;
  - design constraint for the frozen intervention rule: `top_error_category` must require a minimum count (>=2) before triggering anything;
  - low/skip: `publish_feedback` weekly dedup test (manual gate mitigates), Part2Page empty-state UX and filter test, task 4071 statement wording — operator checks wording at the first real part-2 session.
- Next:
  1. Commit the MANUAL_GATE reviewer-path + sandbox simulator follow-up.
  2. Deploy/reseed live data if the new #13/#15 manual-gate missions should affect the learner now.
  3. Schedule/record the first July timed mini-mock as the score baseline.
  4. Start the weekly mentor review from `error_journal` and recent attempts.
  5. Keep deterministic repeated-error intervention frozen until 2-3 weeks of observed weekly-review data.

## Current Snapshot (2026-07-01)

- Goal: add a safe local-Qwen execution harness for small, falsifiable overnight tasks.
- Status: Qwen harness is calibrated and documented; probability visuals are integrated; sandbox MCP/student-flow simulator covers interval visuals, probability bar chart, probability 2x2-table wrong answers, and probability 2x2-table correct-answer happy path for read-only Qwen reports.
- Done:
  - ported the night-runner queue shape to egeMentor-local paths;
  - added `files_allowed` enforcement before acceptance/commit;
  - fixed venv autodetect to ignore broken venvs without `pyvenv.cfg`;
  - moved run artifacts to external `C:\tmp\egeMentor-qwen-runs` and made reports per-run.
  - added a main-worktree contamination check around live executor runs.
- Current Qwen queue tasks: six read-only Qwen reports are queued after plumbing: visualization surface, slice/review lifecycle, Telegram learner flow, bank/content coverage, analytics/digest, and release-smoke readiness. Any file change by Qwen makes a report task RED.
- Latest live report: `C:\tmp\egeMentor-qwen-runs\2026-07-02\report-102003.md`: full Qwen read-only QA batch GREEN.
- Done from Qwen findings: added TG tests for post-attempt visual photo delivery, `/cancel` during active slice, unauthorized callbacks, and `/help`; made failed review result idempotent so repeated FAIL does not create duplicate back-to-work missions; made probability visual captions specific for bar-chart vs 2x2-table cases; expanded the probability bank from 3 to 10 approved tasks.
- Verification: probability bank focused tests `9 passed`; backend pytest `165 passed`; frontend `npm.cmd run build` green; `night_runner.py --dry-run` GREEN across all queued tasks.
- Next: commit probability bank expansion. Then either deploy/reseed live DB or continue content expansion with math foundations / informatics gaps.

## Current Snapshot (2026-06-30)

- Goal: improve pilot service reliability and analytics after the product/pedagogy review.
- Status: implemented the first two high-leverage items: safer exact-answer grading and a read-only weekly digest.
- Done:
  - grouped integer answers such as `7.776` are accepted for integer keys like `7776`;
  - decimal approximations such as `0.667` still do not override exact numeric mismatch;
  - diagnostics expose whether solution details were captured;
  - `LearningService.weekly_digest()` and MCP `weekly_digest` summarize recent attempts, active days, slices, errors, reviews, and manual queue.
- Verification: backend pytest `124 passed`; frontend `npm.cmd run build` green.
- Next: review the weekly mentor-note draft from the 2026-06-23..2026-06-30 digest; do not publish to TG until the operator approves the text. Then clear the 2 old manual-review OДЗ items.

> Короткая текущая карточка. История/детали — `SESSION_LOG.md` (верх) и
> код/контракты — канонические docs в `docs/` и `AGENTS.md`.

Запрещено:

- вести параллельные постоянные task logs;
- считать временные заметки отдельной историей проекта.

Запись в `SESSION_LOG.md` должна быть короткой:

- задача и статус;
- 3-6 пунктов по сути;
- проверка;
- открытый хвост, если он есть.

`ACTIVE_TASK.md` обновлять когда меняется цель, состояние, ключевые решения или следующие шаги.

## 3. Единый рабочий цикл

1. стартовать с одного набора источников (п. 1 + ACTIVE_TASK.md);
2. исследовать код только после этого;
3. завершать работу обновлением `ACTIVE_TASK.md` и короткой записью в `SESSION_LOG.md`;
4. обновлять канонические docs только если реально изменился active flow или контракт.

## 4. Simplicity First (обязательно)

Сложность накапливается необратимо. Каждое изменение должно уменьшать сложность или оставлять её прежней.

- Не вводи абстракции, параметры и слои "на будущее" — только под реальную текущую задачу
- Прячь неизбежную сложность за узким интерфейсом — снаружи просто, внутри можно сложно
- Три похожих строки лучше преждевременной абстракции
- Если код можно удалить без последствий — удали

## 5. Граф вместо разведки

Перед тем как тратить токены на разведку кода (Glob/Grep/чтение файлов по подозрению) — сначала смотри карту в `graphify-out/GRAPH_REPORT.md`. Она уже знает архитектуру, god nodes и связи. Лезь в код только когда граф не даёт ответа.

---

## Текущая карточка

- Цель: Telegram — канал ежедневного дрилла части 1 + повторов; сайт — части 2 + витрина-контролёр. Бэкенд сам решает что слать (повторы вперёд, новые темы фазы — в остаток лимита).
- Статус: **Phase 1 + Phase 2 реализованы и зелёные (pytest 92 passed)**. Phase 1: мгновенная точная проверка, `list_daily_drill`, in-process бот (aiogram через прокси), флаг `drill` в MCP. Phase 2: `build_daily_queue` (повторы→новые, carry-over, дедуп, `shortage`), `select_daily_queue` (policy), `list_approved_for_topic` (свежая=не назначавшаяся), корректный lifecycle повтора + разрешение back_to_work (option A), обязательный chat_id + онбординг, идемпотентный утренний пуш, MCP-инструмент `build_daily_queue`. **Вживую (пуш/чат после Phase 2) не прогнано.**
- Ключевые решения: бот = in-process adapter; маркер дрилла = `source_ref` (`daily:new:<topic>`/`daily:review:<card>`/`daily:manual`); review-PASS закрывает карточку без новых +7/+30; back_to_work передриллится свежей задачей → DONE; пустой банк → явный `shortage` (не молчаливый недобор).
- Срез по теме: **готов и live** (docker api+web). На странице «Срез знаний» — дропдаун «Тема»; проверка по ключу; диагностика подписана темой. Семантика `topic_check`.
- **Срез в TG + ИИ-приём ответов: реализовано и задеплоено live.** Курс: TG = ученический тренажёр, сайт = витрина (фронт не трогали). Общий `ShortAnswerJudge` (порт `assess→AiAssessment`, политика exact-авторитет в `_grade_answer`); API/MCP детерминированы (ExactOnly), ИИ только в боте (`LlmShortAnswerJudge`, `show-work-v2`). `judge_task_answer`/`record_slice` (аудит `details_json`, миграция `b8e4f1a2c3d9`). Бот: `/slice`→предмет→тема→по одной с ИИ-фидбеком, `/cancel`. Docker: сервис `bot` + `[bot]` extra (live: `llm ON`, `getMe OK`).
- **Формат «покажи ход» + мульти-чат:** бот просит расписать решение; LLM извлекает финальный ответ (заземляет вердикт) + оценивает метод (флажит «верный ответ, неверный метод»). Авторизация — список (`telegram_extra_chat_ids`); родитель `1682176470` добавлен в `.env`, live-контейнер видит оба ID; ученик — цель пуша.
- **TG UI/UX v1: реализовано и задеплоено live.** Нативные команды `/start`, `/today`, `/slice`, `/progress`, `/help`, `/cancel`; `/start` = главное меню с inline-кнопками, `/today` только читает backend-очередь, произвольный текст не запускает задания. Срез получил возврат к предметам и чистую замену inline-сообщений; прогресс берётся из `get_dashboard`. Host `HTTPS_PROXY` передаётся только в `TELEGRAM_PROXY_URL` bot-контейнера. Live: `getMe OK`, меню команд подтверждено через Telegram API. Детский smoke выявил два P0-дефекта грейдера: противоречивый positive-feedback после sanitize и потерю extracted-correct при повторном подсчёте среза.
- **Short-answer кластер РЕАЛИЗОВАН (A/B/C):** противоречие `✅ Верно!`/`Близко` снято (`_sanitize_feedback`→`_mask_answer`: маскируем эталон, разбор сохраняем); `record_slice` не теряет extracted-correct и не пишет ложные error-events (метка `exact` только для raw, извлечённый верный → `llm_equivalent`); детерминированное сравнение чисел/дробей через `Fraction` + запрет ИИ переопределять доказанное неравенство (`0,667≠2/3`, в т.ч. через «извлечённый» эталон). EvidenceReviewer миссий не трогали. `pytest` 112 passed, ruff чист, +3 регресс-теста.
- **Наставнические заметки в TG реализованы + pre-live правки по review сделаны:** агент пишет заметку через `publish_feedback`, бот доставляет её утренним пушем (`mentor_notes.delivered_at`, миграция `c0d1e2f3a4b5`). Закрыто: миграция бэкфилит существующие как доставленные (старьё не уйдёт); `_morning_push`→try/except+`_run_daily_push` (сбой не убивает цикл); `_split_for_telegram` режет текст ≤4096. Семантика — at-least-once (редкий дубль при краше send↔commit допустим для пилота). `pytest` 114 passed.
- **Release-smoke готов:** `scripts/release_smoke.py` (health + миграции код-head vs БД + бот getMe + живой Qwen-judge; read-only, без сообщений ученику; exit code). Прогон против live: health/getMe/judge OK, миграции RED (БД `b8e4f1a2c3d9` < код `c0d1e2f3a4b5`) — деплой не сделан. Реальную доставку ученику в автотест не прячем (необратимый outward); логика доставки/грейдинга уже e2e в pytest.
- **Контролёрская видимость заметок:** `delivered_at` выведено наружу — на дашборде («Обратная связь наставника») бейдж «✅ отправлено ученику <дата> / ⏳ ожидает» + полная история; при доставке родителю (`telegram_parent_chat_id`) уходит Telegram-пинг с превью. Гейт публикации — ручной (агент→ОК→публикация→авто-доставка). `pytest` 115 passed, фронт tsc ок.
- **ЗАДЕПЛОЕНО (24.06), смок GREEN:** миграция `c0d1e2f3a4b5` применена, api/web/bot на новом коде, Qwen-judge живой.
- **Полный отчёт-заметка доставлен Ульяне (24.06):** одна заметка `4c2d85ed` — мотивирующая часть сверху + подробная аналитика ниже; отправлена сразу (host-запуск `_deliver_mentor_notes`), `delivered_at`=11:40 → дашборд «✅ отправлено», пинг родителю (если задан `TELEGRAM_PARENT_CHAT_ID`). Утренняя короткая `131481a4` удалена по явной команде (одна чистая заметка). Ручную кнопку на сайте решили НЕ делать (YAGNI; поток «попроси агента → ревью → публикация» достаточен).
- **Снижение тревоги — язык прогресса (25.06, ЗАДЕПЛОЕНО, смок GREEN):** коммит `87533fd`; `up -d --build api web bot` (миграции не было — схему не меняли). Проверка боевого API: `/program` current-phase `coverage.under_review=7`; web HTTP 200; bot свежий образ, RestartCount=0. Фикс overlap (ревью Codex): «в работе» = `in_progress − under_review` (корзины непересекающиеся), +guard-тест. Дашборд показывал `confirmed=0 / 0%` → ребёнок слышит «ничего не закрыла». Меняли язык, не модель (ревью Codex). `coverage`+`under_review`; фронт «Программа» ведёт с «в работе/на повторении/подтверждено» (полоса = «затронуто» = total−open), не с «0%»; TG `/progress` — строка активности по текущей фазе. Правило «зачтено» (верная задача + повтор, не «100%») — на странице и в `/progress`. #1 (повтор другой задачей) **в коде уже корректен** (свежая задача / `shortage`, старую не переиздаёт) — блокер контентный (тонкий банк). #4/#5 (олимпиадные, полный разбор) отложены из кода — словами/ручной заметкой. `pytest` 115, tsc ок.
- **Банк математики Ч1 наполнен (25.06):** +36 задач через MCP (`add_task`→`approve_task`), 12 тем июня math `3→6/тема`. Ответы проверены вычислением (`scratchpad/gen_math.py`, анти-poison). Анблок #1: в темах появились неназначавшиеся siblings для «повтора другой задачей». Часть 2 (№13/14/16/17/18) не трогали (символьный ответ). Осталось по математике: при желании — июльские темы (экономика/стерео/планиметрия/параметр, по 3) и интервальные (Неравенства/ОДЗ).
- **Банк информатики (Python) наполнен (25.06):** +28 задач, 7 ядровых Python-тем по +4 (basics/arithmetic/conditions/for/while/strings/lists). Формат: «что выведет» (трассировка) + «напиши и дай число»; ответ = реальный stdout прогона (`scratchpad/gen_inf.py`). Итог: 5/5/5/5/4/5/4. Всего в банке 142 задачи.
- **Визуализация — фигура решения в drill-разборе (29.06, ЗАДЕПЛОЕНО, live-проверено):** коммит `d90a826`. Принцип: фигура — чистая функция эталона/условия, ИИ в рисовании нет; **показ только после попытки** (до — утечка ключа). Числовая прямая по интервальному ответу (неравенства/ОДЗ). `domain/figures.py` = чистый `parse_interval_answer` (leak-safe), `infrastructure/figures_render.py` = `render_number_line` (matplotlib, вынесен из domain), `LearningService.drill_solution_figure(mission_id)` отдаёт PNG post-attempt, бот `_on_answer` шлёт фото. Парсер не уверен → фигуры нет. matplotlib в extra `[bot]`. Live: рендер в прод-контейнере (кириллица ок, 8244B) + доставка из бота в родительский чат. Решения по ресёрчу: движок не пишем — web-интерактив = **JSXGraph** (MIT), 3D = **GeoGebra** embed (non-commercial!), оба отложены до доказанной потребности; `figure_json` на задаче не вводим (потечёт до попытки); OSS — только после пользы в пилоте ([[scenario-gate-oss-plan]]).
- **Банк информатики part-1 наполнен (29.06):** +28 задач, 7 верифицируемых тем по +4 (системы счисления, информ. объём, логика 1→5, делители №25, пути в графе, рекурсия-трассировка, кодирование Фано). Ответы посчитаны кодом (`scratchpad/gen_inf2.py`). Информатика всего 65 одобренных, в банке 170. Визуальные темы (диаграммы/БД/Excel/файл/теория игр) отложены — нужен другой канал.
- Следующие шаги: (1) **наблюдать визуализацию** на 3–5 дрилл-неравенствах; помогает → второй рендерер, нет → не расширять (решение пользователя); (2) визуальные информ-темы (диаграммы/БД/Excel) — отдельным каналом, когда дойдёт; (3) после 16:00 МСК проверить доставку/бейдж/пинг (`delivered_at`); задать `TELEGRAM_PARENT_CHAT_ID`; (4) единая политика на пути миссий (не зануляй верный ответ за метод); (5) часть 2 на сайте; (6) ревизия сайта; (7) погасить теневой uvicorn на host:8001.
