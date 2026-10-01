"""Structured, JSON-serializable results for checks and suites."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional, Union


@dataclass
class TestResult:
    """Outcome of one check against one prompt/response pair."""

    __test__ = False  # stop pytest from trying to collect this class

    check_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    details: str
    prompt: str
    response: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SuiteResult:
    """Aggregate of every TestResult produced by a Suite run."""

    __test__ = False

    results: list[TestResult]
    total: int
    passed: int
    failed: int

    @classmethod
    def from_results(cls, results: list[TestResult]) -> SuiteResult:
        passed = sum(1 for r in results if r.passed)
        return cls(results=results, total=len(results), passed=passed, failed=len(results) - passed)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def all_passed(self) -> bool:
        return self.failed == 0

    @property
    def failures(self) -> list[TestResult]:
        return [r for r in self.results if not r.passed]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "results": [r.to_dict() for r in self.results],
        }

    def summary(self) -> str:
        return f"{self.passed}/{self.total} checks passed ({self.pass_rate:.0%})"

    def assert_all_passed(self) -> None:
        """Raise AssertionError listing every failure. Handy inside pytest tests."""
        if self.failed:
            lines = [f"[{r.check_name}] {r.prompt[:60]!r}: {r.details}" for r in self.failures]
            raise AssertionError(f"{self.summary()}\n" + "\n".join(lines))

    def report(
        self,
        format: str = "html",
        output: Optional[Union[str, Path]] = None,
        redact: bool = False,
    ) -> Path:
        """Write an HTML or JSON report and return its path.

        ``output`` defaults to ``report.html`` or ``report.json`` to match ``format``.
        ``redact=True`` strips personal data from the report.
        """
        from llmcomply.report import generate_report

        return generate_report(self, format=format, output=output, redact=redact)

    def compliance_report(
        self,
        regulations: Union[str, Iterable[str]] = ("dpdp", "gdpr"),
        format: str = "html",
        output: Optional[Union[str, Path]] = None,
    ) -> Path:
        """Write a clause-by-clause DPDP / GDPR evidence report and return its path.

        ``format`` is ``html``, ``json`` or ``md``. Personal data is always redacted.
        """
        from llmcomply.compliance import build_compliance_report

        return build_compliance_report(self, regulations).save(format, output)
