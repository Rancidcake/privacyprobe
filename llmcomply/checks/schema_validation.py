"""Validate that an LLM response is JSON matching a Pydantic schema."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ValidationError

from llmcomply.checks.base import BaseCheck
from llmcomply.result import TestResult

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n(.*?)\n?\s*```\s*$", re.DOTALL | re.IGNORECASE)


class SchemaCheck(BaseCheck):
    """Passes when the response parses as JSON and validates against ``schema``.

    Markdown code fences (```json ... ```) around the JSON are stripped first,
    since models add them often. Set ``strip_code_fences=False`` to disable this.
    """

    name = "schema_validation"
    description = "Validates response JSON against a Pydantic schema"

    def __init__(self, schema: type[BaseModel], strip_code_fences: bool = True) -> None:
        if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
            raise TypeError("schema must be a pydantic.BaseModel subclass")
        self.schema = schema
        self.strip_code_fences = strip_code_fences

    def run(self, prompt: str, response: str, **kwargs: Any) -> TestResult:
        payload = response
        if self.strip_code_fences:
            match = _FENCE_RE.match(response)
            if match:
                payload = match.group(1)
        try:
            self.schema.model_validate_json(payload)
        except ValidationError as exc:
            errors = exc.errors()
            summary = "; ".join(
                f"{'.'.join(str(p) for p in e['loc']) or '<root>'}: {e['msg']}" for e in errors[:5]
            )
            return self._result(
                prompt,
                response,
                False,
                0.0,
                f"Does not match {self.schema.__name__}: {summary}",
                errors=[{"loc": list(e["loc"]), "msg": e["msg"]} for e in errors],
            )
        return self._result(prompt, response, True, 1.0, f"Valid {self.schema.__name__}")

    def __repr__(self) -> str:
        return f"SchemaCheck(schema={self.schema.__name__})"
