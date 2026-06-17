"""Учебная программа подготовки к ЕГЭ 2027 как фиксированные данные (из ``контроль``).

Фазы — это метаданные программы (метка + окно дат + порядок). Они не хранятся в БД:
тема ссылается на фазу по ключу (``TopicORM.phase``), а ``current_phase_key`` чисто
определяет, в какой фазе ребёнок сейчас. Гранулярные темы сеются для летней дуги
(июнь + июль–август); поздние фазы — крупные вехи без тем.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Phase:
    key: str
    label: str
    start: date
    end: date
    order: int


PHASES: tuple[Phase, ...] = (
    Phase("june_diagnostics", "Июнь · Диагностика (Срез 1)", date(2026, 6, 1), date(2026, 6, 30), 1),
    Phase(
        "july_aug_foundation",
        "Июль–август · Фундамент (Срез 2/3)",
        date(2026, 7, 1),
        date(2026, 8, 10),
        2,
    ),
    Phase("rest_august", "Август · Отдых", date(2026, 8, 11), date(2026, 8, 31), 3),
    Phase("consolidation", "Сентябрь–октябрь · Консолидация", date(2026, 9, 1), date(2026, 10, 31), 4),
    Phase("deepening", "Ноябрь–декабрь · Углубление", date(2026, 11, 1), date(2026, 12, 31), 5),
    Phase("peak", "Январь–февраль · Пик", date(2027, 1, 1), date(2027, 2, 28), 6),
    Phase("simulation", "Март–апрель · Симуляция", date(2027, 3, 1), date(2027, 4, 30), 7),
    Phase("final", "Май · Подводка", date(2027, 5, 1), date(2027, 5, 31), 8),
)

PHASES_BY_KEY: dict[str, Phase] = {phase.key: phase for phase in PHASES}


def current_phase_key(today: date) -> str | None:
    """Phase whose date window contains ``today`` (None if outside the program)."""
    for phase in PHASES:
        if phase.start <= today <= phase.end:
            return phase.key
    return None
