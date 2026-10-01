from __future__ import annotations

import json

import pytest

from privacyprobe import (
    BaseCheck,
    HallucinationCheck,
    PIILeakCheck,
    PromptInjectionCheck,
    Suite,
    ToxicityCheck,
    build_compliance_report,
)
from privacyprobe.regulations import REGULATIONS, get_regulation


def leaky_model(prompt: str) -> str:
    if "contact" in prompt:
        return "Reach Priya at priya@example.com, Aadhaar 2345 6789 0124."
    return "Paris is the capital of France."


@pytest.fixture
def result():
    return (
        Suite(model_fn=leaky_model)
        .add(PIILeakCheck())
        .add(PromptInjectionCheck())
        .add(ToxicityCheck())  # maps to no clause; must not appear
        .run([{"prompt": "capital?"}, {"prompt": "contact details?"}])
    )


def _clause(report, reg, clause_id):
    section = next(s for s in report.sections if s.regulation.key == reg)
    return next(c for c in section.clauses if c.clause.id == clause_id)


def test_registry_is_consistent():
    from privacyprobe.regulations import CHECK_CLAUSES

    for mapping in CHECK_CLAUSES.values():
        for reg, ids in mapping.items():
            for clause_id in ids:
                get_regulation(reg).clause(clause_id)  # raises if a mapping is stale
    assert set(REGULATIONS) == {"dpdp", "gdpr"}
    with pytest.raises(ValueError):
        get_regulation("hipaa")


def test_clause_statuses(result):
    report = build_compliance_report(result)
    security = _clause(report, "dpdp", "s.8(5)")
    assert security.status == "fail"
    assert security.tests == 4 and security.failed == 1  # 2 cases x (pii + injection)
    assert set(security.checks) == {"pii_leak", "prompt_injection"}
    assert _clause(report, "gdpr", "Art. 32").status == "fail"
    assert _clause(report, "dpdp", "s.9").status == "not_tested"
    assert _clause(report, "dpdp", "s.8(3)").status == "not_tested"


def test_passing_clause_and_section_status():
    res = (
        Suite(model_fn=leaky_model)
        .add(HallucinationCheck())
        .run([{"prompt": "capital?", "facts": ["Paris is the capital of France"]}])
    )
    report = build_compliance_report(res, "gdpr")
    assert [s.regulation.key for s in report.sections] == ["gdpr"]
    assert _clause(report, "gdpr", "Art. 5(1)(d)").status == "pass"
    assert report.sections[0].status == "pass"
    assert report.sections[0].tested == 1


def test_evidence_is_redacted(result):
    report = build_compliance_report(result)
    text = report.to_json() + report.to_markdown() + report.to_html()
    assert "priya@example.com" not in text and "2345 6789 0124" not in text
    assert "[EMAIL]" in text


def test_errored_check_counts_as_failure():
    res = Suite(model_fn=leaky_model).add(HallucinationCheck()).run([{"prompt": "no facts"}])
    report = build_compliance_report(res, "dpdp")
    assert _clause(report, "dpdp", "s.8(3)").status == "fail"


def test_custom_check_clauses_including_unlisted():
    class SpecialCategory(BaseCheck):
        name = "special_category"
        clauses = {"gdpr": ("Art. 9", "Art. 22")}

        def run(self, prompt, response, **kwargs):
            return self._result(prompt, response, "health" not in response, 1.0, "ok")

    res = (
        Suite(model_fn=lambda p: "your health record").add(SpecialCategory()).run([{"prompt": "x"}])
    )
    report = build_compliance_report(res, "gdpr")
    assert _clause(report, "gdpr", "Art. 9").status == "fail"
    assert _clause(report, "gdpr", "Art. 22").status == "fail"  # not in registry, still reported


def test_save_formats(tmp_path, result):
    data = json.loads(
        result.compliance_report(format="json", output=tmp_path / "c.json").read_text()
    )
    assert [r["regulation"] for r in data["regulations"]] == ["dpdp", "gdpr"]
    assert "not legal advice" in data["disclaimer"]
    md = result.compliance_report(format="md", output=tmp_path / "c.md").read_text()
    assert "| s.8(5) | Security safeguards | ❌ FAIL |" in md
    html = result.compliance_report(output=tmp_path / "c.html").read_text()
    assert html.startswith("<!doctype html>") and "NOT TESTED" in html
    with pytest.raises(ValueError):
        result.compliance_report(format="pdf", output=tmp_path / "c.pdf")


def test_default_output_name(tmp_path, monkeypatch, result):
    monkeypatch.chdir(tmp_path)
    assert result.compliance_report().name == "compliance.html"
