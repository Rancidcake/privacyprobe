"""Clause-by-clause DPDP / GDPR evidence reports built from a SuiteResult."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from privacyprobe.redact import redact_result
from privacyprobe.regulations import CHECK_CLAUSES, Clause, Regulation, get_regulation
from privacyprobe.report import BASE_CSS, _env, _version, write_output
from privacyprobe.result import SuiteResult, TestResult

DISCLAIMER = (
    "This report summarises automated test evidence. It is not legal advice and does not "
    "by itself establish compliance with any law. Clauses marked NOT TESTED had no "
    "automated checks in this run."
)

PASS, FAIL, NOT_TESTED = "pass", "fail", "not_tested"
_LABELS = {PASS: "PASS", FAIL: "FAIL", NOT_TESTED: "NOT TESTED"}
_EXCERPT = 300


def _excerpt(text: str) -> str:
    return text if len(text) <= _EXCERPT else text[:_EXCERPT] + "…"


@dataclass
class Evidence:
    check_name: str
    details: str
    prompt: str
    response: str

    @classmethod
    def from_result(cls, result: TestResult) -> Evidence:
        r = redact_result(result)
        return cls(r.check_name, r.details, _excerpt(r.prompt), _excerpt(r.response))


@dataclass
class ClauseStatus:
    clause: Clause
    tests: int = 0
    failed: int = 0
    checks: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def status(self) -> str:
        if not self.tests:
            return NOT_TESTED
        return FAIL if self.failed else PASS

    @property
    def label(self) -> str:
        return _LABELS[self.status]

    def to_dict(self) -> dict[str, Any]:
        return {
            "clause": self.clause.id,
            "title": self.clause.title,
            "summary": self.clause.summary,
            "status": self.status,
            "tests": self.tests,
            "failed": self.failed,
            "checks": self.checks,
            "evidence": [e.__dict__ for e in self.evidence],
        }


@dataclass
class RegulationSection:
    regulation: Regulation
    clauses: list[ClauseStatus]

    @property
    def tested(self) -> int:
        return sum(1 for c in self.clauses if c.status != NOT_TESTED)

    @property
    def failing(self) -> int:
        return sum(1 for c in self.clauses if c.status == FAIL)

    @property
    def status(self) -> str:
        if self.failing:
            return FAIL
        return PASS if self.tested else NOT_TESTED

    @property
    def label(self) -> str:
        return _LABELS[self.status]

    def to_dict(self) -> dict[str, Any]:
        r = self.regulation
        return {
            "regulation": r.key,
            "name": r.name,
            "url": r.url,
            "status": self.status,
            "clauses_tested": self.tested,
            "clauses_total": len(self.clauses),
            "clauses_failing": self.failing,
            "clauses": [c.to_dict() for c in self.clauses],
        }


@dataclass
class ComplianceReport:
    sections: list[RegulationSection]
    total_results: int
    generated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated": self.generated,
            "privacyprobe_version": _version(),
            "disclaimer": DISCLAIMER,
            "total_results": self.total_results,
            "regulations": [s.to_dict() for s in self.sections],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Markdown, e.g. for a PR comment or ``$GITHUB_STEP_SUMMARY``."""
        icon = {PASS: "✅", FAIL: "❌", NOT_TESTED: "⚪"}
        lines = [
            "# Privacy compliance evidence report",
            "",
            f"Generated {self.generated} · privacyprobe {_version()} · {self.total_results} results",
            "",
            f"> {DISCLAIMER}",
        ]
        for s in self.sections:
            lines += [
                "",
                f"## {icon[s.status]} {s.regulation.name}",
                "",
                f"{s.tested}/{len(s.clauses)} clauses tested · {s.failing} failing",
                "",
                "| Clause | Topic | Status | Tests | Failed | Checks |",
                "|--------|-------|--------|------:|-------:|--------|",
            ]
            lines += [
                f"| {c.clause.id} | {c.clause.title} | {icon[c.status]} {c.label} "
                f"| {c.tests} | {c.failed} | {', '.join(c.checks) or '-'} |"
                for c in s.clauses
            ]
            for c in s.clauses:
                if c.evidence:
                    lines += ["", f"### {c.clause.id} {c.clause.title}: failures", ""]
                    for e in c.evidence:
                        prompt = e.prompt.replace("`", "'").replace("\n", " ")
                        lines.append(f"- **{e.check_name}**: {e.details}  \n  Prompt: `{prompt}`")
        return "\n".join(lines) + "\n"

    def to_html(self) -> str:
        return _COMPLIANCE_TEMPLATE.render(
            css=BASE_CSS, report=self, disclaimer=DISCLAIMER, version=_version()
        )

    def save(self, format: str = "html", output: Optional[Union[str, Path]] = None) -> Path:
        renderers = {"html": self.to_html, "json": self.to_json, "md": self.to_markdown}
        fmt = format.lower()
        if fmt not in renderers:
            raise ValueError(f"Unsupported format {format!r}; use 'html', 'json' or 'md'")
        return write_output(renderers[fmt](), output or f"compliance.{fmt}")


def _clauses_for(result: TestResult) -> dict[str, list[str]]:
    declared = result.metadata.get("clauses")
    if declared is not None:
        return declared
    return {k: list(v) for k, v in CHECK_CLAUSES.get(result.check_name, {}).items()}


def build_compliance_report(
    result: SuiteResult,
    regulations: Union[str, Iterable[str]] = ("dpdp", "gdpr"),
    max_evidence: int = 5,
) -> ComplianceReport:
    """Group test results by the legal clauses they provide evidence for.

    A clause FAILS if any mapped result failed (including checks that errored),
    PASSES if all mapped results passed, and is NOT TESTED if nothing mapped to it.
    Evidence is redacted, so the report itself does not leak personal data.
    """
    regs = [
        get_regulation(r) for r in ([regulations] if isinstance(regulations, str) else regulations)
    ]
    sections = []
    for reg in regs:
        statuses = {c.id: ClauseStatus(c) for c in reg.clauses}
        for r in result.results:
            for clause_id in _clauses_for(r).get(reg.key, []):
                # Custom checks may cite clauses the registry doesn't list yet.
                cs = statuses.setdefault(clause_id, ClauseStatus(Clause(clause_id, clause_id, "")))
                cs.tests += 1
                if r.check_name not in cs.checks:
                    cs.checks.append(r.check_name)
                if not r.passed:
                    cs.failed += 1
                    if len(cs.evidence) < max_evidence:
                        cs.evidence.append(Evidence.from_result(r))
        sections.append(RegulationSection(reg, list(statuses.values())))
    return ComplianceReport(sections, total_results=result.total)


_COMPLIANCE_TEMPLATE = _env.from_string("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Privacy compliance report</title>
<style>
{{ css|safe }}
  .na { color: var(--muted); }
  .disclaimer { border-left: 3px solid var(--line); padding: 8px 12px; color: var(--muted); margin: 0 0 24px; }
  section { margin-bottom: 36px; }
  h2 { font-size: 18px; margin: 0 0 4px; }
  h3 { font-size: 14px; margin: 16px 0 6px; }
  .ev { border: 1px solid var(--line); border-radius: 6px; padding: 8px; margin-bottom: 8px; }
  a { color: inherit; }
</style>
</head>
<body>
<main>
  <h1>Privacy compliance evidence report</h1>
  <div class="meta">Generated {{ report.generated }} &middot; privacyprobe {{ version }} &middot; {{ report.total_results }} test results</div>
  <p class="disclaimer">{{ disclaimer }}</p>
  {% for s in report.sections %}
  <section>
    <h2><span class="{{ {'pass':'pass','fail':'fail'}.get(s.status, 'na') }}">{{ s.label }}</span> &middot; <a href="{{ s.regulation.url }}">{{ s.regulation.name }}</a></h2>
    <div class="meta">{{ s.tested }}/{{ s.clauses|length }} clauses tested &middot; {{ s.failing }} failing</div>
    <div class="wrap">
    <table>
      <colgroup><col style="width:12%"><col style="width:36%"><col style="width:12%"><col style="width:8%"><col style="width:8%"><col style="width:24%"></colgroup>
      <thead><tr><th>Clause</th><th>Requirement</th><th>Status</th><th>Tests</th><th>Failed</th><th>Checks</th></tr></thead>
      <tbody>
      {% for c in s.clauses %}
        <tr>
          <td>{{ c.clause.id }}</td>
          <td><b>{{ c.clause.title }}</b>{% if c.clause.summary %}<br><span class="na">{{ c.clause.summary }}</span>{% endif %}</td>
          <td class="{{ {'pass':'pass','fail':'fail'}.get(c.status, 'na') }}">{{ c.label }}</td>
          <td>{{ c.tests }}</td>
          <td>{{ c.failed }}</td>
          <td>{{ c.checks|join(', ') or '-' }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    </div>
    {% for c in s.clauses if c.evidence %}
      <h3>{{ c.clause.id }} {{ c.clause.title }}: failing evidence (redacted)</h3>
      {% for e in c.evidence %}
        <div class="ev">
          <b>{{ e.check_name }}</b>: {{ e.details }}
          <pre>Prompt: {{ e.prompt }}

Response: {{ e.response }}</pre>
        </div>
      {% endfor %}
    {% endfor %}
  </section>
  {% endfor %}
</main>
</body>
</html>
""")
