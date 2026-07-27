"""Шаблонный генератор задач (офлайн, по сигналу спроса).

Принцип — тот же анти-poison, что в наполнении банка вручную: **ответ вычисляет код,
который сам владеет решением**, ИИ не участвует. Каждый шаблон — чистая функция
``(rng, difficulty) -> (statement, expected_answer, solution)``; ответ считается по формуле
и проходит внутренний ``assert`` (санити) + формат-guard ``answer_is_correct(ans, ans)``
(и ``parse_interval_answer`` для интервалов) перед вставкой. Не прошло — задача молча
пропускается (fail-closed).

Вставка: DRAFT через ``LearningService.add_task`` (``source="generated"``), дедуп по
контент-хешу ``source_ref=gen:<slug>:<sha1(statement)[:12]>`` (уникальный ``tasks.source_ref``
не даст дублей при повторных прогонах). Апрув — отдельным осознанным шагом (флаг ``--approve``).

Запуск из ``backend/``:

    python -m scripts.generate_tasks --topic "Вычисления: степени и корни" --count 5
    python -m scripts.generate_tasks --from-signal --count 5 --approve
"""

from __future__ import annotations

import argparse
import hashlib
import random
import re
from collections.abc import Callable
from fractions import Fraction
from uuid import UUID

from sqlalchemy import select

from app.application.use_cases import LearningService
from app.domain.enums import TaskStatus
from app.domain.figures import parse_interval_answer
from app.domain.policies import answer_is_correct
from app.infrastructure.db import SessionLocal
from app.infrastructure.models import TopicORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork

PILOT_STUDENT_ID = UUID("00000000-0000-0000-0000-000000000000")

Template = Callable[[random.Random, int], tuple[str, str, str]]


# ---- форматирование ответа строго под грейдер (app.domain.policies) ---------


def fmt_num(value: object) -> str:
    """Число → строка ответа: целое — голыми цифрами (без разрядных точек), иначе дробь
    a/b (грейдер сравнивает дроби и десятичные численно)."""
    fr = Fraction(value).limit_denominator(10**6)
    if fr.denominator == 1:
        return str(fr.numerator)
    return f"{fr.numerator}/{fr.denominator}"


def closed_interval(lo: int, hi: int) -> str:
    return f"[{lo}; {hi}]"


def outer_union(lo: int, hi: int) -> str:
    return f"(-∞; {lo}] ∪ [{hi}; +∞)"


# ---- шаблоны (ключ = точный TopicORM.title) ---------------------------------
# Каждый шаблон считает ответ кодом + внутренний assert. Несколько шаблонов на тему = «тип».


def _powers(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    base = rng.choice([2, 3, 5])
    p, q = rng.randint(2, 3 + difficulty), rng.randint(1, 2 + difficulty)
    r = rng.randint(1, p)  # p+q-r > 0
    exp = p + q - r
    value = base**exp
    assert value == base ** (p + q - r)
    statement = f"Найдите значение выражения {base}^{p} · {base}^{q} / {base}^{r}."
    solution = f"{base}^({p}+{q}−{r}) = {base}^{exp} = {value}."
    return statement, fmt_num(value), solution


def _logarithm(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    base = rng.choice([2, 3, 5, 10])
    k = rng.randint(2, 3 + difficulty)
    x = base**k
    assert base**k == x
    statement = f"Найдите значение выражения log_{base}({x})."
    solution = f"{x} = {base}^{k}, поэтому log_{base}({x}) = {k}."
    return statement, fmt_num(k), solution


def _simple_equation_exp(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    base = rng.choice([2, 3, 5])
    k = rng.randint(2, 3 + difficulty)
    rhs = base**k
    statement = f"Решите уравнение {base}^x = {rhs}."
    solution = f"{rhs} = {base}^{k}, поэтому x = {k}."
    return statement, fmt_num(k), solution


def _simple_equation_log(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    base = rng.choice([2, 3, 5])
    k = rng.randint(2, 3 + difficulty)
    x = base**k
    statement = f"Решите уравнение log_{base}(x) = {k}."
    solution = f"x = {base}^{k} = {x}."
    return statement, fmt_num(x), solution


def _percent(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    hundreds = rng.randint(2, 5 + 3 * difficulty)
    price = hundreds * 100
    p = rng.choice([10, 20, 25, 40, 50])
    result = price * (100 - p) // 100
    assert price * (100 - p) % 100 == 0
    statement = (
        f"Товар стоил {price} руб. Цену снизили на {p}%. "
        "Сколько рублей стал стоить товар?"
    )
    solution = f"{price} · (100−{p})/100 = {price} · {100 - p}/100 = {result}."
    return statement, fmt_num(result), solution


def _probability_addition(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    pa = Fraction(rng.randint(2, 5), 10)
    pb = Fraction(rng.randint(2, 5), 10)
    lo = max(0, int(pa * 10) + int(pb * 10) - 10)  # P(A∩B) ≥ P(A)+P(B)−1
    hi = min(int(pa * 10), int(pb * 10))  # и ≤ min(P(A), P(B))
    pab = Fraction(rng.randint(lo, hi), 10)
    p = pa + pb - pab
    assert 0 <= p <= 1
    statement = (
        f"Вероятность события A равна {fmt_num(pa)}, события B — {fmt_num(pb)}, "
        f"а события «A и B» — {fmt_num(pab)}. Найдите вероятность события «A или B»."
    )
    solution = (
        f"P(A∪B) = P(A)+P(B)−P(A∩B) = "
        f"{fmt_num(pa)}+{fmt_num(pb)}−{fmt_num(pab)} = {fmt_num(p)}."
    )
    return statement, fmt_num(p), solution


_PYTH = [(3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 15, 17), (9, 12, 15), (7, 24, 25)]


def _vector_length(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    a, b, c = rng.choice(_PYTH)
    if rng.random() < 0.5:
        a = -a
    assert a * a + b * b == c * c
    statement = f"Найдите длину вектора ({a}; {b})."
    solution = f"√({a}² + {b}²) = √{a * a + b * b} = {c}."
    return statement, fmt_num(c), solution


def _vector_dot(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    x1, y1 = rng.randint(-5, 5), rng.randint(-5, 5)
    x2, y2 = rng.randint(-5, 5), rng.randint(-5, 5)
    dot = x1 * x2 + y1 * y2
    statement = f"Найдите скалярное произведение векторов ({x1}; {y1}) и ({x2}; {y2})."
    solution = f"{x1}·{x2} + {y1}·{y2} = {dot}."
    return statement, fmt_num(dot), solution


def _derivative_physical(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    a = rng.randint(1, 2 + difficulty)
    b = rng.randint(1, 5)
    t0 = rng.randint(1, 3 + difficulty)
    v = 2 * a * t0 + b  # s(t)=a t^2 + b t + c ; v=s'=2a t + b
    statement = (
        f"Точка движется по закону s(t) = {a}t² + {b}t + 3 (t в секундах, s в метрах). "
        f"Найдите скорость в момент t = {t0} c (в м/с)."
    )
    solution = f"v(t) = s'(t) = {2 * a}t + {b}; v({t0}) = {2 * a}·{t0} + {b} = {v}."
    return statement, fmt_num(v), solution


def _derivative_geometric(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    a = rng.randint(1, 2 + difficulty)
    b = rng.randint(-4, 4)
    x0 = rng.randint(-2, 3)
    slope = 2 * a * x0 + b  # f(x)=a x^2 + b x + c ; f'=2a x + b
    statement = (
        f"Найдите угловой коэффициент касательной к графику функции "
        f"f(x) = {a}x² + {b}x + 1 в точке x₀ = {x0}."
    )
    solution = f"f'(x) = {2 * a}x + {b}; f'({x0}) = {slope}."
    return statement, fmt_num(slope), solution


def _inequality_closed(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    r1 = rng.randint(-6, 1)
    r2 = r1 + rng.randint(1, 4 + difficulty)
    b = -(r1 + r2)
    c = r1 * r2
    b_str = f"+ {b}x" if b >= 0 else f"− {abs(b)}x"
    c_str = f"+ {c}" if c >= 0 else f"− {abs(c)}"
    statement = f"Решите неравенство x² {b_str} {c_str} ≤ 0. Ответ запишите в виде промежутка."
    solution = f"Корни {r1} и {r2}; парабола ветвями вверх, поэтому x ∈ [{r1}; {r2}]."
    return statement, closed_interval(r1, r2), solution


def _inequality_outer(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    r1 = rng.randint(-6, 1)
    r2 = r1 + rng.randint(1, 4 + difficulty)
    b = -(r1 + r2)
    c = r1 * r2
    b_str = f"+ {b}x" if b >= 0 else f"− {abs(b)}x"
    c_str = f"+ {c}" if c >= 0 else f"− {abs(c)}"
    statement = f"Решите неравенство x² {b_str} {c_str} ≥ 0. Ответ запишите в виде промежутков."
    solution = f"Корни {r1} и {r2}; вне корней выражение ≥ 0: (-∞; {r1}] ∪ [{r2}; +∞)."
    return statement, outer_union(r1, r2), solution


_LOGIC_EXPRS = [
    ("(A ∧ ¬B) ∨ C", lambda a, b, c: (a and not b) or c),
    ("(A ∨ B) ∧ ¬C", lambda a, b, c: (a or b) and not c),
    ("¬A ∨ (B ∧ C)", lambda a, b, c: (not a) or (b and c)),
    ("(A → B) ∧ C", lambda a, b, c: ((not a) or b) and c),
]


def _logic_count(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    label, fn = rng.choice(_LOGIC_EXPRS)
    count = sum(
        1
        for a in (False, True)
        for b in (False, True)
        for c in (False, True)
        if fn(a, b, c)
    )
    statement = (
        "Сколько существует наборов значений логических переменных A, B, C, при которых "
        f"выражение {label} истинно?"
    )
    solution = f"Перебор 8 наборов даёт {count} истинных."
    return statement, fmt_num(count), solution


def _combinatorics_noadj(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    k = rng.randint(3, 4 + difficulty)
    n = rng.randint(3, 4 + difficulty)
    count = k * (k - 1) ** (n - 1)
    statement = (
        f"Из алфавита в {k} букв составляют слова длины {n}. Сколько таких слов, в которых "
        "никакие две соседние буквы не совпадают?"
    )
    solution = f"{k}·({k}−1)^({n}−1) = {k}·{k - 1}^{n - 1} = {count}."
    return statement, fmt_num(count), solution


def _divisor_count(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    primes = rng.sample([2, 3, 5, 7], k=2)
    e1 = rng.randint(1, 2 + difficulty)
    e2 = rng.randint(1, 1 + difficulty)
    n = primes[0] ** e1 * primes[1] ** e2
    count = (e1 + 1) * (e2 + 1)
    brute = sum(1 for d in range(1, n + 1) if n % d == 0)
    assert brute == count, (n, brute, count)
    statement = f"Сколько натуральных делителей у числа {n}?"
    solution = f"{n} = {primes[0]}^{e1}·{primes[1]}^{e2}; делителей ({e1}+1)·({e2}+1) = {count}."
    return statement, fmt_num(count), solution


def _python_arithmetic(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    n = rng.randint(100, 100 + 900 * difficulty)
    a = rng.choice([7, 9, 11, 13])
    out = n % a
    statement = f"Что выведет программа на Python?\n\nn = {n}\nprint(n % {a})"
    solution = f"{n} % {a} = {out}."
    return statement, fmt_num(out), solution


def _python_for(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    n = rng.randint(20, 20 + 30 * difficulty)
    d = rng.choice([3, 4, 5, 7])
    total = sum(i for i in range(1, n + 1) if i % d == 0)
    statement = (
        "Что выведет программа на Python?\n\n"
        f"s = 0\nfor i in range(1, {n + 1}):\n    if i % {d} == 0:\n        s += i\nprint(s)"
    )
    solution = f"Сумма кратных {d} от 1 до {n} равна {total}."
    return statement, fmt_num(total), solution


TEMPLATES: dict[str, list[Template]] = {
    "Вычисления: степени и корни": [_powers],
    "Вычисления: логарифмы и тригонометрия": [_logarithm],
    "Простейшие уравнения (показательные, логарифмические)": [
        _simple_equation_exp,
        _simple_equation_log,
    ],
    "Текстовые задачи на проценты": [_percent],
    "Вероятность: теорема сложения": [_probability_addition],
    "Векторы": [_vector_length, _vector_dot],
    "Производная: физический смысл": [_derivative_physical],
    "Производная: геометрический смысл": [_derivative_geometric],
    "Неравенства": [_inequality_closed, _inequality_outer],
    "Логика: таблицы истинности": [_logic_count],
    "Комбинаторика: подсчёт слов и чисел": [_combinatorics_noadj],
    "Делители числа (Задание 25)": [_divisor_count],
    "Python: арифметика, типы, %, //": [_python_arithmetic],
    "Python: цикл for и range": [_python_for],
}

# Интервальные темы: ответ проверяем ещё и parse_interval_answer.
_INTERVAL_TOPICS = {"Неравенства"}


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "topic"


def _verify(expected: str, is_interval: bool) -> bool:
    """Формат-guard перед вставкой (корректность даёт вычисляющий код + assert в шаблоне):
    ответ должен грейдиться сам с собой, интервал — парситься."""
    if not answer_is_correct(expected, expected):
        return False
    if is_interval and parse_interval_answer(expected) is None:
        return False
    return True


def generate_for_topic(
    service: LearningService,
    topic: TopicORM,
    count: int,
    seed: int,
) -> list[UUID]:
    templates = TEMPLATES.get(topic.title)
    if not templates:
        return []
    is_interval = topic.title in _INTERVAL_TOPICS
    rng = random.Random(f"{topic.id}:{seed}")
    created: list[UUID] = []
    attempts = 0
    while len(created) < count and attempts < count * 20:
        attempts += 1
        template = rng.choice(templates)
        difficulty = rng.randint(1, 3)
        try:
            statement, expected, solution = template(rng, difficulty)
        except AssertionError:
            continue  # санити не сошлась — пропускаем (fail-closed)
        if not _verify(expected, is_interval):
            continue
        digest = hashlib.sha1(statement.encode("utf-8")).hexdigest()[:12]
        source_ref = f"gen:{_slug(topic.title)}:{digest}"
        task = service.add_task(
            {
                "subject": topic.subject,
                "topic_id": topic.id,
                "statement": statement,
                "expected_answer": expected,
                "solution": solution,
                "source": "generated",
                "source_url": None,
                "source_ref": source_ref,
                "status": TaskStatus.DRAFT,
            }
        )
        created.append(task.id)
    service._uow.commit()
    return created


def _resolve_topics(service: LearningService, args: argparse.Namespace) -> list[TopicORM]:
    session = service._uow.session
    if args.topic:
        topic = session.scalar(select(TopicORM).where(TopicORM.title == args.topic))
        return [topic] if topic is not None else []
    titles: list[str]
    if args.from_signal:
        demand = service.demand_by_topic(args.signal_days)
        titles = [
            str(row["title"])
            for row in demand
            if row["shortage"] > 0 and str(row["title"]) in TEMPLATES
        ]
    else:
        titles = list(TEMPLATES.keys())
    topics = []
    for title in titles:
        topic = session.scalar(select(TopicORM).where(TopicORM.title == title))
        if topic is not None:
            topics.append(topic)
    return topics


def main() -> None:
    parser = argparse.ArgumentParser(description="Шаблонный генератор задач (DRAFT).")
    parser.add_argument("--topic", default=None, help="Точное название темы (иначе все).")
    parser.add_argument("--count", type=int, default=5, help="Сколько задач на тему.")
    parser.add_argument("--from-signal", action="store_true", help="Только темы с дефицитом.")
    parser.add_argument("--signal-days", type=int, default=30, help="Окно сигнала спроса, дней.")
    parser.add_argument("--seed", type=int, default=0, help="Зерно генерации.")
    parser.add_argument("--approve", action="store_true", help="Сразу одобрить созданные DRAFT.")
    args = parser.parse_args()

    with SessionLocal() as session:
        service = LearningService(SqlAlchemyUnitOfWork(session), _NoReviewer())
        topics = _resolve_topics(service, args)
        if not topics:
            print("Нет тем под генерацию (проверь --topic / наличие шаблона / сигнал).")
            return
        total_created = 0
        for topic in topics:
            created = generate_for_topic(service, topic, args.count, args.seed)
            if args.approve:
                for task_id in created:
                    service.approve_task(task_id)
            total_created += len(created)
            status = "approved" if args.approve else "draft"
            print(f"{topic.title}: +{len(created)} задач ({status})")
        print(f"Итого создано: {total_created}")


class _NoReviewer:
    """Генератор ничего не оценивает — ревьюер не нужен, но LearningService требует его."""

    async def review_attempt(self, _attempt: object) -> object:  # pragma: no cover
        raise NotImplementedError("generator does not review attempts")


if __name__ == "__main__":
    main()
