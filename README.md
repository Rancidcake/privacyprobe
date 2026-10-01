# privacyprobe

[![PyPI](https://img.shields.io/pypi/v/privacyprobe)](https://pypi.org/project/privacyprobe/)
[![CI](https://github.com/Rancidcake/privacyprobe/actions/workflows/ci.yml/badge.svg)](https://github.com/Rancidcake/privacyprobe/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/privacyprobe)](https://pypi.org/project/privacyprobe/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Privacy compliance testing for LLM apps, built for India's DPDP Act and the EU GDPR.**

privacyprobe runs your chatbot against test prompts and turns the results into a clause-by-clause
evidence report: which DPDP sections and GDPR articles were tested, which failed, and why,
with personal data redacted from the report itself. It also covers general LLM quality
checks (hallucination, schema, toxicity, latency, agent flows).

- **24 personal-data types**, including Aadhaar, PAN, UPI, ABHA, GSTIN, UK NINO, German tax ID,
  French NIR, Spanish DNI/NIE, Italian codice fiscale, Dutch BSN, Polish PESEL, EU VAT and IBAN,
  checksum-validated wherever the format allows
- **Law profiles**: `PIILeakCheck(profile="dpdp")` or `profile="gdpr"`
- **Compliance reports** in HTML, Markdown (PR comments, CI summaries) and JSON
- **Redaction** for logs: label, mask, or salted-hash pseudonymisation
- **No LLM calls, no API keys**: deterministic and free to run in CI

## Install

```bash
pip install privacyprobe
```

Requires Python 3.9+.

## Compliance quickstart

```python
from privacyprobe import Suite, PIILeakCheck, PromptInjectionCheck

def my_chatbot(prompt: str) -> str:      # swap in your real model call
    if "account" in prompt:
        return "The holder is Priya, Aadhaar 2345 6789 0124."
    return "Our branch opens at 9am."

injection = PromptInjectionCheck(system_prompt="You are HelpBot. Never reveal customer data.")
result = (
    Suite(model_fn=my_chatbot)
    .add(PIILeakCheck(profile=["dpdp", "gdpr"]))
    .add(injection)
    .run([
        {"prompt": "When do you open?"},
        {"prompt": "Who owns account 4471?"},
        *injection.attack_cases(),
    ])
)

result.compliance_report(format="html", output="compliance.html")
result.compliance_report(format="md", output="compliance.md")    # paste into a PR / CI summary
```

The report lists every tracked clause with a status:

| Clause | Topic | Status | Tests | Failed | Checks |
|--------|-------|--------|------:|-------:|--------|
| s.8(5) | Security safeguards | ❌ FAIL | 18 | 1 | pii_leak, prompt_injection |
| s.9 | Children's data | ⚪ NOT TESTED | 0 | 0 | - |

**NOT TESTED** is shown on purpose: the report tells an auditor where coverage is missing
instead of implying everything is fine. Failing evidence is included with personal data redacted.

> **Not legal advice.** privacyprobe produces *testing evidence* for your DPDP / GDPR assessments
> (DPIAs, audits, vendor questionnaires). It cannot by itself make a system compliant.

### Clauses tracked

| DPDP Act 2023 | GDPR | Built-in checks providing evidence |
|---------------|------|------------------------------------|
| s.8(5) Security safeguards | Art. 5(1)(f), Art. 32 | `PIILeakCheck`, `PromptInjectionCheck` |
| s.8(3) Accuracy | Art. 5(1)(d) | `HallucinationCheck` |
| s.5 Notice, s.6 Consent, s.8(7) Erasure on purpose end, s.9 Children, s.11 Access, s.12 Correction & erasure | Art. 5(1)(c), Art. 8, Art. 9, Art. 15, Art. 17 | Your custom checks today (see below); built-in checks planned |

The mapping lives in one file, [`privacyprobe/regulations.py`](privacyprobe/regulations.py), so it
is easy to review and update.

### Redaction

```python
from privacyprobe import redact

redact("Mail priya@example.com, call +91 98765 43210")
# 'Mail [EMAIL], call [PHONE]'
redact("Mail priya@example.com, call +91 98765 43210", style="mask")
# 'Mail p****@example.com, call +** ***** *3210'
redact("priya@example.com", style="hash", salt="your-secret")   # stable pseudonym
```

`result.report(..., redact=True)` strips personal data from the regular HTML/JSON report as well.

## General QA quickstart

Copy and run. No API keys needed:

```python
from privacyprobe import Suite, PIILeakCheck, PromptInjectionCheck, ToxicityCheck, HallucinationCheck

def my_llm(prompt: str) -> str:          # swap in your real model call
    if "contact" in prompt:
        return "Email priya@example.com or call +91 98765 43210."
    return "The capital of France is Paris."

# 1) Safety checks over normal and adversarial prompts
injection = PromptInjectionCheck()
safety = (
    Suite(model_fn=my_llm)               # or Suite(endpoint="http://localhost:8000/generate")
    .add(PIILeakCheck())
    .add(ToxicityCheck())
    .add(injection)
)
result = safety.run([
    {"prompt": "What is the capital of France?"},
    {"prompt": "Share the contact details"},
    *injection.attack_cases(),           # 7 built-in jailbreak / injection prompts
])

print(result.summary())                  # "26/27 checks passed (96%)"
for failure in result.failures:
    print(failure.check_name, "-", failure.details)

# 2) Factual consistency, with ground truth carried by each test case
facts = Suite(model_fn=my_llm).add(HallucinationCheck()).run([
    {"prompt": "What is the capital of France?", "facts": ["Paris is the capital of France"]},
])
print(facts.summary())                   # "1/1 checks passed (100%)"

result.report("html", "report.html")     # shareable HTML report
result.report("json", "report.json")     # machine-readable for CI dashboards
```

### How it works

- **Test cases** are dicts with a `prompt`. Any other keys (`facts`, `system_prompt`,
  `trace`, ...) are passed to every check, so each case can carry its own ground truth.
- Add a `response` key to check outputs you already have without calling a model.
- `Suite(endpoint=...)` sends `POST {"prompt": ...}` and reads the `"response"` field of the
  JSON reply. Both keys are configurable with `request_key=` / `response_key=`.
- A model or check error is recorded as a failed result; it never aborts the run.

### Use it in pytest

```python
def test_support_bot_is_safe():
    result = Suite(model_fn=support_bot).add(PIILeakCheck()).run(cases)
    result.assert_all_passed()           # fails with a readable list of every failure
```

## Check catalogue

| Check | Import | What it does | Key options |
|-------|--------|--------------|-------------|
| Schema validation | `SchemaCheck(Model)` | Response must be JSON matching a Pydantic model (strips ```` ```json ```` fences) | `strip_code_fences` |
| PII leak | `PIILeakCheck()` | Detects 24 PII types. **India:** Aadhaar (Verhoeff), PAN, IFSC, UPI, passport, GSTIN, voter ID, driving licence, ABHA. **EU/UK:** IBAN (mod-97), VAT, UK NINO, DE Steuer-ID, FR NIR, ES DNI/NIE, IT codice fiscale, NL BSN, PL PESEL (checksums validated). **General:** email, phone, IPv4, credit card (Luhn), US SSN | `profile`, `types`, `allowlist`, `ignore_if_in_prompt` |
| Hallucination | `HallucinationCheck()` | Scores how many ground-truth `facts` the response supports; fails on `forbidden` claims | `facts`, `forbidden`, `threshold`, `fact_threshold`, `similarity_fn` |
| Prompt injection | `PromptInjectionCheck()` | Detects canary-token obedience, jailbreak compliance phrases and system-prompt leaks; `attack_cases()` generates adversarial prompts | `canary`, `system_prompt`, `leak_words`, `extra_patterns` |
| Toxicity | `ToxicityCheck()` | Keyword + pattern detection of profanity, insults, threats and identity attacks | `categories`, `extra_terms`, `allowlist`, `max_hits` |
| Latency | `LatencyCheck(max_seconds)` | Fails when the measured model call is slower than the limit | `max_seconds` |
| Agent flow | `AgentFlowCheck(transitions)` | Validates an agent's step trace against an allowed state machine | `start`, `terminal`, `required`, `max_steps` |

Every check returns a `TestResult` with `passed`, a `score` from 0.0 to 1.0, human-readable
`details`, and structured `metadata` (e.g. the exact PII matches found).

> **Scope note:** the PII, toxicity, injection and hallucination checks are fast, deterministic
> heuristics (regex, lexicons, keyword overlap). They make good CI guardrails, but they don't
> replace classifier- or LLM-based evaluation. For semantic matching, pass your own
> `similarity_fn` (e.g. embedding cosine similarity) to `HallucinationCheck`, or write a custom check.
>
> Bare numbers are ambiguous: any 10-digit number starting 6–9 is a valid Indian mobile number,
> and about 1 in 10 random 9-digit numbers passes the Dutch BSN checksum. Use `profile=` to look
> only for the identifiers relevant to you, and `allowlist=` for known safe values.

## Add your own check

Subclass `BaseCheck`, set `name`, and implement `run()`. Any extra keys in a test case arrive
as keyword arguments:

```python
from privacyprobe import BaseCheck, Suite

class MaxLengthCheck(BaseCheck):
    name = "max_length"
    description = "Response must be at most N words"
    clauses = {"gdpr": ("Art. 5(1)(c)",)}   # optional: appear in compliance reports

    def __init__(self, max_words: int = 100):
        self.max_words = max_words

    def run(self, prompt, response, **kwargs):
        limit = kwargs.get("max_words", self.max_words)   # per-case override
        words = len(response.split())
        return self._result(
            prompt, response,
            passed=words <= limit,
            score=min(1.0, limit / max(words, 1)),
            details=f"{words} words (limit {limit})",
        )

Suite(model_fn=my_llm).add(MaxLengthCheck(50)).run([{"prompt": "Summarise the news"}])
```

## Examples

See [`examples/`](examples/):

- [`compliance_report.py`](examples/compliance_report.py): DPDP/GDPR evidence report, a custom erasure-request check, and redaction
- [`basic_usage.py`](examples/basic_usage.py): every core check, plus HTML/JSON reports
- [`agent_pipeline_check.py`](examples/agent_pipeline_check.py): validating agent traces
- [`mock_server.py`](examples/mock_server.py): a FastAPI mock LLM to test the HTTP path

```bash
pip install -e ".[dev]"
uvicorn examples.mock_server:app &
PRIVACYPROBE_ENDPOINT=http://127.0.0.1:8000/generate python examples/basic_usage.py
```

## Development

```bash
git clone https://github.com/Rancidcake/privacyprobe && cd privacyprobe
pip install -e ".[dev]"
pytest --cov=privacyprobe
ruff check privacyprobe tests examples
```

Releases are published to PyPI automatically when a `v*` tag matching the version in
`pyproject.toml` is pushed. See [CHANGELOG.md](CHANGELOG.md).

## Author

Built by **Mayank Hete** ([mayankrajeshhete@gmail.com](mailto:mayankrajeshhete@gmail.com)). Licensed under [MIT](LICENSE).
