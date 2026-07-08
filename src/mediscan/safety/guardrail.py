"""Output guardrail: block AI text that crosses into practicing medicine.

WHY THIS FILE EXISTS
    Even a well-prompted model can slip and produce a diagnosis, a drug dose,
    or a prescription. MediScan explains; it does not practice medicine. This
    is a HARD, DETERMINISTIC boundary — a clever prompt cannot talk it out of
    its job. If AI text trips it, the assembly (5.10) drops that output to the
    deterministic template (5.8).

    Conservative by design: over-blocking falls back to a safe template (an
    acceptable error); under-blocking is not. Reasons are CATEGORIES, never
    the offending text (no PHI in logs).
"""

import re
from typing import NamedTuple


class GuardrailResult(NamedTuple):
    passed: bool
    category: str | None = None  # which rule tripped, never the text itself


# (category, pattern). Patterns are tuned to catch clear violations while
# leaving benign explanations ("9.8 g/dL", "a doctor can diagnose") alone.
_FORBIDDEN: list[tuple[str, re.Pattern[str]]] = [
    # A dose INSTRUCTION: an action verb near a number + a medication unit.
    (
        "medication_dose",
        re.compile(
            r"\b(?:take|takes|taking|administer\w*|give|gives|giving|dose[ds]?)\b"
            r"[^.\n]{0,40}\b\d+(?:\.\d+)?\s?"
            r"(?:mg|mcg|ml|iu|units?|tablets?|pills?|capsules?)\b",
            re.I,
        ),
    ),
    # Explicit prescription language.
    ("prescription", re.compile(r"\bprescrib(?:e|es|ed|ing|tion)\b", re.I)),
    # A definitive diagnosis being MADE (not merely "a doctor can diagnose").
    (
        "diagnosis",
        re.compile(
            r"\b(?:diagnosed with|been diagnosed|i diagnose|the diagnosis is)\b",
            re.I,
        ),
    ),
]


def check(text: str) -> GuardrailResult:
    """Return pass, or fail with the category that tripped."""
    for category, pattern in _FORBIDDEN:
        if pattern.search(text):
            return GuardrailResult(passed=False, category=category)
    return GuardrailResult(passed=True)
