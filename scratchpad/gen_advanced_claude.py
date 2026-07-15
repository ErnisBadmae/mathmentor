"""Усложнённые задачи (⭐) от старшей модели: ответы вычисляются кодом (анти-poison).

Запуск с хоста: backend/.venv312/Scripts/python.exe scratchpad/gen_advanced_claude.py
Идемпотентно по source_ref (повторный запуск ничего не дублирует).
"""

import sys
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import sympy as sp

from app.domain.enums import Subject, TaskStatus
from app.domain.figures import parse_interval_answer
from app.domain.policies import answer_is_correct
from app.infrastructure.db import SessionLocal
from app.infrastructure.models import TaskORM, TopicORM

x = sp.Symbol("x", real=True)


def fmt(v) -> str:
    """Число -> строка ответа в формате банка (десятичная запятая, без хвостовых нулей)."""
    f = Fraction(v).limit_denominator(10**6)
    if f.denominator == 1:
        return str(f.numerator)
    s = f"{float(f):.6f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def computed_tasks() -> list[dict]:
    tasks: list[dict] = []

    # --- Вычисления: логарифмы и тригонометрия ---
    v = sp.simplify(49 ** (sp.log(8) / sp.log(7)))  # 49^(log_7 8) = 8^2
    assert v == 64, v
    tasks.append(dict(
        topic="Вычисления: логарифмы и тригонометрия",
        ref="claude-adv:log:1",
        statement="⭐ Усложнённая. Найдите значение выражения 49^(log₇ 8).",
        answer=fmt(int(v)),
        solution="49^(log₇8) = 7^(2·log₇8) = (7^(log₇8))² = 8² = 64.",
    ))

    sin_a = Fraction(6, 10)
    cos_a = -Fraction(8, 10)  # α ∈ (π/2; π): cos < 0; проверка тождества ниже
    assert sin_a**2 + cos_a**2 == 1
    tg = sin_a / cos_a
    assert tg == Fraction(-3, 4)
    tasks.append(dict(
        topic="Вычисления: логарифмы и тригонометрия",
        ref="claude-adv:trig:1",
        statement="⭐ Усложнённая. Найдите tg α, если sin α = 0,6 и α ∈ (π/2; π).",
        answer=fmt(tg),
        solution="cos²α = 1 − 0,36 = 0,64; во второй четверти cos α = −0,8. tg α = 0,6/(−0,8) = −0,75.",
    ))

    expr = 5 * sp.sin(sp.rad(74)) / (sp.cos(sp.rad(37)) * sp.sin(sp.rad(37)))
    assert abs(float(expr) - 10) < 1e-12, float(expr)  # sin74° = 2 sin37° cos37° (точно 10)
    v = 10
    tasks.append(dict(
        topic="Вычисления: логарифмы и тригонометрия",
        ref="claude-adv:trig:2",
        statement="⭐ Усложнённая. Найдите значение выражения 5·sin 74° / (cos 37° · sin 37°).",
        answer=fmt(int(v)),
        solution="sin 74° = sin(2·37°) = 2·sin 37°·cos 37°. Дробь равна 5·2 = 10.",
    ))

    # --- Вычисления: степени и корни ---
    v = sp.simplify((3 ** sp.Rational(5, 7) * 9 ** sp.Rational(1, 7)) ** 4 / 27)
    assert v == 3, v
    tasks.append(dict(
        topic="Вычисления: степени и корни",
        ref="claude-adv:pow:1",
        statement="⭐ Усложнённая. Найдите значение выражения (3^(5/7) · 9^(1/7))⁴ / 27.",
        answer=fmt(int(v)),
        solution="3^(5/7)·9^(1/7) = 3^(5/7+2/7) = 3. Тогда 3⁴/27 = 81/27 = 3.",
    ))

    v = sp.sqrt(160**2 - 96**2)
    assert v == 128, v
    tasks.append(dict(
        topic="Вычисления: степени и корни",
        ref="claude-adv:pow:2",
        statement="⭐ Усложнённая. Найдите значение выражения √(160² − 96²).",
        answer=fmt(int(v)),
        solution="160²−96² = (160−96)(160+96) = 64·256. Корень: 8·16 = 128.",
    ))

    v = sp.simplify(5 ** (sp.sqrt(7) + 3) / 5 ** (sp.sqrt(7) + 1))
    assert v == 25, v
    tasks.append(dict(
        topic="Вычисления: степени и корни",
        ref="claude-adv:pow:3",
        statement="⭐ Усложнённая. Найдите значение выражения 5^(√7+3) / 5^(√7+1).",
        answer=fmt(int(v)),
        solution="При делении степеней показатели вычитаются: (√7+3)−(√7+1) = 2, итог 5² = 25.",
    ))

    # --- Векторы ---
    xs = sp.solve(sp.Eq(3 * 6 - (-4) * sp.Symbol("t"), 0))  # коллинеарность: 3·6 − (−4)·t = 0
    assert len(xs) == 1 and xs[0] == sp.Rational(-9, 2), xs
    tasks.append(dict(
        topic="Векторы",
        ref="claude-adv:vec:1",
        statement="⭐ Усложнённая. Векторы a(3; −4) и b(x; 6) коллинеарны. Найдите x.",
        answer=fmt(Fraction(-9, 2)),
        solution="Коллинеарность: 3·6 − (−4)·x = 0 → 18 + 4x = 0 → x = −4,5.",
    ))

    v = sp.simplify(4 * sp.sqrt(2) * sp.cos(sp.rad(135)))
    assert v == -4, v
    tasks.append(dict(
        topic="Векторы",
        ref="claude-adv:vec:2",
        statement="⭐ Усложнённая. Длины векторов a и b равны 4 и √2, угол между ними 135°. "
                  "Найдите скалярное произведение a·b.",
        answer=fmt(-4),
        solution="a·b = |a|·|b|·cos135° = 4·√2·(−√2/2) = −4.",
    ))

    # --- Неравенства ---
    sol = sp.solve_univariate_inequality((x**2 - 9) / (x**2 + 4) <= 0, x, relational=False)
    assert sol == sp.Interval(-3, 3), sol
    ans = "[-3; 3]"
    assert parse_interval_answer(ans) is not None
    tasks.append(dict(
        topic="Неравенства",
        ref="claude-adv:ineq:1",
        statement="⭐ Усложнённая. Решите неравенство (x² − 9)/(x² + 4) ≤ 0.",
        answer=ans,
        solution="Знаменатель x²+4 > 0 всегда, знак дроби = знак (x²−9): x²≤9 → [−3; 3].",
    ))

    t = sp.Symbol("t", positive=True)
    roots = sp.solve(sp.Eq(t**2 - 3 * t - 4, 0), t)
    assert roots == [4], roots  # t=2^x > 0, годится только t > 4 → x > 2
    assert (4 ** 2.1 - 3 * 2 ** 2.1 - 4) > 0 and (4 ** 1.9 - 3 * 2 ** 1.9 - 4) < 0
    ans = "(2; +∞)"
    assert parse_interval_answer(ans) is not None
    tasks.append(dict(
        topic="Неравенства",
        ref="claude-adv:ineq:2",
        statement="⭐ Усложнённая. Решите неравенство 4^x − 3·2^x − 4 > 0.",
        answer=ans,
        solution="Замена t = 2^x > 0: t²−3t−4 > 0 → (t−4)(t+1) > 0 → t > 4 → 2^x > 4 → x > 2.",
    ))

    # --- Простейшие уравнения (показательные, логарифмические) ---
    roots = sorted(sp.solve(sp.Eq(2 ** (x**2 - 4 * x), sp.Rational(1, 8)), x))
    assert roots == [1, 3], roots
    tasks.append(dict(
        topic="Простейшие уравнения (показательные, логарифмические)",
        ref="claude-adv:eq:1",
        statement="⭐ Усложнённая. Решите уравнение 2^(x²−4x) = 1/8. "
                  "Если корней несколько, в ответе укажите больший.",
        answer=fmt(max(roots)),
        solution="1/8 = 2⁻³ → x²−4x = −3 → x²−4x+3 = 0 → x = 1 или x = 3. Больший: 3.",
    ))

    root = sp.solve(sp.Eq(sp.log(sp.log(x, 3), 2), 1), x)
    assert root == [9], root
    tasks.append(dict(
        topic="Простейшие уравнения (показательные, логарифмические)",
        ref="claude-adv:eq:2",
        statement="⭐ Усложнённая. Решите уравнение log₂(log₃ x) = 1.",
        answer=fmt(9),
        solution="log₃x = 2¹ = 2 → x = 3² = 9. ОДЗ (log₃x > 0, x > 0) выполнена.",
    ))

    for tsk in tasks:
        assert answer_is_correct(tsk["answer"], tsk["answer"]), tsk["ref"]
    return tasks


def main() -> None:
    tasks = computed_tasks()
    session = SessionLocal()
    added, skipped = [], []
    try:
        topics = {
            t.title: t.id
            for t in session.query(TopicORM).filter_by(subject=Subject.MATH_PROFILE)
        }
        for tsk in tasks:
            if session.query(TaskORM).filter_by(source_ref=tsk["ref"]).first() is not None:
                skipped.append(tsk["ref"])
                continue
            session.add(TaskORM(
                id=uuid4(),
                subject=Subject.MATH_PROFILE,
                topic_id=topics[tsk["topic"]],
                task_number=None,
                statement=tsk["statement"],
                expected_answer=tsk["answer"],
                solution=tsk["solution"],
                error_category=None,
                status=TaskStatus.APPROVED,
                source="agent-advanced",
                source_ref=tsk["ref"],
                created_at=datetime.now(UTC),
            ))
            added.append(f'{tsk["ref"]} | {tsk["topic"]} | ответ {tsk["answer"]}')
        session.commit()
    finally:
        session.close()
    print(f"Добавлено: {len(added)}, пропущено (уже были): {len(skipped)}")
    for line in added:
        print("  +", line)


if __name__ == "__main__":
    main()
