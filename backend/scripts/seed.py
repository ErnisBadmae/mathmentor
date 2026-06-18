"""Bootstrap demo data for local development.

Creates one guardian user, one student profile (using the all-zero UUID the
frontend defaults to via VITE_STUDENT_ID), two subject tracks matching the
baseline from AGENTS.md, and a handful of active missions so the dashboard
and daily-work screens have something to show. Safe to re-run: it skips
records that already exist instead of duplicating them.
"""

from datetime import UTC, date, datetime
from uuid import UUID

from app.domain.enums import AiPolicy, ErrorCategory, MissionStatus, Role, Subject, TaskStatus
from app.infrastructure.db import SessionLocal
from app.infrastructure.models import (
    CleanSheetEventORM,
    ErrorEventORM,
    MissionORM,
    ScoreEventORM,
    StudentProfileORM,
    StudyLogEntryORM,
    SubjectTrackORM,
    TaskORM,
    TopicORM,
    UserORM,
)

DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DEMO_STUDENT_ID = UUID("00000000-0000-0000-0000-000000000000")

TOPICS = [
    (Subject.MATH_PROFILE, "Уравнения и неравенства с ОДЗ", "15"),
    (Subject.MATH_PROFILE, "Текстовые задачи на проценты", "11"),
    (Subject.INFORMATICS, "Анализ алгоритмов и сложность", "16"),
    (Subject.INFORMATICS, "Работа со строками", "6"),
    (Subject.MATH_PROFILE, "Вероятность: теорема сложения", "4"),
    (Subject.MATH_PROFILE, "Неравенства", "15"),
    (Subject.INFORMATICS, "Python: Thonny, переменные и ввод-вывод", "python-basics"),
    (Subject.INFORMATICS, "Логика: таблицы истинности", "logic"),
    (Subject.INFORMATICS, "Python: арифметика, типы, %, //", "python-arithmetic"),
    (Subject.INFORMATICS, "Python: условия if/elif/else", "python-conditions"),
    (Subject.INFORMATICS, "Python: цикл for и range", "python-for"),
    (Subject.INFORMATICS, "Кодирование изображений и звука", "encoding"),
    (Subject.INFORMATICS, "Комбинаторика: подсчёт слов и чисел", "combinatorics"),
]

# Учебная программа (фазы из app/domain/program.py): (phase_key, subject, title).
# Темы с совпадающим названием переиспользуются (получают фазу), недостающие создаются.
# Гранулярно: июнь (Срез 1) + июль–август (Срез 2/3). Источник — папка `контроль`.
PROGRAM = [
    # --- Июнь · Диагностика (математика) ---
    ("june_diagnostics", Subject.MATH_PROFILE, "Вероятность: теорема сложения"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Вычисления: степени и корни"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Вычисления: логарифмы и тригонометрия"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Простейшие уравнения (показательные, логарифмические)"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Производная: геометрический смысл"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Производная: физический смысл"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Применение производной: экстремумы"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Текстовые задачи: движение"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Текстовые задачи на проценты"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Планиметрия (Часть 1)"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Стереометрия (Часть 1)"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Векторы"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Задача 13: тригонометрическое уравнение"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Задача 13: отбор корней на отрезке"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Уравнения и неравенства с ОДЗ"),
    ("june_diagnostics", Subject.MATH_PROFILE, "Неравенства"),
    # --- Июнь · Диагностика (информатика, без кода) ---
    ("june_diagnostics", Subject.INFORMATICS, "Анализ таблиц и диаграмм"),
    ("june_diagnostics", Subject.INFORMATICS, "Логика: таблицы истинности"),
    ("june_diagnostics", Subject.INFORMATICS, "Кодирование: префиксные коды (условие Фано)"),
    ("june_diagnostics", Subject.INFORMATICS, "Комбинаторика: подсчёт слов и чисел"),
    ("june_diagnostics", Subject.INFORMATICS, "Информационный объём сообщения"),
    ("june_diagnostics", Subject.INFORMATICS, "Кодирование изображений и звука"),
    ("june_diagnostics", Subject.INFORMATICS, "Системы счисления"),
    ("june_diagnostics", Subject.INFORMATICS, "Базы данных (несколько таблиц)"),
    ("june_diagnostics", Subject.INFORMATICS, "Электронные таблицы (Excel)"),
    ("june_diagnostics", Subject.INFORMATICS, "Подсчёт путей в графе"),
    ("june_diagnostics", Subject.INFORMATICS, "Теория игр: выигрышная стратегия"),
    ("june_diagnostics", Subject.INFORMATICS, "Рекурсия (трассировка функций)"),
    # --- Июнь · Диагностика (программирование) ---
    ("june_diagnostics", Subject.INFORMATICS, "Python: Thonny, переменные и ввод-вывод"),
    ("june_diagnostics", Subject.INFORMATICS, "Python: арифметика, типы, %, //"),
    ("june_diagnostics", Subject.INFORMATICS, "Python: условия if/elif/else"),
    ("june_diagnostics", Subject.INFORMATICS, "Python: цикл for и range"),
    ("june_diagnostics", Subject.INFORMATICS, "Python: цикл while и накопитель"),
    ("june_diagnostics", Subject.INFORMATICS, "Поиск максимума/минимума в потоке"),
    ("june_diagnostics", Subject.INFORMATICS, "Задание 17: обработка чисел из файла"),
    ("june_diagnostics", Subject.INFORMATICS, "Списки и срезы"),
    ("june_diagnostics", Subject.INFORMATICS, "Работа со строками"),
    ("june_diagnostics", Subject.INFORMATICS, "Делители числа (Задание 25)"),
    # --- Июль–август · Фундамент (математика) ---
    ("july_aug_foundation", Subject.MATH_PROFILE, "Экономическая задача (№16): вклады"),
    ("july_aug_foundation", Subject.MATH_PROFILE, "Экономическая задача (№16): кредиты"),
    ("july_aug_foundation", Subject.MATH_PROFILE, "Стереометрия (№14): объёмы и углы"),
    ("july_aug_foundation", Subject.MATH_PROFILE, "Планиметрия (№17): подобие и площади"),
    ("july_aug_foundation", Subject.MATH_PROFILE, "Параметр (№18): графический метод"),
    # --- Июль–август · Фундамент (информатика) ---
    ("july_aug_foundation", Subject.INFORMATICS, "Задание 26: обработка таблицы"),
    ("july_aug_foundation", Subject.INFORMATICS, "Жадные алгоритмы"),
    ("july_aug_foundation", Subject.INFORMATICS, "Динамическое программирование (идея)"),
    ("july_aug_foundation", Subject.INFORMATICS, "Анализ алгоритмов и сложность"),
    ("july_aug_foundation", Subject.INFORMATICS, "Задание 27: эффективность (введение)"),
    # --- Июль–август · Фундамент (программирование) ---
    ("july_aug_foundation", Subject.INFORMATICS, "Чтение большого файла и сортировка"),
    ("july_aug_foundation", Subject.INFORMATICS, "Задание 26: топ-значения, два прохода"),
    ("july_aug_foundation", Subject.INFORMATICS, "Задание 27: однопроходный алгоритм"),
    ("july_aug_foundation", Subject.INFORMATICS, "Оптимизация решения по времени"),
]

MISSIONS = [
    (
        Subject.MATH_PROFILE,
        0,
        "Решить уравнение с учётом ОДЗ",
        "Реши уравнение, отдельно проверь каждый корень на соответствие ОДЗ.",
        80.0,
        "corpus:slice4:task1",
    ),
    (
        Subject.MATH_PROFILE,
        4,
        "Вероятность: совместные события",
        "Реши задачу и отдельно проверь, не посчитал ли пересечение дважды.",
        80.0,
        "corpus:probability:task-b",
    ),
    (
        Subject.INFORMATICS,
        2,
        "Оценить сложность алгоритма",
        "Определи асимптотическую сложность алгоритма и обоснуй ответ.",
        80.0,
        "seed:informatics:complexity-linear",
    ),
    (
        Subject.INFORMATICS,
        3,
        "Разбор строки по условию",
        "Напиши программу, которая обрабатывает строку по заданному условию.",
        80.0,
        "seed:informatics:string-filter",
    ),
    (
        Subject.MATH_PROFILE,
        5,
        "Неравенство: квадратное",
        "Реши неравенство и запиши ответ промежутком.",
        80.0,
        "corpus:slice4:task9",
    ),
    (
        Subject.MATH_PROFILE,
        5,
        "Неравенство: показательное",
        "Реши неравенство, отдельно проверь смену знака при основании меньше 1.",
        80.0,
        "corpus:slice4:task10",
    ),
    (
        Subject.MATH_PROFILE,
        5,
        "Неравенство: логарифмическое",
        "Реши неравенство, сначала явно выпиши ОДЗ.",
        80.0,
        "corpus:slice4:task11",
    ),
    (
        Subject.MATH_PROFILE,
        5,
        "Неравенство: рациональное",
        "Реши неравенство методом интервалов, не забудь исключённые точки.",
        80.0,
        "corpus:slice4:task12",
    ),
    (
        Subject.INFORMATICS,
        6,
        "Python: Thonny и ввод-вывод",
        "Напиши код с переменными, input(), int() и print().",
        80.0,
        "seed:informatics:thonny-variables-io",
    ),
    (
        Subject.INFORMATICS,
        7,
        "Логика: таблица истинности",
        "Разбери выражение по всем наборам переменных.",
        80.0,
        "seed:informatics:truth-table-basic",
    ),
    (
        Subject.INFORMATICS,
        8,
        "Python: арифметика и типы",
        "Используй int(), str(), остаток % и целое деление //.",
        80.0,
        "seed:informatics:arithmetic-int-str-mod-div",
    ),
    (
        Subject.INFORMATICS,
        9,
        "Python: условия",
        "Напиши ветвление if / elif / else по условию.",
        80.0,
        "seed:informatics:if-elif-else-priority",
    ),
    (
        Subject.INFORMATICS,
        10,
        "Python: for и range",
        "Реши задачу перебором чисел через for и range().",
        80.0,
        "seed:informatics:for-range-count",
    ),
    (
        Subject.INFORMATICS,
        11,
        "Кодирование: объём файла",
        "Посчитай информационный объём изображения или звука.",
        80.0,
        "seed:informatics:image-audio-size",
    ),
    (
        Subject.INFORMATICS,
        12,
        "Комбинаторика: подсчёт слов",
        "Посчитай количество вариантов без полного перебора руками.",
        80.0,
        "seed:informatics:combinatorics-words",
    ),
]

TASKS = [
    {
        "id": 4001,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 0,
        "task_number": "slice4-1",
        "statement": "Решите уравнение log₃(2x − 1) = 2.",
        "expected_answer": "5",
        "solution": "ОДЗ: 2x−1>0. По определению логарифма 2x−1 = 3² = 9, 2x = 10, x = 5.",
        "error_category": ErrorCategory.ARITHMETIC,
        "source_ref": "corpus:slice4:task1",
    },
    {
        "id": 4002,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 0,
        "task_number": "slice4-2",
        "statement": "Решите уравнение log₂(x + 3) = log₂(2x − 1).",
        "expected_answer": "4",
        "solution": "ОДЗ: x+3>0 и 2x−1>0. x+3 = 2x−1, x = 4.",
        "error_category": ErrorCategory.SIGN_TRANSFER,
        "source_ref": "corpus:slice4:task2",
    },
    {
        "id": 4003,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 0,
        "task_number": "slice4-3",
        "statement": (
            "Решите уравнение (log₃x)² − log₃x − 2 = 0. Если корней несколько, запишите наибольший."
        ),
        "expected_answer": "9",
        "solution": (
            "t = log₃x. t² − t − 2 = 0, t = 2 или t = -1. x = 9 или x = 1/3. Наибольший корень 9."
        ),
        "error_category": ErrorCategory.ODZ_LOGIC,
        "source_ref": "corpus:slice4:task3",
    },
    {
        "id": 4004,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 0,
        "task_number": "slice4-4",
        "statement": "Решите уравнение log₆(x − 5) + log₆x = 1.",
        "expected_answer": "6",
        "solution": "ОДЗ: x>5. log₆(x(x−5)) = 1, x²−5x = 6, x = 6 или -1. По ОДЗ остаётся 6.",
        "error_category": ErrorCategory.ODZ_LOGIC,
        "source_ref": "corpus:slice4:task4",
    },
    {
        "id": 4005,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 0,
        "task_number": "slice4-5",
        "statement": "Решите уравнение (x² − 9)/(x − 3) = 0.",
        "expected_answer": "-3",
        "solution": (
            "Дробь равна нулю, когда числитель равен нулю, а знаменатель нет. "
            "x=±3, но x=3 запрещён."
        ),
        "error_category": ErrorCategory.ODZ_LOGIC,
        "source_ref": "corpus:slice4:task5",
    },
    {
        "id": 4006,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 0,
        "task_number": "slice4-6",
        "statement": "Решите уравнение (2x + 1)/(x − 4) = 3.",
        "expected_answer": "13",
        "solution": "ОДЗ: x≠4. 2x+1 = 3(x−4), 2x+1 = 3x−12, x = 13.",
        "error_category": ErrorCategory.ARITHMETIC,
        "source_ref": "corpus:slice4:task6",
    },
    {
        "id": 4007,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 0,
        "task_number": "slice4-7",
        "statement": "Решите уравнение (x + 4)/(x − 2) = (x − 1)/(x − 3).",
        "expected_answer": "3,5",
        "solution": "ОДЗ: x≠2, x≠3. (x+4)(x−3)=(x−1)(x−2), x²+x−12=x²−3x+2, 4x=14, x=3,5.",
        "error_category": ErrorCategory.ARITHMETIC,
        "source_ref": "corpus:slice4:task7",
    },
    {
        "id": 4008,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 0,
        "task_number": "slice4-8",
        "statement": "Решите уравнение x + 6/x = 5. Если корней несколько, запишите наименьший.",
        "expected_answer": "2",
        "solution": "ОДЗ: x≠0. x²−5x+6=0, x=2 или x=3. Наименьший корень 2.",
        "error_category": ErrorCategory.CONDITION_READING,
        "source_ref": "corpus:slice4:task8",
    },
    {
        "id": 4009,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 5,
        "task_number": "slice4-9",
        "statement": "Решите неравенство x² − x − 6 ≤ 0.",
        "expected_answer": "[-2; 3]",
        "solution": "(x−3)(x+2)=0. Парабола ветвями вверх, берём промежуток между корнями.",
        "error_category": ErrorCategory.OTHER,
        "source_ref": "corpus:slice4:task9",
    },
    {
        "id": 4010,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 5,
        "task_number": "slice4-10",
        "statement": "Решите неравенство (1/2)^x < 1/8.",
        "expected_answer": "x > 3",
        "solution": "1/8 = (1/2)³. Основание меньше 1, поэтому знак неравенства меняется: x > 3.",
        "error_category": ErrorCategory.SIGN_TRANSFER,
        "source_ref": "corpus:slice4:task10",
    },
    {
        "id": 4011,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 5,
        "task_number": "slice4-11",
        "statement": "Решите неравенство log₂(x − 1) < 3.",
        "expected_answer": "(1; 9)",
        "solution": "ОДЗ: x>1. x−1 < 8, x < 9. Ответ: 1 < x < 9.",
        "error_category": ErrorCategory.ODZ_LOGIC,
        "source_ref": "corpus:slice4:task11",
    },
    {
        "id": 4012,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 5,
        "task_number": "slice4-12",
        "statement": "Решите неравенство (x − 1)/(x + 2) ≥ 0.",
        "expected_answer": "(-∞; -2) ∪ [1; +∞)",
        "solution": "Метод интервалов. x=1 включаем, x=-2 исключаем.",
        "error_category": ErrorCategory.CONDITION_READING,
        "source_ref": "corpus:slice4:task12",
    },
    {
        "id": 4013,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 4,
        "task_number": "probability-a",
        "statement": (
            "В коробке 30 шаров: 12 красных, 8 синих и 10 зелёных. "
            "Найдите вероятность достать красный или синий шар."
        ),
        "expected_answer": "2/3",
        "solution": "События взаимоисключающие: 12/30 + 8/30 = 20/30 = 2/3.",
        "error_category": ErrorCategory.PROBABILITY_DOUBLE_COUNT,
        "source_ref": "corpus:probability:task-a",
    },
    {
        "id": 4014,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 4,
        "task_number": "probability-b",
        "statement": (
            "Вероятность сдать математику — 0,9, информатику — 0,8, "
            "оба экзамена — 0,75. Найдите вероятность не сдать ни один."
        ),
        "expected_answer": "0,05",
        "solution": "P(хотя бы один) = 0,9 + 0,8 − 0,75 = 0,95. P(ни одного) = 1 − 0,95 = 0,05.",
        "error_category": ErrorCategory.PROBABILITY_DOUBLE_COUNT,
        "source_ref": "corpus:probability:task-b",
    },
    {
        "id": 4015,
        "subject": Subject.MATH_PROFILE,
        "topic_index": 4,
        "task_number": "probability-c",
        "statement": (
            "Вероятность дождя — 0,4, ветра — 0,3, дождя и ветра — 0,15. "
            "Найдите вероятность того, что дождь будет, а ветра не будет."
        ),
        "expected_answer": "0,25",
        "solution": "Только дождь = P(дождь) − P(дождь и ветер) = 0,4 − 0,15 = 0,25.",
        "error_category": ErrorCategory.PROBABILITY_DOUBLE_COUNT,
        "source_ref": "corpus:probability:task-c",
    },
    {
        "id": 4016,
        "subject": Subject.INFORMATICS,
        "topic_index": 2,
        "task_number": "complexity-linear",
        "statement": (
            "Дан алгоритм:\n"
            "s = 0\n"
            "for i in range(n):\n"
            "    for j in range(3):\n"
            "        s += a[i] * j\n"
            "Определите асимптотическую сложность по n и кратко обоснуйте ответ."
        ),
        "expected_answer": "O(n)",
        "solution": (
            "Внешний цикл выполняется n раз, внутренний всегда 3 раза. "
            "Итого 3n элементарных шагов, константа отбрасывается: O(n)."
        ),
        "error_category": ErrorCategory.CONDITION_READING,
        "source": "seed",
        "source_ref": "seed:informatics:complexity-linear",
    },
    {
        "id": 4017,
        "subject": Subject.INFORMATICS,
        "topic_index": 3,
        "task_number": "string-filter",
        "statement": (
            "Дана строка из строчных латинских букв. Напишите программу на Python, "
            "которая выводит количество символов, стоящих сразу после буквы 'a'. "
            "Например, для строки 'abacada' ответ равен 3."
        ),
        "expected_answer": (
            "Нужно пройти строку со второго символа и посчитать позиции i, "
            "для которых s[i-1] == 'a'. Для 'abacada' ответ 3."
        ),
        "solution": (
            "s = input().strip()\n"
            "count = 0\n"
            "for i in range(1, len(s)):\n"
            "    if s[i - 1] == 'a':\n"
            "        count += 1\n"
            "print(count)"
        ),
        "error_category": ErrorCategory.CONDITION_READING,
        "source": "seed",
        "source_ref": "seed:informatics:string-filter",
    },
    {
        "id": 4018,
        "subject": Subject.INFORMATICS,
        "topic_index": 6,
        "task_number": "python-basics-1",
        "statement": (
            "В Thonny напишите программу: она спрашивает имя и год рождения, "
            "а затем выводит строку `Привет, <имя>! В 2026 тебе будет <возраст>.`"
        ),
        "expected_answer": (
            "Нужны input() для имени и года, int() для года, переменная age = 2026 - year "
            "и print() с собранной строкой."
        ),
        "solution": (
            "name = input()\n"
            "year = int(input())\n"
            "age = 2026 - year\n"
            "print('Привет, ' + name + '! В 2026 тебе будет ' + str(age) + '.')"
        ),
        "error_category": ErrorCategory.CODE_ALGORITHM,
        "source": "seed",
        "source_ref": "seed:informatics:thonny-variables-io",
    },
    {
        "id": 4019,
        "subject": Subject.INFORMATICS,
        "topic_index": 7,
        "task_number": "truth-table-1",
        "statement": (
            "Для логического выражения `(A and not B) or C` найдите количество наборов "
            "значений A, B, C, при которых выражение истинно."
        ),
        "expected_answer": "5",
        "solution": (
            "Если C=1, выражение истинно при любых A и B: 4 набора. "
            "Если C=0, нужно A and not B, это один набор A=1, B=0. Итого 5."
        ),
        "error_category": ErrorCategory.ALGORITHM_LOGIC,
        "source": "seed",
        "source_ref": "seed:informatics:truth-table-basic",
    },
    {
        "id": 4020,
        "subject": Subject.INFORMATICS,
        "topic_index": 8,
        "task_number": "python-arithmetic-1",
        "statement": (
            "Дано число n = 2026. С помощью операций % и // найдите последние две цифры "
            "числа и число без последних двух цифр."
        ),
        "expected_answer": "26 и 20",
        "solution": "n % 100 = 26, n // 100 = 20. В коде n нужно хранить как int.",
        "error_category": ErrorCategory.ARITHMETIC,
        "source": "seed",
        "source_ref": "seed:informatics:arithmetic-int-str-mod-div",
    },
    {
        "id": 4021,
        "subject": Subject.INFORMATICS,
        "topic_index": 9,
        "task_number": "python-conditions-1",
        "statement": (
            "Напишите программу: вводится целое число n. Если оно делится на 2, вывести "
            "`even`; иначе если делится на 3, вывести `divisible_by_3`; иначе вывести `other`."
        ),
        "expected_answer": (
            "Нужно if n % 2 == 0, затем elif n % 3 == 0, затем else. "
            "Проверка делимости на 2 имеет приоритет."
        ),
        "solution": (
            "n = int(input())\n"
            "if n % 2 == 0:\n"
            "    print('even')\n"
            "elif n % 3 == 0:\n"
            "    print('divisible_by_3')\n"
            "else:\n"
            "    print('other')"
        ),
        "error_category": ErrorCategory.CODE_ALGORITHM,
        "source": "seed",
        "source_ref": "seed:informatics:if-elif-else-priority",
    },
    {
        "id": 4022,
        "subject": Subject.INFORMATICS,
        "topic_index": 10,
        "task_number": "python-for-1",
        "statement": (
            "С помощью for и range посчитайте, сколько чисел от 1 до 100 включительно "
            "делятся на 7, но не делятся на 14."
        ),
        "expected_answer": "7",
        "solution": (
            "Подходят 7, 21, 35, 49, 63, 77, 91. В коде проверяем n % 7 == 0 and n % 14 != 0."
        ),
        "error_category": ErrorCategory.CODE_ALGORITHM,
        "source": "seed",
        "source_ref": "seed:informatics:for-range-count",
    },
    {
        "id": 4023,
        "subject": Subject.INFORMATICS,
        "topic_index": 11,
        "task_number": "encoding-1",
        "statement": (
            "Изображение размером 1024 на 768 пикселей кодируется палитрой из 256 цветов. "
            "Найдите информационный объём изображения в Кбайтах без учёта сжатия."
        ),
        "expected_answer": "768 Кбайт",
        "solution": (
            "256 цветов = 8 бит = 1 байт на пиксель. 1024 * 768 байт = 786432 байт = 768 Кбайт."
        ),
        "error_category": ErrorCategory.ARITHMETIC,
        "source": "seed",
        "source_ref": "seed:informatics:image-audio-size",
    },
    {
        "id": 4024,
        "subject": Subject.INFORMATICS,
        "topic_index": 12,
        "task_number": "combinatorics-1",
        "statement": (
            "Сколько существует пятибуквенных слов из букв A, B, C, если никакие две "
            "одинаковые буквы не стоят рядом?"
        ),
        "expected_answer": "48",
        "solution": (
            "Первая буква: 3 варианта. Каждая следующая: 2 варианта, кроме предыдущей. "
            "Итого 3 * 2^4 = 48."
        ),
        "error_category": ErrorCategory.CONDITION_READING,
        "source": "seed",
        "source_ref": "seed:informatics:combinatorics-words",
    },
]


def stable_uuid(number: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{number:012d}")


def seed() -> None:
    session = SessionLocal()
    try:
        if session.get(UserORM, DEMO_USER_ID) is None:
            session.add(
                UserORM(
                    id=DEMO_USER_ID,
                    display_name="Family operator",
                    role=Role.GUARDIAN,
                    created_at=datetime.now(UTC),
                )
            )

        if session.get(StudentProfileORM, DEMO_STUDENT_ID) is None:
            session.add(
                StudentProfileORM(
                    id=DEMO_STUDENT_ID,
                    user_id=DEMO_USER_ID,
                    exam_year=2027,
                    display_name="Demo student",
                )
            )

        existing_tracks = {
            track.subject
            for track in session.query(SubjectTrackORM).filter_by(student_id=DEMO_STUDENT_ID)
        }
        for index, (subject, current_score) in enumerate(
            [(Subject.MATH_PROFILE, 65), (Subject.INFORMATICS, 50)], start=1
        ):
            if subject not in existing_tracks:
                session.add(
                    SubjectTrackORM(
                        id=stable_uuid(index),
                        student_id=DEMO_STUDENT_ID,
                        subject=subject,
                        current_score=current_score,
                        target_score=85,
                        phase="foundation",
                    )
                )
            if (
                session.query(ScoreEventORM)
                .filter_by(source_ref=f"seed:score:{subject.value}")
                .first()
                is None
            ):
                session.add(
                    ScoreEventORM(
                        id=stable_uuid(3000 + index),
                        student_id=DEMO_STUDENT_ID,
                        subject=subject,
                        score=current_score,
                        kind="baseline",
                        occurred_on=date.today(),
                        note="Initial observed baseline from AGENTS.md.",
                        source_ref=f"seed:score:{subject.value}",
                    )
                )

        if (
            session.query(CleanSheetEventORM)
            .filter_by(source_ref="seed:clean-sheet:baseline")
            .first()
            is None
        ):
            session.add(
                CleanSheetEventORM(
                    id=stable_uuid(3100),
                    student_id=DEMO_STUDENT_ID,
                    occurred_on=date.today(),
                    tasks_total=5,
                    clean_sheet_count=2,
                    note="Initial programming clean-sheet ratio: 0.4.",
                    source_ref="seed:clean-sheet:baseline",
                )
            )

        topic_ids: dict[tuple[Subject, str], UUID] = {}
        existing_topics = {
            (topic.subject, topic.title): topic.id for topic in session.query(TopicORM)
        }
        for index, (subject, title, task_number) in enumerate(TOPICS, start=1):
            if (subject, title) in existing_topics:
                topic_ids[(subject, title)] = existing_topics[(subject, title)]
                continue
            topic_id = stable_uuid(1000 + index)
            session.add(
                TopicORM(
                    id=topic_id,
                    subject=subject,
                    title=title,
                    spec_year=2026,
                    task_number=task_number,
                )
            )
            topic_ids[(subject, title)] = topic_id

        # Program phases: reuse a topic if its title already exists (assign phase),
        # otherwise create a program-only topic so the controller sees full coverage.
        topic_objs = {(topic.subject, topic.title): topic for topic in session.query(TopicORM)}
        for order, (phase_key, subject, title) in enumerate(PROGRAM, start=1):
            key = (subject, title)
            topic = topic_objs.get(key)
            if topic is None:
                topic = TopicORM(
                    id=stable_uuid(5000 + order),
                    subject=subject,
                    title=title,
                    spec_year=2026,
                    task_number=None,
                    phase=phase_key,
                    program_order=order,
                )
                session.add(topic)
                topic_objs[key] = topic
                topic_ids[key] = topic.id
            else:
                topic.phase = phase_key
                topic.program_order = order

        # Срез-история (диагностика, §11): study-log результаты + ошибки журнала.
        # Источник: Desktop\ЕГЭ\срезы знаний\история первых срезов.md. Идемпотентно по source_ref.
        srez_date = date(2026, 6, 7)
        srez_log = [
            ("srez:1:studylog", "Срез №1 — 4 темы", 12, 10),
            ("srez:2:studylog", "Срез №2 — без вероятности", 9, 8),
        ]
        for index, (source_ref, title, total, correct) in enumerate(srez_log, start=1):
            if session.query(StudyLogEntryORM).filter_by(source_ref=source_ref).first() is None:
                session.add(
                    StudyLogEntryORM(
                        id=stable_uuid(6000 + index),
                        student_id=DEMO_STUDENT_ID,
                        subject=Subject.MATH_PROFILE,
                        occurred_on=srez_date,
                        topic_title=title,
                        tasks_total=total,
                        tasks_correct=correct,
                        percent_correct=correct / total,
                        status_note="зачёт" if correct / total >= 0.8 else None,
                        note="Импортировано из истории срезов.",
                        source_ref=source_ref,
                    )
                )
        probability_topic = topic_objs.get((Subject.MATH_PROFILE, "Вероятность: теорема сложения"))
        srez_errors = [
            (
                "srez:1:err:probability",
                probability_topic.id if probability_topic is not None else None,
                ErrorCategory.PROBABILITY_DOUBLE_COUNT,
                "Двойной счёт в теореме сложения: взяла P(A) вместо P(только A).",
            ),
            (
                "srez:2:err:logdiff",
                None,
                ErrorCategory.OTHER,
                "Разность логарифмов log2(24)-log2(3): знала направление, не довела (нет уверенности).",
            ),
        ]
        for index, (source_ref, topic_id, category, detail) in enumerate(srez_errors, start=1):
            if session.query(ErrorEventORM).filter_by(source_ref=source_ref).first() is None:
                session.add(
                    ErrorEventORM(
                        id=stable_uuid(6100 + index),
                        student_id=DEMO_STUDENT_ID,
                        subject=Subject.MATH_PROFILE,
                        topic_id=topic_id,
                        category=category,
                        detail=detail,
                        created_at=datetime.combine(srez_date, datetime.min.time(), tzinfo=UTC),
                        source_ref=source_ref,
                    )
                )

        task_by_ref: dict[str, TaskORM] = {}
        for task_spec in TASKS:
            source_ref = task_spec["source_ref"]
            topic = TOPICS[task_spec["topic_index"]]
            existing_task = session.query(TaskORM).filter_by(source_ref=source_ref).first()
            if existing_task is not None:
                existing_task.subject = task_spec["subject"]
                existing_task.topic_id = topic_ids[topic[0], topic[1]]
                existing_task.task_number = task_spec["task_number"]
                existing_task.statement = task_spec["statement"]
                existing_task.expected_answer = task_spec["expected_answer"]
                existing_task.solution = task_spec["solution"]
                existing_task.error_category = task_spec["error_category"]
                existing_task.status = TaskStatus.APPROVED
                existing_task.source = task_spec.get("source", "corpus_llm")
                task_by_ref[source_ref] = existing_task
                continue
            task = TaskORM(
                id=stable_uuid(task_spec["id"]),
                subject=task_spec["subject"],
                topic_id=topic_ids[topic[0], topic[1]],
                task_number=task_spec["task_number"],
                statement=task_spec["statement"],
                expected_answer=task_spec["expected_answer"],
                solution=task_spec["solution"],
                error_category=task_spec["error_category"],
                status=TaskStatus.APPROVED,
                source=task_spec.get("source", "corpus_llm"),
                source_ref=source_ref,
                created_at=datetime.now(UTC),
            )
            session.add(task)
            task_by_ref[source_ref] = task

        probability_task = task_by_ref.get("corpus:probability:task-b")
        probability_topic_id = topic_ids[
            TOPICS[4][0],
            TOPICS[4][1],
        ]
        legacy_probability_mission = (
            session.query(MissionORM)
            .filter_by(student_id=DEMO_STUDENT_ID, title="Задача на проценты")
            .first()
        )
        canonical_probability_mission = legacy_probability_mission
        if canonical_probability_mission is not None:
            canonical_probability_mission.title = "Вероятность: совместные события"
            canonical_probability_mission.instructions = (
                "Реши задачу и отдельно проверь, не посчитал ли пересечение дважды."
            )
            canonical_probability_mission.subject = Subject.MATH_PROFILE
            canonical_probability_mission.topic_id = probability_topic_id
            canonical_probability_mission.task_id = (
                probability_task.id if probability_task is not None else None
            )
            canonical_probability_mission.threshold_percent = 80.0
        else:
            canonical_probability_mission = (
                session.query(MissionORM)
                .filter_by(
                    student_id=DEMO_STUDENT_ID,
                    title="Вероятность: совместные события",
                )
                .first()
            )

        existing_mission_titles = {
            mission.title
            for mission in session.query(MissionORM).filter_by(student_id=DEMO_STUDENT_ID)
        }
        for index, (subject, topic_index, title, instructions, threshold, task_ref) in enumerate(
            MISSIONS, start=1
        ):
            topic_id = topic_ids[TOPICS[topic_index][0], TOPICS[topic_index][1]]
            task = task_by_ref.get(task_ref) if task_ref is not None else None
            if title in existing_mission_titles:
                for mission in (
                    session.query(MissionORM)
                    .filter_by(student_id=DEMO_STUDENT_ID, title=title)
                    .all()
                ):
                    mission.subject = subject
                    mission.topic_id = topic_id
                    mission.task_id = task.id if task is not None else None
                    mission.instructions = instructions
                    mission.threshold_percent = threshold
                continue
            session.add(
                MissionORM(
                    id=stable_uuid(2000 + index),
                    student_id=DEMO_STUDENT_ID,
                    subject=subject,
                    topic_id=topic_id,
                    task_id=task.id if task is not None else None,
                    title=title,
                    instructions=instructions,
                    status=MissionStatus.ACTIVE,
                    ai_policy=AiPolicy.ATTEMPT_FIRST,
                    threshold_percent=threshold,
                    due_date=date.today(),
                )
            )

        starter_task_refs = {
            "Решить уравнение с учётом ОДЗ": "corpus:slice4:task1",
            "Вероятность: совместные события": "corpus:probability:task-b",
            "Оценить сложность алгоритма": "seed:informatics:complexity-linear",
            "Разбор строки по условию": "seed:informatics:string-filter",
        }
        for mission in session.query(MissionORM).filter_by(student_id=DEMO_STUDENT_ID):
            if mission.task_id is not None or mission.title not in starter_task_refs:
                continue
            task = task_by_ref.get(starter_task_refs[mission.title])
            if task is not None and task.status == TaskStatus.APPROVED:
                mission.task_id = task.id
                mission.topic_id = task.topic_id

        if canonical_probability_mission is not None:
            probability_duplicates = (
                session.query(MissionORM)
                .filter_by(
                    student_id=DEMO_STUDENT_ID,
                    title="Вероятность: совместные события",
                )
                .all()
            )
            for mission in probability_duplicates:
                if mission.id != canonical_probability_mission.id:
                    mission.status = MissionStatus.SKIPPED

        session.commit()
        print("Seed complete.")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
