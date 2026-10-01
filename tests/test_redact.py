from __future__ import annotations

import pytest

from privacyprobe import SuiteResult, TestResult, redact
from privacyprobe.redact import redact_result

TEXT = "Mail priya@example.com or call +91 98765 43210. Aadhaar 2345 6789 0124."


def test_label_style():
    assert redact(TEXT) == "Mail [EMAIL] or call [PHONE]. Aadhaar [AADHAAR]."


def test_mask_style():
    out = redact(TEXT, style="mask")
    assert "p****@example.com" in out
    assert "+** ***** *3210" in out
    assert "**** **** 0124" in out


def test_hash_style_is_stable_and_salted():
    a = redact("a@b.com", style="hash")
    assert a == redact("x a@b.com", style="hash")[2:]
    assert a.startswith("[EMAIL:") and a != redact("a@b.com", style="hash", salt="s3cret")


def test_profile_and_allowlist():
    assert "[AADHAAR]" not in redact(TEXT, profile="gdpr")
    assert "priya@example.com" in redact(TEXT, allowlist=["priya@example.com"])


def test_no_pii_unchanged():
    assert redact("nothing to see") == "nothing to see"


def test_bad_style():
    with pytest.raises(ValueError):
        redact(TEXT, style="blur")


def test_redact_result_covers_metadata():
    r = TestResult(
        "pii_leak",
        False,
        0.0,
        "found a@b.com",
        "p a@b.com",
        "r a@b.com",
        metadata={"findings": {"email": ["a@b.com"]}},
    )
    out = redact_result(r)
    assert "a@b.com" not in repr(out)
    assert out.metadata["findings"] == {"email": ["[EMAIL]"]}
    assert r.response == "r a@b.com"  # original untouched


def test_report_redact_flag(tmp_path):
    result = SuiteResult.from_results(
        [
            TestResult(
                "pii_leak",
                False,
                0.0,
                "x",
                "p",
                "call +91 98765 43210",
                metadata={"findings": {"phone": ["+91 98765 43210"]}},
            )
        ]
    )
    for fmt in ("html", "json"):
        assert "98765" in result.report(fmt, tmp_path / f"raw.{fmt}").read_text()
        assert "98765" not in result.report(fmt, tmp_path / f"safe.{fmt}", redact=True).read_text()
