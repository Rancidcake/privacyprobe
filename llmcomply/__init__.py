"""llmcomply: privacy compliance (DPDP, GDPR) and quality testing for LLM apps."""

from importlib.metadata import PackageNotFoundError, version

from llmcomply.checks import (
    AgentFlowCheck,
    BaseCheck,
    HallucinationCheck,
    LatencyCheck,
    PIILeakCheck,
    PromptInjectionCheck,
    SchemaCheck,
    ToxicityCheck,
)
from llmcomply.compliance import ComplianceReport, build_compliance_report
from llmcomply.redact import redact
from llmcomply.regulations import REGULATIONS
from llmcomply.report import generate_report
from llmcomply.result import SuiteResult, TestResult
from llmcomply.suite import Suite

try:
    __version__ = version("llmcomply")
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
