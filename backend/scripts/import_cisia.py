"""Import the explicitly requested CISIA math sample and create its bot missions.

Dry run by default. Apply: python -m scripts.import_cisia --apply
"""

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.application.use_cases import LearningService, RuleBasedReviewer
from app.domain.enums import AiPolicy, MissionStatus, Subject
from app.domain.multiple_choice import CISIA_SOURCE, choice_answer
from app.infrastructure.db import SessionLocal
from app.infrastructure.models import MissionORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "data/cisia"
    bundle = json.loads((root / "math.json").read_text(encoding="utf-8"))
    items = bundle["questions"]
    if sorted(q["number"] for q in items) != list(range(1, 21)):
        raise ValueError("Incomplete CISIA mathematics bundle")
    for q in items:
        choice_answer(q["expected_answer"])
        if hashlib.sha256((root / q["asset"]).read_bytes()).hexdigest() != q["asset_sha256"]:
            raise ValueError(f"Changed source image: {q['number']}")
    if not args.apply:
        print("Validated 20 mathematics source images and official choices; use --apply to import.")
        return
    student = UUID("00000000-0000-0000-0000-000000000000")
    with SessionLocal() as session:
        service = LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer())
        created = 0
        for q in items:
            ref = q["source_ref"]
            task = service.add_task(
                {
                    "subject": Subject.MATH_PROFILE,
                    "topic_id": None,
                    "task_number": f"CISIA-{q['number']:02d}",
                    "statement": (
                        "Источник: CISIA · English TOLC-I Sample Test (2021), "
                        f"вопрос {q['number']}, стр. {q['pdf_page']}. "
                        "Условие и варианты A–E — на изображении из методички."
                    ),
                    "expected_answer": q["expected_answer"],
                    "source": CISIA_SOURCE,
                    "source_ref": ref,
                    "source_url": f"tolc-i-sinavi-ornek-sorulari.pdf#page={q['pdf_page']}",
                }
            )
            if (
                task.source != CISIA_SOURCE
                or task.topic_id is not None
                or task.expected_answer != q["expected_answer"]
            ):
                raise ValueError(f"Conflicting existing CISIA task: {ref}")
            service.approve_task(task.id)
            exists = session.scalar(
                select(MissionORM).where(
                    MissionORM.student_id == student,
                    MissionORM.source_ref == ref,
                )
            )
            if exists is not None:
                continue
            service.create_mission(
                {
                    "student_id": student,
                    "subject": Subject.MATH_PROFILE,
                    "topic_id": None,
                    "task_id": task.id,
                    "title": f"CISIA · Математика · вопрос {q['number']}/20",
                    "instructions": (
                        "Сначала реши самостоятельно на бумаге. Затем нажми A–E "
                        "или пришли одну латинскую букву A, B, C, D или E. "
                        "Проверка — по официальному ключу; /skip — отложить, /cancel — выйти. "
                        "Это тренировка по образцу 2021 года."
                    ),
                    "status": MissionStatus.ACTIVE,
                    "ai_policy": AiPolicy.ATTEMPT_FIRST,
                    "threshold_percent": 100.0,
                    "due_date": date.today(),
                    "source_ref": ref,
                }
            )
            created += 1
        print(
            f"CISIA: 20 approved math tasks, {created} new missions; "
            "repeated import preserves attempts."
        )


if __name__ == "__main__":
    main()
