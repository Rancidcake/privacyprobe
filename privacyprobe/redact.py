"""Redact personal data from text, e.g. before writing LLM logs or reports."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import replace
from typing import Any, Optional, Union

from privacyprobe.checks.pii_leak import PIIMatch, resolve_types, scan
from privacyprobe.result import SuiteResult, TestResult

STYLES = ("label", "mask", "hash")


def _mask(m: PIIMatch) -> str:
    if m.type == "email":
        local, _, domain = m.value.partition("@")
        return f"{local[:1]}{'*' * max(len(local) - 1, 1)}@{domain}"
    # Keep separators and the last 4 alphanumerics: "+91 98765 43210" -> "+** ***** *3210"
    keep_from = sum(c.isalnum() for c in m.value) - 4
    out, seen = [], 0
    for c in m.value:
        if c.isalnum():
            out.append(c if seen >= keep_from else "*")
            seen += 1
        else:
            out.append(c)
    return "".join(out)


def _replacement(m: PIIMatch, style: str, salt: str) -> str:
    if style == "label":
        return f"[{m.type.upper()}]"
    if style == "mask":
        return _mask(m)
    digest = hashlib.sha256((salt + m.value).encode()).hexdigest()[:10]
    return f"[{m.type.upper()}:{digest}]"


def redact(
    text: str,
    *,
    types: Optional[Iterable[str]] = None,
    profile: Optional[Union[str, Iterable[str]]] = None,
    style: str = "label",
    salt: str = "",
    allowlist: Iterable[str] = (),
) -> str:
    """Replace personal data in ``text``.

    Styles:
        ``label``: ``priya@example.com`` -> ``[EMAIL]``
        ``mask``:  ``+91 98765 43210`` -> ``+** ***** *3210`` (emails keep the domain)
        ``hash``:  ``[EMAIL:1f3a...]``, the same value always gives the same token, so
                   logs stay joinable (pseudonymisation). Pass a secret ``salt``: an
                   unsalted hash of a phone number can be brute-forced.

    ``types`` / ``profile`` select which PII types to redact (default: all).
    """
    if style not in STYLES:
        raise ValueError(f"Unknown style {style!r}; use one of {STYLES}")
    matches = scan(text, resolve_types(types, profile), allowlist)
    out, pos = [], 0
    for m in matches:
        out += [text[pos : m.start], _replacement(m, style, salt)]
        pos = m.end
    out.append(text[pos:])
    return "".join(out)


def _redact_obj(obj: Any, **kwargs: Any) -> Any:
    if isinstance(obj, str):
        return redact(obj, **kwargs)
    if isinstance(obj, dict):
        return {k: _redact_obj(v, **kwargs) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(_redact_obj(v, **kwargs) for v in obj)
    return obj


def redact_result(result: TestResult, **kwargs: Any) -> TestResult:
    """Copy of ``result`` with PII removed from prompt, response, details and metadata."""
    return replace(
        result,
        prompt=redact(result.prompt, **kwargs),
        response=redact(result.response, **kwargs),
        details=redact(result.details, **kwargs),
        metadata=_redact_obj(result.metadata, **kwargs),
    )


def redact_suite_result(result: SuiteResult, **kwargs: Any) -> SuiteResult:
    return SuiteResult.from_results([redact_result(r, **kwargs) for r in result.results])
