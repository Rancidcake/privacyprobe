# Changelog
All notable changes to `llmcomply` will be documented here.
Format: [Keep a Changelog](https://keepachangelog.com/)
Versioning: [Semantic Versioning](https://semver.org/)

## [Unreleased]

## [0.2.0] - 2026-10-01
### Changed
- **Renamed the package from `llmqa` to `llmcomply`** (`llmqa` is taken on PyPI) and
  refocused it on privacy compliance testing for DPDP and GDPR
- `PIILeakCheck` now validates Aadhaar numbers with the Verhoeff checksum and IBANs with
  mod-97, which sharply cuts false positives on random 12-digit numbers and IBAN-like strings
- When two PII types match overlapping text, it is reported once, as the more specific type
- `PromptInjectionCheck` ignores punctuation when detecting system-prompt leaks, and the
  default `leak_words` is now 6 (was 8); 7-word verbatim leaks were being missed

### Added
- Compliance reports: `SuiteResult.compliance_report()` / `build_compliance_report()` group
  results by DPDP Act section and GDPR article, with PASS / FAIL / NOT TESTED per clause,
  redacted failing evidence, and HTML, Markdown and JSON output
- `llmcomply.regulations`: a single registry of regulations, clauses and check-to-clause mappings
- `BaseCheck.clauses`, so custom checks can declare the clauses they provide evidence for
- 11 new PII types: `eu_vat`, `uk_nino`, `de_steuer_id`, `fr_nir`, `es_dni`, `es_nie`,
  `it_codice_fiscale`, `nl_bsn`, `pl_pesel` (checksum-validated where the format has one),
  `in_driving_licence`, `abha`
- `PIILeakCheck(profile="dpdp" | "gdpr")` limits detection to identifiers relevant to a law
- `PIILeakCheck.scan()` returns matches with their positions (`PIIMatch`)
- `redact()` with `label`, `mask` and salted `hash` styles
- `SuiteResult.report(..., redact=True)` strips personal data from regular reports
- `examples/compliance_report.py`

## [0.1.0] - 2026-10-01
### Added
- `Suite` class for orchestrating checks, with a fluent `add()` API, REST `endpoint` or
  `model_fn` targets, per-case keyword passthrough and automatic latency measurement
- `BaseCheck` abstract class
- `SchemaCheck` for Pydantic-based output validation (strips Markdown code fences)
- `PIILeakCheck` for 13 PII pattern types: email, phone, Aadhaar, PAN, credit card
  (Luhn-validated), SSN, IPv4, IFSC, UPI, Indian passport, GSTIN, IBAN, voter ID
- `HallucinationCheck` for factual consistency via keyword overlap, with forbidden
  claims and a pluggable `similarity_fn` for semantic similarity
- `PromptInjectionCheck` for adversarial prompt resistance (canary tokens, compliance
  phrases, system-prompt leak detection) with built-in `attack_cases()`
- `ToxicityCheck` for keyword + pattern based toxicity detection
- `LatencyCheck` for response-time thresholds
- `AgentFlowCheck` for validating multi-step agent state transitions
- `TestResult` and `SuiteResult` dataclasses, including `SuiteResult.assert_all_passed()`
  for use inside pytest
- HTML and JSON report generation via `SuiteResult.report()` (HTML output is escaped)
- FastAPI mock LLM server for local testing
- GitHub Actions CI (Python 3.9–3.11)
- GitHub Actions auto-publish on version tag, gated on the test suite

[Unreleased]: https://github.com/Rancidcake/llmcomply/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Rancidcake/llmcomply/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Rancidcake/llmcomply/releases/tag/v0.1.0
