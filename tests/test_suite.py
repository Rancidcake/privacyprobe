from __future__ import annotations

import pytest

import llmcomply
from llmcomply import (
    BaseCheck,
    LatencyCheck,
    PIILeakCheck,
    PromptInjectionCheck,
    Suite,
    SuiteResult,
    TestResult,
)


def test_public_api_exports():
    for name in llmcomply.__all__:
        assert hasattr(llmcomply, name)
    assert llmcomply.__version__


def test_fluent_add_returns_suite():
    suite = Suite(model_fn=str)
    assert suite.add(PIILeakCheck()) is suite
    assert len(suite.add(LatencyCheck()).checks) == 2


def test_add_rejects_non_check():
    with pytest.raises(TypeError):
        Suite().add("not a check")


def test_endpoint_and_model_fn_exclusive(echo_model):
    with pytest.raises(ValueError):
        Suite(endpoint="http://x", model_fn=echo_model)


def test_run_with_model_fn(echo_model):
    result = (
        Suite(model_fn=echo_model)
        .add(PIILeakCheck())
        .add(LatencyCheck(5))
        .run([{"prompt": "hello"}, {"prompt": "my ip is 10.0.0.1"}])
    )
    assert isinstance(result, SuiteResult)
    assert (result.total, result.passed, result.failed) == (4, 3, 1)
    assert result.results[0].response == "Echo: hello"
    assert result.failures[0].check_name == "pii_leak"
    assert result.pass_rate == 0.75


def test_run_with_http_endpoint(mock_endpoint):
    result = (
        Suite(endpoint=f"{mock_endpoint}/generate").add(LatencyCheck(5)).run([{"prompt": "ping"}])
    )
    assert result.all_passed
    assert result.results[0].response == "Mock response to: ping"
    assert result.results[0].metadata["latency"] >= 0


def test_endpoint_non_json_body(mock_endpoint):
    assert Suite(endpoint=f"{mock_endpoint}/plain").query("x") == "plain: x"


def test_model_failure_recorded(mock_endpoint):
    result = Suite(endpoint=f"{mock_endpoint}/error").add(PIILeakCheck()).run([{"prompt": "x"}])
    assert result.failed == 1
    assert "Model call failed" in result.results[0].details
    assert result.results[0].metadata["error"] is True


def test_precomputed_response_skips_model():
    calls = []
    suite = Suite(model_fn=lambda p: calls.append(p) or "x").add(PIILeakCheck())
    result = suite.run([{"prompt": "q", "response": "a@b.com"}])
    assert calls == [] and result.failed == 1


def test_no_model_and_no_response_fails_gracefully():
    result = Suite().add(PIILeakCheck()).run([{"prompt": "q"}])
    assert result.failed == 1 and "No model configured" in result.results[0].details


def test_extra_case_keys_passed_to_checks():
    seen = {}

    class Spy(BaseCheck):
        name = "spy"

        def run(self, prompt, response, **kwargs):
            seen.update(kwargs)
            return self._result(prompt, response, True, 1.0, "ok")

    Suite(model_fn=str).add(Spy()).run([{"prompt": "q", "facts": ["f"], "system_prompt": "s"}])
    assert seen["facts"] == ["f"] and seen["system_prompt"] == "s" and "latency" in seen


def test_check_exception_becomes_failed_result():
    class Boom(BaseCheck):
        name = "boom"

        def run(self, prompt, response, **kwargs):
            raise RuntimeError("kaboom")

    result = Suite(model_fn=str).add(Boom()).add(PIILeakCheck()).run([{"prompt": "q"}])
    assert result.total == 2 and result.failed == 1
    assert "kaboom" in result.results[0].details


def test_run_validation():
    with pytest.raises(ValueError, match="no checks"):
        Suite(model_fn=str).run([{"prompt": "q"}])
    with pytest.raises(ValueError, match="prompt"):
        Suite(model_fn=str).add(PIILeakCheck()).run([{"response": "r"}])


def test_injection_suite_end_to_end():
    check = PromptInjectionCheck()
    vulnerable = Suite(
        model_fn=lambda p: check.canary if "canary" in p.lower() or "LLMCOMPLY" in p else "no"
    )
    result = vulnerable.add(check).run(check.attack_cases())
    assert result.failed == result.total


def test_assert_all_passed():
    ok = SuiteResult.from_results([TestResult("c", True, 1.0, "", "p", "r")])
    ok.assert_all_passed()
    bad = SuiteResult.from_results([TestResult("c", False, 0.0, "broke", "p", "r")])
    with pytest.raises(AssertionError, match="broke"):
        bad.assert_all_passed()


def test_empty_suite_result():
    empty = SuiteResult.from_results([])
    assert empty.pass_rate == 0.0 and empty.all_passed
