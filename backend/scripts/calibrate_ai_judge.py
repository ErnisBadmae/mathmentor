"""Offline-replay калибровка ИИ-судьи против детерминированного exact-авторитета.

Протокол перенесён из expert-agent ADR-013 («judge допускается к доверию только через
калибровку»); kappa-математика скопирована из канонического источника —
expert-agent ``app/services/retrieval/relevance_judge.py`` (сверка по VERSION ниже).

Что делает:
1. Берёт исторические попытки (``attempts.answer_text``) с эталоном (missions/tasks).
2. Дедуп по тройке (statement, expected, answer) — судья зовётся один раз на тройку,
   вес тройки = число реальных попыток.
3. Живой ``LlmShortAnswerJudge`` (тот же класс/промпт, что в проде) даёт мнение equivalent.
4. Сравнение с exact-авторитетом: agreement, Cohen's kappa, confusion matrix.
5. Расхождения выгружаются в JSONL на ручное ревью — автоматически они НЕ ошибки:
   - judge=1 / exact=0 — кандидаты «эквивалентная форма» (ценность судьи ИЛИ ложное
     спасение — решает человек);
   - judge=0 / exact=1 — судья бракует верное (опасные false negatives).

Запуск (нужен живой LLM; провайдер — из прод-настроек):
    python scripts/calibrate_ai_judge.py [--limit N] \
        [--out data/ai_judge_disagreements.jsonl] [--max-failure-rate 0.1]

Exit non-zero, если судья вернул None чаще ``--max-failure-rate`` (fail-closed) —
пригодно как acceptance ночного раннера.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.application.ports import AiAssessment  # noqa: E402
from app.domain.policies import answer_is_correct, numeric_mismatch  # noqa: E402

VERSION = "1.0"  # kappa: expert-agent relevance_judge (канонический источник)


class ShortAnswerJudgeLike(Protocol):
    async def assess(
        self, statement: str, correct_answer: str, student_answer: str | None
    ) -> AiAssessment | None: ...


@dataclass(frozen=True)
class ReplayRow:
    """Одна уникальная тройка (statement, expected, answer) из истории попыток."""

    statement: str
    expected: str
    answer: str
    weight: int  # сколько реальных попыток схлопнулось в тройку
    exact: bool  # детерминированный вердикт exact-политики
    numeric_stop: bool  # оба значения числовые и не совпали (авторитетный стоп)
    judge_label: int | None = None  # 1/0 = мнение судьи, None = сбой/не звался
    judge_extracted: str | None = None
    judge_feedback: str = ""


def dedupe_rows(raw: Iterable[tuple[str, str, str]]) -> list[ReplayRow]:
    """Схлопнуть попытки в уникальные тройки, сразу считая детерминированные вердикты."""
    weights: dict[tuple[str, str, str], int] = {}
    for statement, expected, answer in raw:
        key = (statement.strip(), expected.strip(), answer.strip())
        weights[key] = weights.get(key, 0) + 1
    rows = []
    for (statement, expected, answer), weight in sorted(weights.items()):
        rows.append(
            ReplayRow(
                statement=statement,
                expected=expected,
                answer=answer,
                weight=weight,
                exact=answer_is_correct(answer, expected),
                numeric_stop=numeric_mismatch(answer, expected),
            )
        )
    return rows


def collect_attempt_triples(limit: int | None = None) -> list[tuple[str, str, str]]:
    """Исторические попытки с ответом и эталоном (сырые тройки, до дедупа)."""
    from app.infrastructure.db import SessionLocal

    sql = """
        SELECT COALESCE(t.statement, m.instructions, m.title) AS statement,
               COALESCE(m.expected_answer, t.expected_answer) AS expected,
               a.answer_text AS answer
        FROM attempts a
        JOIN missions m ON m.id = a.mission_id
        LEFT JOIN tasks t ON t.id = m.task_id
        WHERE a.answer_text IS NOT NULL
          AND COALESCE(m.expected_answer, t.expected_answer) IS NOT NULL
        ORDER BY a.submitted_at
    """
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    with SessionLocal() as session:
        return [(r.statement or "", r.expected, r.answer) for r in session.execute(text(sql))]


async def judge_rows(rows: list[ReplayRow], judge: ShortAnswerJudgeLike) -> list[ReplayRow]:
    """Прогнать судью по тройкам; сбой на тройке = judge_label None (fail-closed)."""
    judged: list[ReplayRow] = []
    for index, row in enumerate(rows, start=1):
        assessment = await judge.assess(row.statement, row.expected, row.answer)
        if assessment is None:
            judged.append(replace(row, judge_label=None, judge_feedback="judge failed/None"))
        else:
            judged.append(
                replace(
                    row,
                    judge_label=int(assessment.equivalent),
                    judge_extracted=assessment.extracted_answer,
                    judge_feedback=assessment.feedback,
                )
            )
        if index % 10 == 0:
            print(f"[calibrate] judged {index}/{len(rows)}", file=sys.stderr)
    return judged


def cohen_kappa(tp: int, fp: int, fn: int, tn: int) -> float | None:
    """Cohen's kappa; None при вырожденных маргиналах. Копия из expert-agent (VERSION)."""
    n = tp + fp + fn + tn
    if n == 0:
        return None
    po = (tp + tn) / n
    pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
    if pe >= 1.0:
        return None
    return (po - pe) / (1 - pe)


def build_report(rows: list[ReplayRow], total_attempts: int) -> dict[str, object]:
    """Судья против exact-авторитета. Ось truth = exact-политика, ось pred = judge."""
    tp = fp = fn = tn = 0
    failures = 0
    for row in rows:
        if row.judge_label is None:
            failures += 1
        elif row.judge_label == 1 and row.exact:
            tp += 1
        elif row.judge_label == 1 and not row.exact:
            fp += 1
        elif row.judge_label == 0 and row.exact:
            fn += 1
        else:
            tn += 1
    n = tp + fp + fn + tn
    kappa = cohen_kappa(tp, fp, fn, tn)
    return {
        "version": VERSION,
        "unique_triples": len(rows),
        "total_attempts": total_attempts,
        "compared": n,
        "judge_failures": failures,
        "failure_rate": round(failures / len(rows), 4) if rows else None,
        "agreement": round((tp + tn) / n, 4) if n else None,
        "cohen_kappa": round(kappa, 4) if kappa is not None else None,
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "judge_rescues_to_review": fp,  # judge=1/exact=0: эквивалент или ложное спасение
        "judge_rejects_of_correct": fn,  # judge=0/exact=1: опасные false negatives
    }


def disagreement_records(rows: list[ReplayRow]) -> list[dict[str, object]]:
    """Расхождения судьи с exact — на ручное ревью (человек решает, кто прав)."""
    records = []
    for row in rows:
        if row.judge_label is None or int(row.exact) == row.judge_label:
            continue
        records.append(
            {
                "kind": "judge_rescue" if row.judge_label == 1 else "judge_reject",
                "statement": row.statement[:400],
                "expected": row.expected,
                "answer": row.answer,
                "weight": row.weight,
                "exact": row.exact,
                "numeric_stop": row.numeric_stop,
                "judge_extracted": row.judge_extracted,
                "judge_feedback": row.judge_feedback,
                "human_verdict": None,  # заполняет человек: judge_right | exact_right
            }
        )
    return records


async def main() -> int:
    try:  # Windows-консоль может быть cp1251
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="ограничить число попыток (смоук)")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/ai_judge_disagreements.jsonl"),
        help="JSONL с расхождениями на ручное ревью",
    )
    parser.add_argument("--max-failure-rate", type=float, default=0.1)
    args = parser.parse_args()

    from app.config import get_settings
    from app.infrastructure.llm import LlmShortAnswerJudge

    connection = get_settings().llm_connection()
    if connection is None:
        print("LLM provider is disabled in settings — калибровать нечего", file=sys.stderr)
        return 1

    triples = collect_attempt_triples(args.limit)
    rows = dedupe_rows(triples)
    if not rows:
        print("нет попыток с ответом и эталоном", file=sys.stderr)
        return 1

    judged = await judge_rows(rows, LlmShortAnswerJudge(connection))
    report = build_report(judged, total_attempts=len(triples))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    records = disagreement_records(judged)
    with args.out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    report["disagreements_out"] = str(args.out)
    report["disagreements"] = len(records)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    failure_rate = report["failure_rate"]
    if isinstance(failure_rate, float) and failure_rate > args.max_failure_rate:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
