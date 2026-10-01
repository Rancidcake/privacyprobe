from __future__ import annotations

import json

import pytest

from llmcomply import SuiteResult, TestResult, generate_report


@pytest.fixture
def suite_result():
    return SuiteResult.from_results(
        [
            TestResult("pii_leak", True, 1.0, "No PII detected", "hi", "hello"),
            TestResult(
                "toxicity",
                False,
                0.5,
                "Toxic content",
                "<b>prompt</b>",
                "<script>alert('x')</script>",
                metadata={"hits": {"insult": ["idiot"]}},
            ),
        ]
    )


def test_json_report(tmp_path, suite_result):
    path = suite_result.report("json", tmp_path / "out.json")
    data = json.loads(path.read_text())
    assert (data["total"], data["passed"], data["failed"]) == (2, 1, 1)
    assert data["pass_rate"] == 0.5
    assert data["results"][1]["metadata"]["hits"]["insult"] == ["idiot"]
    assert "llmcomply_version" in data and "generated" in data


def test_html_report(tmp_path, suite_result):
    path = suite_result.report("html", tmp_path / "out.html")
    html = path.read_text()
    assert html.startswith("<!doctype html>")
    assert "pii_leak" in html and "toxicity" in html
    assert "PASS" in html and "FAIL" in html


def test_html_report_escapes_model_output(tmp_path, suite_result):
    html = suite_result.report("html", tmp_path / "out.html").read_text()
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "<b>prompt</b>" not in html


def test_default_output_name_matches_format(tmp_path, monkeypatch, suite_result):
    monkeypatch.chdir(tmp_path)
    assert suite_result.report().name == "report.html"
    assert suite_result.report("json").name == "report.json"
    assert (tmp_path / "report.json").exists()


def test_creates_parent_dirs(tmp_path, suite_result):
    path = generate_report(suite_result, "json", tmp_path / "nested" / "dir" / "r.json")
    assert path.exists()


def test_unknown_format(tmp_path, suite_result):
    with pytest.raises(ValueError):
        suite_result.report("pdf", tmp_path / "r.pdf")
