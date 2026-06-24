"""Small test-only scenario gate for document AI quality checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

Tier = Literal["mainline", "expanded"]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Scenario:
    slug: str
    tier: Tier
    run: Callable[[], list[CheckResult]]
    description: str = ""


@dataclass(frozen=True)
class ScenarioReport:
    slug: str
    tier: Tier
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [check for check in self.checks if not check.passed]


@dataclass(frozen=True)
class GateReport:
    reports: list[ScenarioReport]

    @property
    def mainline_reports(self) -> list[ScenarioReport]:
        return [report for report in self.reports if report.tier == "mainline"]

    @property
    def expanded_reports(self) -> list[ScenarioReport]:
        return [report for report in self.reports if report.tier == "expanded"]

    @property
    def blocking_passed(self) -> bool:
        mainline = self.mainline_reports
        return bool(mainline) and all(report.passed for report in mainline)

    @property
    def failed_mainline(self) -> list[ScenarioReport]:
        return [report for report in self.mainline_reports if not report.passed]


def run_scenarios(scenarios: list[Scenario]) -> GateReport:
    reports = [
        ScenarioReport(slug=scenario.slug, tier=scenario.tier, checks=scenario.run())
        for scenario in scenarios
    ]
    return GateReport(reports=reports)
