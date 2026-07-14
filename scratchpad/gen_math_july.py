"""Генерация + верификация июльских задач (TASK_BANK_JULY_REFILL.md).

Анти-poison: каждый expected_answer вычислен кодом (арифметика/sympy/симуляция
платежей циклом), не взят "из головы". Скрипт печатает финальный JSON и таблицу
самопроверок; ничего не пишет в БД сам — внесение делается отдельно через MCP
add_task (DRAFT).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.domain.figures import parse_interval_answer  # noqa: E402
from app.domain.policies import answer_is_correct  # noqa: E402

import sympy as sp

x = sp.symbols("x", real=True)

TASKS: list[dict] = []
CHECKS: list[tuple[str, bool]] = []


def fmt_num(value) -> str:
    """Целое -> '7776'; рациональное конечное десятичное -> '0,04' (запятая)."""
    r = sp.nsimplify(value)
    r = sp.Rational(r)
    if r.q == 1:
        return str(int(r))
    dec = sp.Float(r, 20)
    s = f"{dec:.10f}".rstrip("0").rstrip(".")
    if "." not in s:
        return s
    whole, frac = s.split(".")
    return f"{whole},{frac}"


def add_task(*, statement, expected_answer, solution, topic_title, source,
             source_ref, error_category=None):
    TASKS.append(
        {
            "subject": "math_profile",
            "topic_title": topic_title,
            "statement": statement,
            "expected_answer": expected_answer,
            "solution": solution,
            "source": source,
            "source_ref": source_ref,
            "error_category": error_category,
        }
    )
    ok = answer_is_correct(expected_answer, expected_answer)
    CHECKS.append((source_ref, ok))
    assert ok, f"self-check failed for {source_ref}"


def add_interval_task(*, statement, expected_answer, solution, topic_title, source,
                       source_ref, error_category=None):
    parsed = parse_interval_answer(expected_answer)
    assert parsed is not None, f"parse_interval_answer failed for {source_ref}: {expected_answer!r}"
    add_task(
        statement=statement, expected_answer=expected_answer, solution=solution,
        topic_title=topic_title, source=source, source_ref=source_ref,
        error_category=error_category,
    )


# ---------------------------------------------------------------------------
# Часть A.1 — Экономическая задача (№16): вклады
# Каждый ответ — результат цикла начисления процентов (не формула из головы).
# ---------------------------------------------------------------------------

def simulate_deposit(principal: float, rate_percent: float, years: int, topup_after_year: int | None = None, topup_amount: float = 0.0) -> float:
    balance = principal
    for year in range(1, years + 1):
        balance *= 1 + rate_percent / 100
        if topup_after_year == year:
            balance += topup_amount
    return balance


# 1) простой сложный процент, 3 года
bal1 = simulate_deposit(100_000, 10, 3)
assert abs(bal1 - round(bal1)) < 1e-6
add_task(
    statement=(
        "Вкладчик положил в банк 100 000 рублей под 10% годовых (проценты "
        "начисляются в конце года и присоединяются к вкладу). Сколько рублей "
        "будет на счёте через 3 года?"
    ),
    expected_answer=str(round(bal1)),
    solution=(
        "Симуляция по годам: balance *= 1.10 три раза подряд: "
        "100000 -> 110000 -> 121000 -> 133100."
    ),
    topic_title="Экономическая задача (№16): вклады",
    source="agent-july-refill",
    source_ref="july-refill:vklady:1",
)

# 2) сложный процент + пополнение после 1-го года
bal2 = simulate_deposit(50_000, 8, 2, topup_after_year=1, topup_amount=10_000)
assert abs(bal2 - round(bal2)) < 1e-6
add_task(
    statement=(
        "Вкладчик положил 50 000 рублей на 2 года под 8% годовых с ежегодным "
        "присоединением процентов к вкладу. В конце первого года (сразу после "
        "начисления процентов) вкладчик пополнил счёт на 10 000 рублей. "
        "Сколько рублей будет на счёте в конце второго года?"
    ),
    expected_answer=str(round(bal2)),
    solution=(
        "Год 1: 50000*1.08=54000, +10000=64000. "
        "Год 2: 64000*1.08=69120."
    ),
    topic_title="Экономическая задача (№16): вклады",
    source="agent-july-refill",
    source_ref="july-refill:vklady:2",
)

# 3) найти ставку перебором целых процентов (цикл-поиск, не формула)
target_principal, target_years, target_final = 200_000, 2, 242_000
found_rate = None
for candidate_rate in range(1, 51):
    balance = simulate_deposit(target_principal, candidate_rate, target_years)
    if abs(balance - target_final) < 1e-6:
        found_rate = candidate_rate
        break
assert found_rate is not None
add_task(
    statement=(
        "Вкладчик положил 200 000 рублей на 2 года. Проценты начисляются в "
        "конце каждого года по одной и той же целой процентной ставке и "
        "присоединяются к вкладу. Известно, что через 2 года на счёте стало "
        "242 000 рублей. Найдите ставку в процентах годовых."
    ),
    expected_answer=str(found_rate),
    solution=(
        "Перебор целых ставок r от 1 до 50: находим r, при котором "
        "200000*(1+r/100)^2 = 242000. Подходит r=10: 200000*1.1^2=242000."
    ),
    topic_title="Экономическая задача (№16): вклады",
    source="agent-july-refill",
    source_ref="july-refill:vklady:3",
)

# 4) найти число лет циклом до превышения порога
balance = 120_000.0
years = 0
while balance <= 200_000:
    balance *= 1.20
    years += 1
add_task(
    statement=(
        "Вкладчик положил 120 000 рублей под 20% годовых (проценты "
        "присоединяются к вкладу ежегодно). Через сколько лет сумма на счёте "
        "впервые превысит 200 000 рублей?"
    ),
    expected_answer=str(years),
    solution=(
        "Цикл: 120000 -> 144000 (1 год) -> 172800 (2 года) -> 207360 (3 года, "
        "уже больше 200000). Ответ: 3."
    ),
    topic_title="Экономическая задача (№16): вклады",
    source="agent-july-refill",
    source_ref="july-refill:vklady:4",
)


# ---------------------------------------------------------------------------
# Часть A.2 — Экономическая задача (№16): кредиты
# ---------------------------------------------------------------------------

def simulate_differentiated_loan(principal: float, rate_percent: float, years: int):
    """Равными долями основного долга + проценты на остаток на начало года."""
    remaining = principal
    principal_payment = principal / years
    payments = []
    for _year in range(years):
        interest = remaining * rate_percent / 100
        payment = principal_payment + interest
        payments.append(payment)
        remaining -= principal_payment
    return payments


# 1) дифф. платежи — общая сумма выплат
payments1 = simulate_differentiated_loan(300_000, 20, 3)
total1 = sum(payments1)
assert abs(total1 - round(total1)) < 1e-6
add_task(
    statement=(
        "Ученица взяла кредит 300 000 рублей на 3 года под 20% годовых. Долг "
        "выплачивается дифференцированными платежами: каждый год выплачивается "
        "равная доля основного долга (1/3 от 300 000) плюс проценты на "
        "оставшуюся часть долга на начало года. Найдите общую сумму выплат за "
        "всё время (в рублях)."
    ),
    expected_answer=str(round(total1)),
    solution=(
        "Год 1: долг 300000, проценты 60000, платёж 160000, остаток 200000. "
        "Год 2: проценты 40000, платёж 140000, остаток 100000. "
        "Год 3: проценты 20000, платёж 120000, остаток 0. "
        "Сумма: 160000+140000+120000=420000."
    ),
    topic_title="Экономическая задача (№16): кредиты",
    source="agent-july-refill",
    source_ref="july-refill:kredity:1",
)

# 2) дифф. платежи — переплата
payments2 = simulate_differentiated_loan(400_000, 15, 4)
total2 = sum(payments2)
overpay2 = total2 - 400_000
assert abs(overpay2 - round(overpay2)) < 1e-6
add_task(
    statement=(
        "Кредит 400 000 рублей взят на 4 года под 15% годовых, выплаты "
        "дифференцированные (равными долями основного долга плюс проценты на "
        "остаток долга на начало года). Найдите переплату по кредиту (в "
        "рублях)."
    ),
    expected_answer=str(round(overpay2)),
    solution=(
        "Платежи по годам: 160000, 145000, 130000, 115000 (сумма 550000). "
        "Переплата: 550000-400000=150000."
    ),
    topic_title="Экономическая задача (№16): кредиты",
    source="agent-july-refill",
    source_ref="july-refill:kredity:2",
)

# 3) дифф. платежи — платёж в конкретный год
payments3 = simulate_differentiated_loan(240_000, 25, 4)
last_payment = payments3[-1]
assert abs(last_payment - round(last_payment)) < 1e-6
add_task(
    statement=(
        "Кредит 240 000 рублей взят на 4 года под 25% годовых, выплаты "
        "дифференцированные (равными долями основного долга плюс проценты на "
        "остаток долга на начало года). Найдите сумму последнего (четвёртого) "
        "платежа (в рублях)."
    ),
    expected_answer=str(round(last_payment)),
    solution=(
        "Основной долг каждый год: 60000. Остаток перед 4-м годом: 60000. "
        "Проценты 4-го года: 60000*0.25=15000. Платёж: 60000+15000=75000."
    ),
    topic_title="Экономическая задача (№16): кредиты",
    source="agent-july-refill",
    source_ref="july-refill:kredity:3",
)


# 4) аннуитет — равный платёж, найден перебором/симуляцией, проверен обнулением долга
def annuity_forward_balance(principal: float, rate_percent: float, years: int, payment: float) -> float:
    balance = principal
    for _ in range(years):
        balance *= 1 + rate_percent / 100
        balance -= payment
    return balance


def find_annuity_payment(principal: float, rate_percent: float, years: int) -> int:
    """Целочисленный ежегодный платёж, при котором остаток долга после
    `years` платежей равен нулю (двоичный поиск + симуляция вперёд)."""
    lo, hi = 0, int(principal * (1 + rate_percent / 100) ** years)
    for _ in range(200):
        mid = (lo + hi) / 2
        remaining = annuity_forward_balance(principal, rate_percent, years, mid)
        if remaining > 0:
            lo = mid
        else:
            hi = mid
    payment = round(hi)
    remaining_check = annuity_forward_balance(principal, rate_percent, years, payment)
    assert abs(remaining_check) < 1.0, remaining_check
    return payment


annuity_payment = find_annuity_payment(200_000, 10, 2)
add_task(
    statement=(
        "Кредит 200 000 рублей взят на 2 года под 10% годовых. Долг "
        "выплачивается равными ежегодными платежами (аннуитет): каждый год "
        "долг сначала увеличивается на 10%, затем уменьшается на сумму "
        "платежа, и после второго платежа долг должен стать равным нулю. "
        "Найдите размер ежегодного платежа (в рублях, округлите до целого)."
    ),
    expected_answer=str(annuity_payment),
    solution=(
        "Численный поиск (двоичный поиск + симуляция вперёд): подбираем "
        "платёж A, при котором ((200000*1.1 - A)*1.1 - A) = 0."
    ),
    topic_title="Экономическая задача (№16): кредиты",
    source="agent-july-refill",
    source_ref="july-refill:kredity:4",
)


# ---------------------------------------------------------------------------
# Часть A.3 — Стереометрия (Часть 1), формулы/координаты, без картинки
# ---------------------------------------------------------------------------

# 1) объём куба через известный объём -> площадь поверхности
cube_volume = sp.Integer(27)
edge = sp.nsimplify(cube_volume ** sp.Rational(1, 3))
assert edge == 3
surface = 6 * edge ** 2
add_task(
    statement="Объём куба равен 27. Найдите площадь его полной поверхности.",
    expected_answer=fmt_num(surface),
    solution="Ребро a: a^3=27 -> a=3. Площадь поверхности: 6a^2=6*9=54.",
    topic_title="Стереометрия (Часть 1)",
    source="agent-july-refill",
    source_ref="july-refill:stereo:1",
)

# 2) диагональ куба -> объём
diag = 6 * sp.sqrt(3)
edge2 = sp.simplify(diag / sp.sqrt(3))
assert edge2 == 6
volume2 = edge2 ** 3
add_task(
    statement="Диагональ куба равна 6√3. Найдите объём этого куба.",
    expected_answer=fmt_num(volume2),
    solution="Диагональ куба d=a√3=6√3 -> a=6. Объём: a^3=216.",
    topic_title="Стереометрия (Часть 1)",
    source="agent-july-refill",
    source_ref="july-refill:stereo:2",
)

# 3) объём шара / пи
radius = sp.Integer(3)
ball_volume_over_pi = sp.simplify(sp.Rational(4, 3) * radius ** 3)
add_task(
    statement="Радиус шара равен 3. Найдите объём шара, делённый на π.",
    expected_answer=fmt_num(ball_volume_over_pi),
    solution="V=(4/3)*pi*r^3, r=3 -> V/pi=(4/3)*27=36.",
    topic_title="Стереометрия (Часть 1)",
    source="agent-july-refill",
    source_ref="july-refill:stereo:3",
)

# 4) диагональ прямоугольного параллелепипеда (подобран целый ответ)
a, b, c = sp.Integer(3), sp.Integer(4), sp.Integer(12)
diagonal = sp.sqrt(a ** 2 + b ** 2 + c ** 2)
diagonal_simplified = sp.nsimplify(diagonal)
assert diagonal_simplified.is_Integer, diagonal_simplified
add_task(
    statement=(
        "Измерения прямоугольного параллелепипеда равны 3, 4 и 12. Найдите "
        "длину его диагонали."
    ),
    expected_answer=fmt_num(diagonal_simplified),
    solution="d=sqrt(a^2+b^2+c^2)=sqrt(9+16+144)=sqrt(169)=13.",
    topic_title="Стереометрия (Часть 1)",
    source="agent-july-refill",
    source_ref="july-refill:stereo:4",
)


# ---------------------------------------------------------------------------
# Часть A.4 — Планиметрия (Часть 1)
# ---------------------------------------------------------------------------

# 1) формула Герона, стороны 13-14-15
sa, sb, sc = sp.Integer(13), sp.Integer(14), sp.Integer(15)
sp_ = (sa + sb + sc) / 2
heron_area = sp.sqrt(sp_ * (sp_ - sa) * (sp_ - sb) * (sp_ - sc))
heron_area_simplified = sp.nsimplify(heron_area)
assert heron_area_simplified.is_Integer, heron_area_simplified
add_task(
    statement="Стороны треугольника равны 13, 14 и 15. Найдите его площадь.",
    expected_answer=fmt_num(heron_area_simplified),
    solution="Формула Герона: p=21, S=sqrt(21*8*7*6)=sqrt(7056)=84.",
    topic_title="Планиметрия (Часть 1)",
    source="agent-july-refill",
    source_ref="july-refill:planim:1",
)

# 2) гипотенуза прямоугольного треугольника
leg1, leg2 = sp.Integer(9), sp.Integer(12)
hyp = sp.sqrt(leg1 ** 2 + leg2 ** 2)
hyp_simplified = sp.nsimplify(hyp)
assert hyp_simplified.is_Integer, hyp_simplified
add_task(
    statement="В прямоугольном треугольнике катеты равны 9 и 12. Найдите гипотенузу.",
    expected_answer=fmt_num(hyp_simplified),
    solution="По теореме Пифагора: c=sqrt(9^2+12^2)=sqrt(81+144)=sqrt(225)=15.",
    topic_title="Планиметрия (Часть 1)",
    source="agent-july-refill",
    source_ref="july-refill:planim:2",
)

# 3) радиус описанной окружности равностороннего треугольника
side = 6 * sp.sqrt(3)
circumradius = sp.simplify(side / sp.sqrt(3))
add_task(
    statement=(
        "Сторона правильного треугольника равна 6√3. Найдите радиус "
        "окружности, описанной около этого треугольника."
    ),
    expected_answer=fmt_num(circumradius),
    solution="Для правильного треугольника R=a/√3=6√3/√3=6.",
    topic_title="Планиметрия (Часть 1)",
    source="agent-july-refill",
    source_ref="july-refill:planim:3",
)

# 4) площадь трапеции
base1, base2, height = sp.Integer(8), sp.Integer(14), sp.Integer(5)
trapezoid_area = (base1 + base2) / 2 * height
add_task(
    statement=(
        "Основания трапеции равны 8 и 14, высота равна 5. Найдите площадь "
        "трапеции."
    ),
    expected_answer=fmt_num(trapezoid_area),
    solution="S=((a+b)/2)*h=((8+14)/2)*5=11*5=55.",
    topic_title="Планиметрия (Часть 1)",
    source="agent-july-refill",
    source_ref="july-refill:planim:4",
)


# ---------------------------------------------------------------------------
# Часть A.5 — Неравенства (интервалы через sympy)
# ---------------------------------------------------------------------------

def interval_to_ege_string(sol) -> str:
    """sympy Union/Interval -> строка формата '(-∞; -2) ∪ [1; +∞)'."""
    def one(iv: sp.Interval) -> str:
        lo = "-∞" if iv.left == -sp.oo else fmt_num(iv.left)
        hi = "+∞" if iv.right == sp.oo else fmt_num(iv.right)
        lb = "(" if iv.left_open or iv.left == -sp.oo else "["
        rb = ")" if iv.right_open or iv.right == sp.oo else "]"
        return f"{lb}{lo}; {hi}{rb}"

    if isinstance(sol, sp.Union):
        parts = [one(a) for a in sol.args]
    else:
        parts = [one(sol)]
    return " ∪ ".join(parts)


# 1) квадратное неравенство
sol1 = sp.solve_univariate_inequality(x ** 2 - 5 * x + 6 < 0, x, relational=False)
answer1 = interval_to_ege_string(sol1)
add_interval_task(
    statement="Решите неравенство x² − 5x + 6 < 0.",
    expected_answer=answer1,
    solution="Корни x=2, x=3. Ветви параболы вверх -> знак минус между корнями.",
    topic_title="Неравенства",
    source="agent-july-refill",
    source_ref="july-refill:nerav:1",
)

# 2) дробно-рациональное
sol2 = sp.solve_univariate_inequality((x + 3) / (x - 2) <= 0, x, relational=False)
answer2 = interval_to_ege_string(sol2)
add_interval_task(
    statement="Решите неравенство (x + 3)/(x − 2) ≤ 0.",
    expected_answer=answer2,
    solution="Нули числителя/знаменателя: -3 (включаем), 2 (исключаем, ОДЗ).",
    topic_title="Неравенства",
    source="agent-july-refill",
    source_ref="july-refill:nerav:2",
)

# 3) показательное
sol3 = sp.solve_univariate_inequality(2 ** x >= 8, x, relational=False)
answer3 = interval_to_ege_string(sol3)
add_interval_task(
    statement="Решите неравенство 2^x ≥ 8.",
    expected_answer=answer3,
    solution="8=2^3, основание 2>1 -> x≥3.",
    topic_title="Неравенства",
    source="agent-july-refill",
    source_ref="july-refill:nerav:3",
)

# 4) логарифмическое (с учётом ОДЗ внутри solve_univariate_inequality)
sol4 = sp.solve_univariate_inequality(sp.log(x + 1, 3) <= 2, x, relational=False)
answer4 = interval_to_ege_string(sol4)
add_interval_task(
    statement="Решите неравенство log₃(x + 1) ≤ 2.",
    expected_answer=answer4,
    solution="ОДЗ: x>-1. x+1≤9 -> x≤8. Итог: (-1; 8].",
    topic_title="Неравенства",
    source="agent-july-refill",
    source_ref="july-refill:nerav:4",
)


# ---------------------------------------------------------------------------
# Часть A.6 — Уравнения и неравенства с ОДЗ
# ---------------------------------------------------------------------------

# 1) логарифмическое уравнение с ОДЗ (число)
eq1_sols = sp.solveset(sp.Eq(sp.log(x - 2, 5), 2), x, domain=sp.Interval.open(2, sp.oo))
eq1_sol = list(eq1_sols)
assert len(eq1_sol) == 1
add_task(
    statement="Решите уравнение log₅(x − 2) = 2. Учтите ОДЗ.",
    expected_answer=fmt_num(eq1_sol[0]),
    solution="ОДЗ: x>2. x-2=5^2=25 -> x=27 (входит в ОДЗ).",
    topic_title="Уравнения и неравенства с ОДЗ",
    source="agent-july-refill",
    source_ref="july-refill:odz:1",
)

# 2) иррациональное уравнение с отбором постороннего корня
domain2 = sp.Interval(5, sp.oo)
eq2_sols = sp.solveset(sp.Eq(sp.sqrt(x + 7), x - 5), x, domain=domain2)
eq2_sol = [s for s in eq2_sols if s.is_real]
assert len(eq2_sol) == 1
add_task(
    statement="Решите уравнение √(x + 7) = x − 5. Учтите ОДЗ и отберите верный корень.",
    expected_answer=fmt_num(eq2_sol[0]),
    solution=(
        "ОДЗ: x≥5. Возводим в квадрат: x+7=x^2-10x+25 -> x^2-11x+18=0 -> "
        "x=9 или x=2. Корень x=2 не входит в ОДЗ (x≥5), остаётся x=9."
    ),
    topic_title="Уравнения и неравенства с ОДЗ",
    source="agent-july-refill",
    source_ref="july-refill:odz:2",
)

# 3) неравенство с корнем в знаменателе (ОДЗ строго внутри домена)
sol3b = sp.solve_univariate_inequality(
    (x - 4) / sp.sqrt(x + 1) >= 0, x, relational=False, domain=sp.Interval.open(-1, sp.oo)
)
answer3b = interval_to_ege_string(sol3b)
add_interval_task(
    statement="Решите неравенство (x − 4)/√(x + 1) ≥ 0. Учтите ОДЗ.",
    expected_answer=answer3b,
    solution=(
        "ОДЗ: x+1>0 -> x>-1 (знаменатель не может быть 0). На ОДЗ знаменатель "
        "положителен, знак дроби = знак (x-4) -> x≥4. Итог: [4; +∞)."
    ),
    topic_title="Уравнения и неравенства с ОДЗ",
    source="agent-july-refill",
    source_ref="july-refill:odz:3",
)

# 4) неравенство суммы логарифмов с ОДЗ
sol4b = sp.solve_univariate_inequality(
    sp.log(x * (x - 3), 2) <= 2, x, relational=False, domain=sp.Interval.open(3, sp.oo)
)
answer4b = interval_to_ege_string(sol4b)
add_interval_task(
    statement="Решите неравенство log₂(x) + log₂(x − 3) ≤ 2. Учтите ОДЗ.",
    expected_answer=answer4b,
    solution=(
        "ОДЗ: x>0 и x>3 -> x>3. log2(x(x-3))<=2 -> x(x-3)<=4 -> x^2-3x-4<=0 -> "
        "-1<=x<=4. Пересечение с ОДЗ: (3; 4]."
    ),
    topic_title="Уравнения и неравенства с ОДЗ",
    source="agent-july-refill",
    source_ref="july-refill:odz:4",
)


# ---------------------------------------------------------------------------
# Часть B — усложнённый блок с фото, пересчёт контрольных ответов кодом
# ---------------------------------------------------------------------------

PART_B_CONTROL = {
    "book-photo:062": "0,04",
    "book-photo:063": "27,9",
    "book-photo:065": "0,4",
    "book-photo:066": "-3",
    "book-photo:068": "25",
    "book-photo:069": "12",
}

part_b_results: list[tuple[str, str, str, bool]] = []

# 1) 2cos2a при sin a = -0.7
sin_a = sp.Rational(-7, 10)
cos2a_1 = 1 - 2 * sin_a ** 2
val1 = fmt_num(2 * cos2a_1)
part_b_results.append(("book-photo:062", val1, PART_B_CONTROL["book-photo:062"], val1 == PART_B_CONTROL["book-photo:062"]))
add_task(
    statement="⭐ Усложнённая. Найдите 2cos2α, если sinα = −0,7.",
    expected_answer=val1,
    solution="cos2α=1-2sin²α=1-2*0.49=0.02. 2cos2α=0.04.",
    topic_title="Вычисления: логарифмы и тригонометрия",
    source="book-photo",
    source_ref="book-photo:062",
)

# 2) 45cos2a при cos a = -0.9
cos_a = sp.Rational(-9, 10)
cos2a_2 = 2 * cos_a ** 2 - 1
val2 = fmt_num(45 * cos2a_2)
part_b_results.append(("book-photo:063", val2, PART_B_CONTROL["book-photo:063"], val2 == PART_B_CONTROL["book-photo:063"]))
add_task(
    statement="⭐ Усложнённая. Найдите 45cos2α, если cosα = −0,9.",
    expected_answer=val2,
    solution="cos2α=2cos²α-1=2*0.81-1=0.62. 45*0.62=27.9.",
    topic_title="Вычисления: логарифмы и тригонометрия",
    source="book-photo",
    source_ref="book-photo:063",
)

# 3) (24√a * 48√a) / (a * 16√a) при a=2.5
a_val = sp.Rational(5, 2)
expr3 = (a_val ** sp.Rational(1, 24) * a_val ** sp.Rational(1, 48)) / (a_val * a_val ** sp.Rational(1, 16))
val3 = fmt_num(sp.simplify(expr3))
part_b_results.append(("book-photo:065", val3, PART_B_CONTROL["book-photo:065"], val3 == PART_B_CONTROL["book-photo:065"]))
add_task(
    statement=(
        "⭐ Усложнённая. Найдите значение выражения "
        "(²⁴√a · ⁴⁸√a) / (a · ¹⁶√a) при a = 2,5."
    ),
    expected_answer=val3,
    solution="Показатель степени: 1/24+1/48-1-1/16 = -1 -> выражение = 1/a = 1/2,5 = 0,4.",
    topic_title="Вычисления: степени и корни",
    source="book-photo",
    source_ref="book-photo:065",
)

# 4) log_0.25 64
base4 = sp.Rational(1, 4)
val4_expr = sp.log(64, base4)
val4 = fmt_num(sp.simplify(val4_expr))
part_b_results.append(("book-photo:066", val4, PART_B_CONTROL["book-photo:066"], val4 == PART_B_CONTROL["book-photo:066"]))
add_task(
    statement="⭐ Усложнённая. Найдите значение выражения log₀,₂₅ 64.",
    expected_answer=val4,
    solution="(1/4)^x=64=4^3 -> 4^(-x)=4^3 -> x=-3.",
    topic_title="Вычисления: логарифмы и тригонометрия",
    source="book-photo",
    source_ref="book-photo:066",
)

# 5) (2^(4/7) * 5^(2/3))^21 / 10^12
expr5 = (2 ** sp.Rational(4, 7) * 5 ** sp.Rational(2, 3)) ** 21 / 10 ** 12
val5 = fmt_num(sp.simplify(expr5))
part_b_results.append(("book-photo:068", val5, PART_B_CONTROL["book-photo:068"], val5 == PART_B_CONTROL["book-photo:068"]))
add_task(
    statement="⭐ Усложнённая. Найдите значение выражения (2^(4/7) · 5^(2/3))²¹ / 10¹².",
    expected_answer=val5,
    solution="(2^(4/7))^21=2^12, (5^(2/3))^21=5^14. Итог: 2^12*5^14/10^12=5^2=25.",
    topic_title="Вычисления: степени и корни",
    source="book-photo",
    source_ref="book-photo:068",
)

# 6) 0.75^(1/4) * 4^(1/2) * 12^(3/4)
expr6 = sp.Rational(3, 4) ** sp.Rational(1, 4) * 4 ** sp.Rational(1, 2) * 12 ** sp.Rational(3, 4)
val6 = fmt_num(sp.simplify(expr6))
part_b_results.append(("book-photo:069", val6, PART_B_CONTROL["book-photo:069"], val6 == PART_B_CONTROL["book-photo:069"]))
add_task(
    statement="⭐ Усложнённая. Найдите значение выражения 0,75^(1/4) · 4^(1/2) · 12^(3/4).",
    expected_answer=val6,
    solution="0.75=3/4. (3/4)^(1/4)*2*12^(3/4) = 2*3^1*4^(1/2) = 2*3*2 = 12.",
    topic_title="Вычисления: степени и корни",
    source="book-photo",
    source_ref="book-photo:069",
)


# ---------------------------------------------------------------------------
# Отчёт
# ---------------------------------------------------------------------------

out_path = REPO_ROOT / "scratchpad" / "july_tasks.json"
out_path.write_text(json.dumps(TASKS, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"TOTAL TASKS: {len(TASKS)}")
print("\nPART B recompute vs control:")
all_match = True
for ref, computed, control, matched in part_b_results:
    print(f"  {ref}: computed={computed!r} control={control!r} match={matched}")
    all_match = all_match and matched
print(f"PART B ALL MATCH: {all_match}")

print("\nSelf-checks (answer_is_correct(expected, expected)):")
passed = sum(1 for _, ok in CHECKS if ok)
print(f"  {passed}/{len(CHECKS)} passed")

print(f"\nJSON written to: {out_path}")
