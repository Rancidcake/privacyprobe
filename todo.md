# llmqa — Build TODO for Claude Code
> PyPI-publishable Python library for AI/LLM quality assurance testing.
> Every decision here is intentional and auditable. Rationale is included inline.

---

## 0. Project Philosophy
- This is a **pip-installable library**, not a script collection.
- Every public function/class must be importable from `llmqa` directly.
- Zero unnecessary dependencies — keep install footprint small.
- Tests must pass in CI before any publish.
- Changelog must be updated on every meaningful change.

---

## 1. Repository Structure

```
llmqa/
├── llmqa/                  # The actual library (importable package)
│   ├── __init__.py         # Public API surface — export everything the user needs here
│   ├── suite.py            # Suite class — orchestrates checks and runs them
│   ├── result.py           # TestResult and SuiteResult dataclasses
│   ├── report.py           # HTML + JSON report generation
│   └── checks/             # All individual check modules live here
│       ├── __init__.py     # Re-exports all checks for `from llmqa.checks import X`
│       ├── base.py         # BaseCheck abstract class — every check inherits this
│       ├── hallucination.py
│       ├── pii_leak.py
│       ├── prompt_injection.py
│       ├── responsible_ai.py
│       ├── schema_validation.py
│       ├── latency.py
│       └── agent_flow.py
├── tests/                  # pytest test suite for the library itself (meta)
│   ├── conftest.py         # Shared fixtures (mock LLM endpoint, sample responses)
│   ├── test_suite.py
│   ├── test_checks.py
│   └── test_report.py
├── examples/               # Runnable usage examples — important for README credibility
│   ├── basic_usage.py
│   └── agent_pipeline_check.py
├── .github/
│   └── workflows/
│       ├── ci.yml          # Runs tests on every push/PR
│       └── publish.yml     # Auto-publishes to PyPI on git tag (v*)
├── docs/                   # Optional but good — GitHub Pages / ReadTheDocs
│   └── index.md
├── pyproject.toml          # Single source of truth for packaging (PEP 517/518)
├── CHANGELOG.md            # Required for audit — every version's changes logged here
├── LICENSE                 # MIT (most permissive, maximises adoption)
├── README.md               # Must include: install, quickstart, check list, badge
└── todo.md                 # This file
```

**Why this structure?**
- `llmqa/` as the inner package is standard PyPI convention
- `checks/` as a subpackage keeps concerns separated and makes the library extensible
- `tests/` at root is pytest convention, not inside the package (don't ship tests to users)
- `examples/` gives real runnable code for README and documentation
- `.github/workflows/` enables zero-touch CI/CD — test on push, publish on tag

---

## 2. pyproject.toml (Packaging Config)

**Why pyproject.toml, not setup.py?**
`setup.py` is legacy. `pyproject.toml` is PEP 517/518 compliant, the current standard, and what PyPI expects from modern packages.

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "llmqa"
version = "0.1.0"
description = "A Python library for AI/LLM output quality assurance and responsible AI testing"
readme = "README.md"
license = { file = "LICENSE" }
authors = [{ name = "Mayank Hete", email = "mayankrajeshhete@gmail.com" }]
requires-python = ">=3.9"
keywords = ["llm", "testing", "ai", "quality-assurance", "responsible-ai", "genai"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Testing",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
]

dependencies = [
    "requests>=2.28",        # HTTP calls to LLM endpoints
    "pydantic>=2.0",         # Schema validation for LLM output
    "jinja2>=3.1",           # HTML report templating
    "pytest>=7.0",           # Test runner integration
]

[project.optional-dependencies]
dev = [
    "pytest-cov",            # Coverage reporting
    "pytest-html",           # HTML test output
    "httpx",                 # For async endpoint testing
    "black",                 # Formatter
    "ruff",                  # Linter
    "twine",                 # PyPI upload tool
    "build",                 # Package builder
]

[project.urls]
Homepage = "https://github.com/mayank-hete/llmqa"
Repository = "https://github.com/mayank-hete/llmqa"
Issues = "https://github.com/mayank-hete/llmqa"
```

---

## 3. Core Classes to Build

### 3a. `BaseCheck` (checks/base.py)
```python
# WHY: Abstract base class ensures every check has a consistent interface.
# Any new check added later MUST implement run() — enforced by ABC.
from abc import ABC, abstractmethod
from llmqa.result import TestResult

class BaseCheck(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, prompt: str, response: str, **kwargs) -> TestResult:
        """Run this check. Returns a TestResult with pass/fail + details."""
        ...
```

### 3b. `Suite` (suite.py)
```python
# WHY: Suite is the orchestrator. Users add checks, give it an endpoint,
# and call .run(). Separates check logic from orchestration.
class Suite:
    def __init__(self, endpoint: str = None, model_fn: callable = None):
        # endpoint: REST API URL of LLM (e.g. FastAPI mock or OpenAI)
        # model_fn: alternatively pass a callable directly (for local models)
        ...

    def add(self, check: BaseCheck) -> "Suite":
        # Fluent API: suite.add(X).add(Y).run(cases)
        ...

    def run(self, test_cases: list[dict]) -> SuiteResult:
        # Iterates test_cases, calls each check, collects TestResults
        ...
```

### 3c. `TestResult` and `SuiteResult` (result.py)
```python
# WHY: Dataclasses keep results structured and serializable to JSON.
@dataclass
class TestResult:
    check_name: str
    passed: bool
    score: float          # 0.0 to 1.0
    details: str
    prompt: str
    response: str

@dataclass
class SuiteResult:
    results: list[TestResult]
    total: int
    passed: int
    failed: int

    def report(self, format: str = "html", output: str = "report.html"):
        # Generates output — delegates to report.py
        ...
```

---

## 4. Checks to Implement (Priority Order)

### ✅ Priority 1 — Core checks (v0.1.0)

| File | Check | What it does | Why it matters |
|------|-------|-------------|----------------|
| `schema_validation.py` | `SchemaCheck` | Validates response JSON against a Pydantic schema | Most common LLM output requirement |
| `pii_leak.py` | `PIILeakCheck` | Regex + pattern match for 13 PII types (email, phone, Aadhaar, PAN, etc.) | Directly from Argus project experience |
| `hallucination.py` | `HallucinationCheck` | Compares response against ground truth facts using keyword/semantic overlap | Core responsible AI concern |
| `prompt_injection.py` | `PromptInjectionCheck` | Tests if adversarial prompts hijack model behaviour | Security-critical for production LLMs |

### ⏳ Priority 2 — Extended checks (v0.2.0)

| File | Check | What it does |
|------|-------|-------------|
| `responsible_ai.py` | `ToxicityCheck` | Keyword + pattern based toxicity detection |
| `latency.py` | `LatencyCheck` | Measures response time, flags if over threshold |
| `agent_flow.py` | `AgentFlowCheck` | Validates multi-step agent pipeline state transitions |

---

## 5. Mock LLM Server (for tests and examples)

**File:** `examples/mock_server.py`

```python
# WHY: Users need something to test against out of the box.
# A FastAPI mock endpoint lets the library's own tests be self-contained
# and gives examples that actually run without needing OpenAI keys.
from fastapi import FastAPI
app = FastAPI()

@app.post("/generate")
def generate(prompt: str):
    return {"response": f"Mock response to: {prompt}"}
```

Run with: `uvicorn examples.mock_server:app --reload`

Add `fastapi` and `uvicorn` to dev dependencies only.

---

## 6. CI/CD Workflows

### `.github/workflows/ci.yml`
```yaml
# WHY: Tests must run on every push so regressions are caught before merge.
# Runs on Python 3.9, 3.10, 3.11 to ensure compatibility.
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest --cov=llmqa --cov-report=xml
```

### `.github/workflows/publish.yml`
```yaml
# WHY: Automates PyPI publish on git tag push (v0.1.0, v1.0.0 etc.)
# No manual twine uploads — tag the release, CI does the rest.
# Uses PyPI Trusted Publisher (OIDC) — no API key stored in secrets.
name: Publish to PyPI
on:
  push:
    tags: ["v*"]
jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

---

## 7. CHANGELOG.md Format

**WHY:** Changelog is required for any serious open source library. Employers,
contributors, and users check it. Use Keep a Changelog format.

```markdown
# Changelog
All notable changes to `llmqa` will be documented here.
Format: [Keep a Changelog](https://keepachangelog.com/)
Versioning: [Semantic Versioning](https://semver.org/)

## [Unreleased]

## [0.1.0] - 2026-10-01
### Added
- `Suite` class for orchestrating checks
- `BaseCheck` abstract class
- `SchemaCheck` for Pydantic-based output validation
- `PIILeakCheck` for 13 PII pattern types
- `HallucinationCheck` for factual consistency
- `PromptInjectionCheck` for adversarial prompt resistance
- HTML and JSON report generation via `SuiteResult.report()`
- FastAPI mock LLM server for local testing
- GitHub Actions CI (Python 3.9–3.11)
- GitHub Actions auto-publish on version tag
```

---

## 8. README.md Must Include

- [ ] PyPI badge: `![PyPI](https://img.shields.io/pypi/v/llmqa)`
- [ ] CI badge from GitHub Actions
- [ ] One-line description
- [ ] `pip install llmqa`
- [ ] Quickstart code block (copy-paste runnable)
- [ ] Full check catalogue table
- [ ] How to add a custom check (extensibility story)
- [ ] Link to examples/
- [ ] Author credit: Mayank Hete

---

## 9. PyPI Publish Steps (First Time)

1. Register at https://pypi.org — create account
2. Enable 2FA on PyPI (now required)
3. Go to PyPI → Account Settings → Publishing → Add GitHub repo as Trusted Publisher
   - No API key needed — uses OIDC token from GitHub Actions
4. Push first tag: `git tag v0.1.0 && git push origin v0.1.0`
5. GitHub Action triggers, builds, and uploads automatically
6. Verify: `pip install llmqa` in a fresh venv

---

## 10. Build Order for Claude Code

**Do these in sequence:**

- [ ] 1. Create repo structure (all files/folders)
- [ ] 2. Write `pyproject.toml`
- [ ] 3. Write `checks/base.py` (BaseCheck)
- [ ] 4. Write `result.py` (TestResult, SuiteResult)
- [ ] 5. Write `checks/schema_validation.py`
- [ ] 6. Write `checks/pii_leak.py`
- [ ] 7. Write `checks/hallucination.py`
- [ ] 8. Write `checks/prompt_injection.py`
- [ ] 9. Write `checks/__init__.py` (re-export all checks)
- [ ] 10. Write `suite.py`
- [ ] 11. Write `report.py` (HTML + JSON output)
- [ ] 12. Write `llmqa/__init__.py` (public API surface)
- [ ] 13. Write `examples/mock_server.py`
- [ ] 14. Write `examples/basic_usage.py`
- [ ] 15. Write `tests/conftest.py`
- [ ] 16. Write `tests/test_suite.py`
- [ ] 17. Write `tests/test_checks.py`
- [ ] 18. Write `tests/test_report.py`
- [ ] 19. Write `.github/workflows/ci.yml`
- [ ] 20. Write `.github/workflows/publish.yml`
- [ ] 21. Write `CHANGELOG.md`
- [ ] 22. Write `LICENSE` (MIT)
- [ ] 23. Write `README.md`
- [ ] 24. Run `pytest` — all tests must pass
- [ ] 25. Run `python -m build` — verify package builds cleanly
- [ ] 26. Push to GitHub, tag `v0.1.0`, verify PyPI publish action triggers