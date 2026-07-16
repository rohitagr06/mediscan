"""Plain-language phrasing for a single finding (Sprint 8.6).

WHY THIS FILE EXISTS
    Both the urgency roll-up (reasons) and the deterministic template
    summaries need to describe one finding in a human sentence. They used to
    do it separately, producing the confusing "X is high (low) at 0.01" —
    where "high" is the SEVERITY band and "low" the DIRECTION, two different
    axes jammed together. This one shared helper phrases a finding clearly, so
    the engine and the summaries always read the same way.

    Pure function, no AI, no I/O. Lives in medical/ (the engine owns the
    verdict's wording); ai/templates.py imports it (ai -> medical is allowed).
"""

from mediscan.schemas.labs import AbnormalDirection, Severity
from mediscan.schemas.medical import SeverityAssessment

# Severity band -> how strongly to phrase it (adverb). NORMAL never reaches
# here (callers filter it out), but .get() keeps it safe if it ever did.
_SEVERITY_ADVERB: dict[Severity, str] = {
    Severity.MILD: "mildly",
    Severity.MODERATE: "moderately",
    Severity.HIGH: "markedly",
    Severity.CRITICAL: "critically",
}

# Direction -> a plain word. "elevated" reads better than "high" for a value.
_DIRECTION_WORD: dict[AbnormalDirection, str] = {
    AbnormalDirection.LOW: "low",
    AbnormalDirection.HIGH: "elevated",
}


def describe_finding(a: SeverityAssessment) -> str:
    """One clear sentence for a single finding.

    Examples:
        "Creatinine is mildly elevated at 1.33."
        "Absolute Basophil Count is markedly low at 0.01."
        "Uric Acid could not be assessed (no reference range)." (severity None)
    """
    if a.severity is None:
        return f"{a.test_name} could not be assessed (no reference range)."
    if a.abnormal_direction is not None:
        direction = _DIRECTION_WORD[a.abnormal_direction]
    else:
        direction = "outside range"
    adverb = _SEVERITY_ADVERB.get(a.severity, "")
    phrase = f"{adverb} {direction}".strip()
    return f"{a.test_name} is {phrase} at {a.value}."
