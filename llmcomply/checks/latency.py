"""Flag responses that take longer than a threshold."""

from __future__ import annotations

from typing import Any

from llmcomply.checks.base import BaseCheck
from llmcomply.result import TestResult


class LatencyCheck(BaseCheck):
    """Fails when response time exceeds ``max_seconds``.

    :class:`~llmcomply.Suite` measures the model call and passes it as the
    ``latency`` keyword (seconds). When responses are supplied pre-computed in
    the test case, include a ``latency`` key yourself.
    """

    name = "latency"
    description = "Measures response time, flags if over threshold"

    def __init__(self, max_seconds: float = 2.0) -> None:
        if max_seconds <= 0:
            raise ValueError("max_seconds must be positive")
        self.max_seconds = max_seconds

    def run(self, prompt: str, response: str, **kwargs: Any) -> TestResult:
        latency = kwargs.get("latency")
        if latency is None:
            raise ValueError(
                "No latency measured: run via Suite with a model, or add 'latency' to the test case"
            )
        latency = float(latency)
        passed = latency <= self.max_seconds
        score = 1.0 if passed else self.max_seconds / latency
        verdict = "within" if passed else "exceeds"
        return self._result(
            prompt,
            response,
            passed,
            score,
            f"{latency:.3f}s {verdict} limit of {self.max_seconds:.3f}s",
            latency=latency,
        )

    def __repr__(self) -> str:
        return f"LatencyCheck(max_seconds={self.max_seconds})"
