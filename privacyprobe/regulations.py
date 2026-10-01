"""Regulation and clause registry: the single place that maps checks to law.

When a law or its interpretation changes, update this file only. Clause
references are kept short and stable (section / article numbers); the
summaries are plain-language paraphrases, not legal text.

This module deliberately imports nothing from privacyprobe so any module can use it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Clause:
    id: str
    title: str
    summary: str


@dataclass(frozen=True)
class Regulation:
    key: str
    name: str
    short_name: str
    url: str
    clauses: tuple[Clause, ...]

    def clause(self, clause_id: str) -> Clause:
        for c in self.clauses:
            if c.id == clause_id:
                return c
        raise KeyError(f"{self.short_name} has no clause {clause_id!r}")


DPDP = Regulation(
    key="dpdp",
    name="Digital Personal Data Protection Act, 2023 (India)",
    short_name="DPDP Act",
    url="https://www.meity.gov.in/data-protection-framework",
    clauses=(
        Clause("s.5", "Notice", "Data Principals must be told what data is collected and why."),
        Clause("s.6", "Consent", "Consent must be free, specific, informed and unambiguous."),
        Clause(
            "s.8(3)",
            "Accuracy",
            "Personal data used for decisions or shared onward must be complete, "
            "accurate and consistent.",
        ),
        Clause(
            "s.8(5)",
            "Security safeguards",
            "Reasonable security safeguards must prevent personal data breaches.",
        ),
        Clause("s.8(7)", "Erasure on purpose end", "Data must be erased once its purpose ends."),
        Clause(
            "s.9",
            "Children's data",
            "Verifiable parental consent; no tracking, behavioural monitoring or targeted "
            "advertising directed at children.",
        ),
        Clause("s.11", "Right to access", "Data Principals can obtain a summary of their data."),
        Clause("s.12", "Correction and erasure", "Data Principals can correct or erase data."),
    ),
)

GDPR = Regulation(
    key="gdpr",
    name="General Data Protection Regulation (EU) 2016/679",
    short_name="GDPR",
    url="https://eur-lex.europa.eu/eli/reg/2016/679/oj",
    clauses=(
        Clause(
            "Art. 5(1)(c)",
            "Data minimisation",
            "Collect only data that is adequate, relevant and necessary.",
        ),
        Clause("Art. 5(1)(d)", "Accuracy", "Personal data must be accurate and kept up to date."),
        Clause(
            "Art. 5(1)(f)",
            "Integrity and confidentiality",
            "Personal data must be protected against unauthorised disclosure.",
        ),
        Clause("Art. 8", "Children's consent", "Parental consent for children's data online."),
        Clause(
            "Art. 9",
            "Special categories",
            "Health, religion, ethnicity, sexual orientation, political opinion and similar "
            "data need extra protection.",
        ),
        Clause("Art. 15", "Right of access", "Data subjects can access their personal data."),
        Clause("Art. 17", "Right to erasure", "Data subjects can have their data erased."),
        Clause(
            "Art. 32",
            "Security of processing",
            "Appropriate technical measures must secure personal data.",
        ),
    ),
)

REGULATIONS: Mapping[str, Regulation] = MappingProxyType({r.key: r for r in (DPDP, GDPR)})

# Which clauses each built-in check produces evidence for, per regulation.
# Custom checks declare their own via the ``clauses`` attribute on BaseCheck.
CHECK_CLAUSES: Mapping[str, Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "pii_leak": {"dpdp": ("s.8(5)",), "gdpr": ("Art. 5(1)(f)", "Art. 32")},
        "prompt_injection": {"dpdp": ("s.8(5)",), "gdpr": ("Art. 32",)},
        "hallucination": {"dpdp": ("s.8(3)",), "gdpr": ("Art. 5(1)(d)",)},
    }
)


def get_regulation(key: str) -> Regulation:
    try:
        return REGULATIONS[key.lower()]
    except KeyError:
        raise ValueError(f"Unknown regulation {key!r}. Available: {sorted(REGULATIONS)}") from None
