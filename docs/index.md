# privacyprobe documentation

`privacyprobe` is a pip-installable library for privacy compliance testing of LLM apps against
India's DPDP Act 2023 and the EU GDPR. It also covers general quality checks: hallucinations,
prompt injection, schema conformance, toxicity, latency and agent flows.

- **Install:** `pip install privacyprobe`
- **Quickstart, check catalogue and custom checks:** see the [README](https://github.com/Rancidcake/privacyprobe#readme)
- **Changes:** [CHANGELOG](https://github.com/Rancidcake/privacyprobe/blob/main/CHANGELOG.md)

## Core concepts

| Concept | Description |
|---------|-------------|
| `Suite` | Holds checks and a model target (`endpoint=` URL or `model_fn=` callable). `run(cases)` returns a `SuiteResult`. |
| Test case | A dict with `prompt`, an optional precomputed `response`, and any extra keys, which are passed to checks as keyword arguments. |
| `BaseCheck` | Abstract base class. Implement `run(prompt, response, **kwargs) -> TestResult`. |
| `TestResult` | `check_name`, `passed`, `score` (0–1), `details`, `prompt`, `response`, `metadata`. |
| `SuiteResult` | `results`, `total`, `passed`, `failed`, `pass_rate`, `failures`, `report()`, `assert_all_passed()`. |

## Per-case keyword arguments understood by built-in checks

| Key | Used by | Meaning |
|-----|---------|---------|
| `facts` | `HallucinationCheck` | Ground-truth statements the response should support |
| `forbidden` | `HallucinationCheck` | Known-false claims that must not appear |
| `system_prompt` | `PromptInjectionCheck` | The system prompt that must not leak |
| `latency` | `LatencyCheck` | Seconds; set automatically by `Suite` when it calls the model |
| `trace` | `AgentFlowCheck` | List of agent steps (strings or dicts with `state`/`step`/`name`/`action`/`tool`) |

## Reports

`result.report("html", "report.html")` writes a self-contained, escaped HTML page.
`result.report("json", "report.json")` writes the full results for dashboards or CI artifacts.

## Compliance reports

```python
result.compliance_report(regulations=["dpdp", "gdpr"], format="html")  # or "md", "json"
```

Each clause in [`privacyprobe/regulations.py`](https://github.com/Rancidcake/privacyprobe/blob/main/privacyprobe/regulations.py)
gets a status:

- **FAIL:** at least one mapped result failed, including a check that crashed
- **PASS:** every mapped result passed
- **NOT TESTED:** nothing in this run produced evidence for the clause

A check's clauses come from `CHECK_CLAUSES` (built-in checks) or its `clauses` attribute
(custom checks). `PIILeakCheck(profile="gdpr")` only claims GDPR clauses, because it only
looked for EU identifiers. Evidence is always redacted. The report is testing evidence,
not legal advice.

## Redaction

`redact(text, style="label" | "mask" | "hash", profile=..., types=..., salt=...)`.
Use `hash` with a secret `salt` for pseudonymised logs that can still be joined; unsalted
hashes of short identifiers like phone numbers can be brute-forced.
