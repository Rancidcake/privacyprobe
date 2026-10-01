"""Suite: orchestrates running checks against an LLM."""

from __future__ import annotations

import time
from collections.abc import Iterable, Mapping
from typing import Any, Callable, Optional

import requests

from privacyprobe.checks.base import BaseCheck
from privacyprobe.result import SuiteResult, TestResult

ModelFn = Callable[[str], str]


class Suite:
    """Runs a set of checks over a list of test cases.

    Give it a model to query, either as a REST ``endpoint`` or as a
    ``model_fn(prompt) -> response`` callable, then add checks and call
    :meth:`run`::

        suite = Suite(model_fn=my_llm).add(PIILeakCheck()).add(ToxicityCheck())
        result = suite.run([{"prompt": "Tell me about Alice"}])

    Each test case is a dict with a ``prompt`` and optionally a precomputed
    ``response`` (then the model is not called). Every other key (``facts``,
    ``system_prompt``, ``trace``, ...) is passed to each check as a keyword
    argument. The measured call time is passed as ``latency``.

    Endpoint protocol: ``POST {request_key: prompt}`` as JSON. The response
    text is read from the JSON field ``response_key``, falling back to the raw
    body when the reply is not JSON.

    A check that raises is recorded as a failed result rather than aborting
    the run.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model_fn: Optional[ModelFn] = None,
        *,
        request_key: str = "prompt",
        response_key: str = "response",
        headers: Optional[Mapping[str, str]] = None,
        timeout: float = 30.0,
    ) -> None:
        if endpoint and model_fn:
            raise ValueError("Pass either endpoint or model_fn, not both")
        self.endpoint = endpoint
        self.model_fn = model_fn
        self.request_key = request_key
        self.response_key = response_key
        self.headers = dict(headers or {})
        self.timeout = timeout
        self.checks: list[BaseCheck] = []

    def add(self, check: BaseCheck) -> Suite:
        """Add a check. Returns self so calls can be chained."""
        if not isinstance(check, BaseCheck):
            raise TypeError(f"Expected a BaseCheck instance, got {type(check).__name__}")
        self.checks.append(check)
        return self

    def query(self, prompt: str) -> str:
        """Send one prompt to the configured model and return its response text."""
        if self.model_fn is not None:
            return str(self.model_fn(prompt))
        if self.endpoint:
            resp = requests.post(
                self.endpoint,
                json={self.request_key: prompt},
                headers=self.headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            try:
                body = resp.json()
            except ValueError:
                return resp.text
            if isinstance(body, Mapping) and self.response_key in body:
                return str(body[self.response_key])
            return resp.text
        raise ValueError(
            "No model configured: pass endpoint= or model_fn= to Suite, "
            "or include 'response' in each test case"
        )

    def run(self, test_cases: Iterable[Mapping[str, Any]]) -> SuiteResult:
        """Run every check on every test case and collect the results."""
        if not self.checks:
            raise ValueError("Suite has no checks; add some with suite.add(...)")
        results: list[TestResult] = []
        for case in test_cases:
            if "prompt" not in case:
                raise ValueError(f"Test case is missing 'prompt': {case!r}")
            prompt = str(case["prompt"])
            extra = {k: v for k, v in case.items() if k not in ("prompt", "response")}

            if "response" in case:
                response = str(case["response"])
            else:
                start = time.perf_counter()
                try:
                    response = self.query(prompt)
                except Exception as exc:  # model failure fails every check for this case
                    results += [
                        self._error(c, prompt, "", f"Model call failed: {exc!r}")
                        for c in self.checks
                    ]
                    continue
                extra.setdefault("latency", time.perf_counter() - start)

            for check in self.checks:
                try:
                    results.append(check.run(prompt, response, **extra))
                except Exception as exc:
                    results.append(self._error(check, prompt, response, f"Check error: {exc!r}"))
        return SuiteResult.from_results(results)

    @staticmethod
    def _error(check: BaseCheck, prompt: str, response: str, details: str) -> TestResult:
        return TestResult(
            check_name=check.name,
            passed=False,
            score=0.0,
            details=details,
            prompt=prompt,
            response=response,
            # Keep clauses so a crashed check counts against them, not as untested.
            metadata={"error": True, **({"clauses": check.clause_map()} if check.clauses else {})},
        )

    def __repr__(self) -> str:
        target = self.endpoint or (self.model_fn and getattr(self.model_fn, "__name__", "model_fn"))
        return f"Suite(target={target!r}, checks={self.checks!r})"
