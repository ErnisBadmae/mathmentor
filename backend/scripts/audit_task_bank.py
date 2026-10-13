"""Аудит банка: у одобренной дрилл-задачи ответ должен записываться в бланк ЕГЭ.

Гейт в ``LearningService.approve_task`` защищает только то, что одобряют ПОСЛЕ него.
Этот скрипт проверяет уже одобренное — прогонять после массовых заливок и миграций.
Правило одно и то же (``answer_fits_exam_blank``), продублировать его негде.

    python -m scripts.audit_task_bank

Код возврата 1, если нашлись негодные задачи — годится для CI.
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from app.application.use_cases import LearningService
from app.domain.enums import TaskStatus
from app.domain.policies import answer_fits_exam_blank
from app.infrastructure.db import SessionLocal
from app.infrastructure.models import TaskORM


def main() -> int:
    with SessionLocal() as session:
        tasks = session.scalars(
            select(TaskORM).where(TaskORM.status == TaskStatus.APPROVED)
        ).all()
        offenders = [
            (task.expected_answer, task.source, getattr(task.topic, "title", "—"), task.source_ref)
            for task in tasks
            # часть 2 проверяет человек: ответ бывает символьным (√, интервалы), не бланковым
            if not LearningService._requires_manual_review_path(
                {"topic_title": getattr(task.topic, "title", None)}
            )
            and not answer_fits_exam_blank(task.expected_answer)
        ]

    print(f"Проверено одобренных дрилл-задач: {len(tasks)}")
    if not offenders:
        print("Все ответы записываются в бланк ЕГЭ.")
        return 0

    print(f"НЕ записываются в бланк: {len(offenders)}")
    for answer, source, title, source_ref in offenders:
        print(f"  {answer!r} | {source} | {title} | {source_ref}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
