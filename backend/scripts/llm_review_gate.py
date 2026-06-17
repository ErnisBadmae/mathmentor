"""Golden replay gate for the LLM reviewer (REQUIREMENTS §14).

Replays a small set of known EGE mistakes against the LIVE configured local model
and checks that each is classified into the expected ``error_category`` without
silently falling back to manual review or an empty answer. Run it before trusting
a new model / prompt / rubric version:

    python scripts/llm_review_gate.py [--tier mainline|expanded|all] [--json report.json]

Discipline (mainline = blocking, expanded = advisory) comes from
``!DOC/open-source/ENGLISHFRIEND_REUSE_ANALYSIS.md``. The evaluation functions are
pure and unit-tested in ``tests/test_llm_gate.py``; only ``main`` touches the model.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.application.ports import AttemptForReview, EvidenceDraft  # noqa: E402
from app.config import Settings  # noqa: E402
from app.domain.enums import (  # noqa: E402
    AttemptKind,
    AttemptMode,
    ErrorCategory,
    EvidenceStatus,
    Subject,
)

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
SCENARIOS_PATH = (
    Path(__file__).resolve().parents[1] / "tests" / "scenarios" / "error_categories.yaml"
)
MIN_FEEDBACK_CHARS = 15


@dataclass(frozen=True)
class GoldenScenario:
    name: str
    tier: str  # mainline | expanded
    subject: Subject
    kind: AttemptKind
    expected_category: ErrorCategory
    answer_text: str | None = None
    code_text: str | None = None
    expected_answer: str | None = None
    threshold_percent: float = 80
    must_contain_any: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GoldenResult:
    scenario: GoldenScenario
    failures: list[str]
    category: str = ""
    feedback_preview: str = ""

    @property
    def passed(self) -> bool:
        return not self.failures


def load_scenarios(path: Path) -> list[GoldenScenario]:
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [
        GoldenScenario(
            name=str(item["name"]),
            tier=str(item.get("tier", "expanded")),
            subject=Subject(item["subject"]),
            kind=AttemptKind(item["kind"]),
            expected_category=ErrorCategory(item["expected_category"]),
            answer_text=item.get("answer_text"),
            code_text=item.get("code_text"),
            expected_answer=item.get("expected_answer"),
            threshold_percent=float(item.get("threshold_percent", 80)),
            must_contain_any=list(item.get("must_contain_any") or []),
        )
        for item in raw
    ]


def evaluate_review(scenario: GoldenScenario, draft: EvidenceDraft) -> GoldenResult:
    """Pure check of one reviewer answer against a golden scenario (no I/O)."""
    failures: list[str] = []

    if draft.status == EvidenceStatus.NEEDS_MANUAL_REVIEW:
        failures.append(
            "fail-closed: модель ушла в manual review вместо классификации (LLM недоступна/мусор)"
        )

    feedback = (draft.feedback or "").strip()
    if len(feedback) < MIN_FEEDBACK_CHARS:
        failures.append(f"silent-fallback: feedback короче {MIN_FEEDBACK_CHARS} символов")

    if draft.error_category != scenario.expected_category:
        failures.append(
            f"категория {draft.error_category} != ожидаемой {scenario.expected_category}"
        )

    lowered = feedback.casefold()
    if scenario.must_contain_any and not any(
        m.casefold() in lowered for m in scenario.must_contain_any
    ):
        failures.append(f"нет ни одного ожидаемого маркера в feedback: {scenario.must_contain_any}")

    return GoldenResult(
        scenario=scenario,
        failures=failures,
        category=str(draft.error_category),
        feedback_preview=feedback[:160],
    )


def summarize(results: list[GoldenResult]) -> dict:
    mainline = [r for r in results if r.scenario.tier == "mainline"]
    mainline_failed = [r for r in mainline if not r.passed]
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "mainline_total": len(mainline),
        "mainline_failed": len(mainline_failed),
        "gate_green": not mainline_failed,
        "failures": [
            {"scenario": r.scenario.name, "tier": r.scenario.tier, "failures": r.failures}
            for r in results
            if not r.passed
        ],
    }


async def _run(tier: str) -> dict:
    from app.infrastructure.llm import OpenAICompatibleReviewer

    # Load the repo-root .env explicitly so the gate works regardless of cwd
    # (Settings' default env_file is resolved relative to the current directory).
    connection = Settings(_env_file=str(ENV_FILE)).llm_connection()
    if connection is None:
        sys.exit("LLM_PROVIDER is disabled — set vllm or llama_cpp to run the golden gate.")
    reviewer = OpenAICompatibleReviewer(connection)

    scenarios = load_scenarios(SCENARIOS_PATH)
    if tier != "all":
        scenarios = [s for s in scenarios if s.tier == tier]

    results: list[GoldenResult] = []
    for scenario in scenarios:
        print(f"[{scenario.tier}] {scenario.name} … ", end="", flush=True)
        draft = await reviewer.review_attempt(
            AttemptForReview(
                subject=scenario.subject,
                mission_title=scenario.name,
                topic_title=None,
                kind=scenario.kind,
                mode=AttemptMode.CLEAN_SHEET,
                answer_text=scenario.answer_text,
                code_text=scenario.code_text,
                expected_answer=scenario.expected_answer,
                threshold_percent=scenario.threshold_percent,
            )
        )
        result = evaluate_review(scenario, draft)
        results.append(result)
        print("OK" if result.passed else f"FAIL: {result.failures}")

    return summarize(results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=["mainline", "expanded", "all"], default="mainline")
    parser.add_argument("--json", type=Path, default=None, help="Write JSON report to file")
    args = parser.parse_args()

    report = asyncio.run(_run(args.tier))
    print(
        f"\nGate: {'GREEN' if report['gate_green'] else 'RED'} | "
        f"passed {report['passed']}/{report['total']} "
        f"(mainline failed: {report['mainline_failed']}/{report['mainline_total']})"
    )
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Report: {args.json}")
    sys.exit(0 if report["gate_green"] else 1)


if __name__ == "__main__":
    main()
