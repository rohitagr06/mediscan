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
    """The outcome of one guardrail check.

    Attributes:
        passed: True if the text is safe to show; False if a rule tripped.
        category: The rule category that tripped (e.g. "medication_dose"),
            or None when passed. Deliberately a CATEGORY, never the offending
            text, so nothing PHI-adjacent leaks into logs.
    """

    passed: bool
    category: str | None = None


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
    """Check one piece of AI-generated text for forbidden medical content.

    Args:
        text: The AI output string to screen (e.g. a summary's text field).

    Returns:
        GuardrailResult(passed=True) if no rule matched, else
        GuardrailResult(passed=False, category=<rule name>). Callers treat a
        failure as "discard this AI output and use the deterministic template".
    """
    for category, pattern in _FORBIDDEN:
        if pattern.search(text):
            return GuardrailResult(passed=False, category=category)
    return GuardrailResult(passed=True)
