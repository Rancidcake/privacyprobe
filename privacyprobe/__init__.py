"""privacyprobe: privacy compliance (DPDP, GDPR) and quality testing for LLM apps."""

from importlib.metadata import PackageNotFoundError, version

from privacyprobe.checks import (
    AgentFlowCheck,
    BaseCheck,
    HallucinationCheck,
    LatencyCheck,
    PIILeakCheck,
    PromptInjectionCheck,
    SchemaCheck,
    ToxicityCheck,
)
from privacyprobe.compliance import ComplianceReport, build_compliance_report
from privacyprobe.redact import redact
from privacyprobe.regulations import REGULATIONS
from privacyprobe.report import generate_report
from privacyprobe.result import SuiteResult, TestResult
from privacyprobe.suite import Suite

try:
    __version__ = version("privacyprobe")
except PackageNotFoundError:  # running from a source checkout without install
    __version__ = "0.0.0+unknown"

__all__ = [
    "REGULATIONS",
    "AgentFlowCheck",
    "BaseCheck",
    "ComplianceReport",
    "HallucinationCheck",
    "LatencyCheck",
    "PIILeakCheck",
    "PromptInjectionCheck",
    "SchemaCheck",
    "Suite",
    "SuiteResult",
    "TestResult",
    "ToxicityCheck",
    "__version__",
    "build_compliance_report",
    "generate_report",
    "redact",
]
