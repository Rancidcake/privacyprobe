"""Validate state transitions in a multi-step agent pipeline."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any, Optional

from llmcomply.checks.base import BaseCheck
from llmcomply.result import TestResult

_STATE_KEYS = ("state", "step", "name", "action", "tool")


def _state_of(step: Any) -> str:
    if isinstance(step, str):
        return step
    if isinstance(step, Mapping):
        for key in _STATE_KEYS:
            if key in step:
                return str(step[key])
    raise ValueError(f"Cannot determine state of trace step: {step!r}")


class AgentFlowCheck(BaseCheck):
    """Checks that an agent's trace follows an allowed state machine.

    The trace is a list of steps, each a state name or a dict with one of the
    keys ``state``/``step``/``name``/``action``/``tool``. It is read from the
    ``trace`` keyword (per test case) or, if absent, parsed from the response
    as a JSON list (or an object with a ``trace``/``steps`` list).

    Args:
        transitions: ``{state: [allowed next states]}``.
        start: Required first state.
        terminal: States the trace is allowed to end on.
        required: States that must appear somewhere in the trace.
        max_steps: Fail traces longer than this (catches loops).
    """

    name = "agent_flow"
    description = "Validates multi-step agent pipeline state transitions"

    def __init__(
        self,
        transitions: Mapping[str, Iterable[str]],
        start: Optional[str] = None,
        terminal: Optional[Iterable[str]] = None,
        required: Optional[Iterable[str]] = None,
        max_steps: Optional[int] = None,
    ) -> None:
        self.transitions = {k: set(v) for k, v in transitions.items()}
        self.start = start
        self.terminal = set(terminal) if terminal is not None else None
        self.required = list(required or ())
        self.max_steps = max_steps

    def _load_trace(self, response: str, kwargs: dict[str, Any]) -> list[str]:
        trace = kwargs.get("trace")
        if trace is None:
            try:
                trace = json.loads(response)
            except json.JSONDecodeError as exc:
                raise ValueError("No 'trace' given and response is not a JSON trace") from exc
            if isinstance(trace, Mapping):
                trace = trace.get("trace", trace.get("steps"))
        if not isinstance(trace, list):
            raise ValueError("Agent trace must be a list of steps")
        return [_state_of(s) for s in trace]

    def run(self, prompt: str, response: str, **kwargs: Any) -> TestResult:
        states = self._load_trace(response, kwargs)
        errors: list[str] = []
        if not states:
            errors.append("empty trace")
        if self.start is not None and states and states[0] != self.start:
            errors.append(f"starts at {states[0]!r}, expected {self.start!r}")

        pairs = list(zip(states, states[1:]))
        bad = [(a, b) for a, b in pairs if b not in self.transitions.get(a, ())]
        errors += [f"illegal transition {a!r} -> {b!r}" for a, b in bad]

        if self.terminal is not None and states and states[-1] not in self.terminal:
            errors.append(f"ends at non-terminal state {states[-1]!r}")
        missing = [s for s in self.required if s not in states]
        if missing:
            errors.append(f"required states never reached: {missing}")
        if self.max_steps is not None and len(states) > self.max_steps:
            errors.append(f"{len(states)} steps exceeds max_steps={self.max_steps}")

        score = (len(pairs) - len(bad)) / len(pairs) if pairs else (1.0 if states else 0.0)
        if errors:
            return self._result(
                prompt, response, False, score, "; ".join(errors), trace=states, errors=errors
            )
        return self._result(
            prompt, response, True, 1.0, f"Valid flow: {' -> '.join(states)}", trace=states
        )
