"""Abstract base class shared by every privacyprobe check."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from privacyprobe.result import TestResult


class BaseCheck(ABC):
    """Every check inherits from this and must implement :meth:`run`.

    Subclasses set ``name`` and ``description`` as class attributes. ``run``
    receives the prompt, the model's response, and any extra fields from the
    test case (e.g. ``facts``, ``latency``) as keyword arguments. Checks must
    accept and ignore keyword arguments they do not use.

    ``clauses`` maps regulation keys to the clauses this check produces evidence
    for, e.g. ``{"gdpr": ("Art. 9",)}``. It is stamped onto every result as
    ``metadata["clauses"]`` and used by compliance reports.
    """

    name: str = "base"
    description: str = ""
    clauses: Mapping[str, tuple[str, ...]] = MappingProxyType({})

    @abstractmethod
    def run(self, prompt: str, response: str, **kwargs: Any) -> TestResult:
        """Run this check. Returns a TestResult with pass/fail + details."""

    def _result(
        self,
        prompt: str,
        response: str,
        passed: bool,
        score: float,
        details: str,
        **metadata: Any,
    ) -> TestResult:
        """Build a TestResult stamped with this check's name and clauses."""
        if self.clauses:
            metadata.setdefault("clauses", self.clause_map())
        return TestResult(
            check_name=self.name,
            passed=passed,
            score=max(0.0, min(1.0, float(score))),
            details=details,
            prompt=prompt,
            response=response,
            metadata=metadata,
        )

    def clause_map(self) -> dict[str, list[str]]:
        return {reg: list(ids) for reg, ids in self.clauses.items()}

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
