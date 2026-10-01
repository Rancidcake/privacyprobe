"""Check an LLM response for factual consistency with ground-truth facts."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Callable, Optional, Union

from privacyprobe.checks.base import BaseCheck
from privacyprobe.regulations import CHECK_CLAUSES
from privacyprobe.result import TestResult

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.'][a-z0-9]+)*")

STOPWORDS = frozenset(
    """a an the and or but if then of to in on at by for with from as is are was were be
    been being it its this that these those there their they he she his her him we our you
    your i me my do does did has have had not no so than too very can will would should
    could may might must about into over under also just which who whom what when where why
    how all any each some such only own same other more most""".split()
)


def _content_tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS}


def keyword_overlap(fact: str, response: str) -> float:
    """Fraction of the fact's content words that appear in the response (0.0-1.0)."""
    fact_tokens = _content_tokens(fact)
    if not fact_tokens:
        return 1.0
    return len(fact_tokens & _content_tokens(response)) / len(fact_tokens)


class HallucinationCheck(BaseCheck):
    """Scores how well a response is supported by ground-truth facts.

    Each fact counts as *supported* when ``similarity_fn(fact, response)`` is at
    least ``fact_threshold``. The score is the fraction of supported facts, and
    the check passes when the score is at least ``threshold`` and no
    ``forbidden`` statement (a known-false claim) appears in the response.

    By default similarity is keyword overlap. Pass ``similarity_fn`` to plug in
    semantic similarity (e.g. embedding cosine similarity) without adding
    dependencies to privacyprobe itself.

    Facts and forbidden claims can be given here or per test case via the
    ``facts`` / ``forbidden`` keys; per-case values take precedence.
    """

    name = "hallucination"
    clauses = CHECK_CLAUSES["hallucination"]
    description = "Compares response against ground truth facts using keyword/semantic overlap"

    def __init__(
        self,
        facts: Optional[Union[str, Sequence[str]]] = None,
        threshold: float = 1.0,
        fact_threshold: float = 0.8,
        forbidden: Optional[Sequence[str]] = None,
        similarity_fn: Optional[Callable[[str, str], float]] = None,
    ) -> None:
        if not 0.0 <= threshold <= 1.0 or not 0.0 <= fact_threshold <= 1.0:
            raise ValueError("threshold and fact_threshold must be between 0.0 and 1.0")
        self.facts = facts
        self.threshold = threshold
        self.fact_threshold = fact_threshold
        self.forbidden = forbidden
        self.similarity_fn = similarity_fn or keyword_overlap

    @staticmethod
    def _as_list(value: Optional[Union[str, Sequence[str]]]) -> list[str]:
        if value is None:
            return []
        return [value] if isinstance(value, str) else list(value)

    def run(self, prompt: str, response: str, **kwargs: Any) -> TestResult:
        facts = self._as_list(kwargs.get("facts", self.facts))
        forbidden = self._as_list(kwargs.get("forbidden", self.forbidden))
        if not facts and not forbidden:
            raise ValueError(
                "HallucinationCheck needs ground truth: pass facts=/forbidden= to the "
                "check or add a 'facts' key to the test case"
            )

        scores = {fact: self.similarity_fn(fact, response) for fact in facts}
        unsupported = [f for f, s in scores.items() if s < self.fact_threshold]
        contradicted = [
            f for f in forbidden if self.similarity_fn(f, response) >= self.fact_threshold
        ]

        score = (len(facts) - len(unsupported)) / len(facts) if facts else 1.0
        if contradicted:
            score = 0.0
        passed = score >= self.threshold and not contradicted

        problems = []
        if unsupported:
            problems.append(f"{len(unsupported)}/{len(facts)} facts unsupported: {unsupported}")
        if contradicted:
            problems.append(f"forbidden claims present: {contradicted}")
        details = "; ".join(problems) if problems else f"All {len(facts)} facts supported"
        return self._result(
            prompt,
            response,
            passed,
            score,
            details,
            fact_scores=scores,
            unsupported=unsupported,
            contradicted=contradicted,
        )
