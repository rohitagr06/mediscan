"""Deterministic urgency roll-up (decisions #006, #022).

Turns a list of per-test SeverityAssessment verdicts into ONE overall
UrgencyAssessment for the whole report. Pure function, no AI, no mutation.

THE TWO SAFETY RULES (decision #022):
  1. Conservative roll-up: the report's urgency is the WORST finding's
     urgency -- never softer. One Critical value forces Seek Immediate Care.
  2. Unknown never looks fine: a value we could not assess (severity None)
     floors the report at Consult Soon and says so, rather than being
     silently ignored.
"""

from mediscan.medical.phrasing import describe_finding
from mediscan.schemas import (
    Severity,
    UrgencyAssessment,
    UrgencyLevel,
)
from mediscan.schemas.medical import SeverityAssessment

# Graduated mapping: each severity band maps to one urgency level.
# Normal and Mild are both Routine; every band above steps up by one.
_SEVERITY_TO_URGENCY: dict[Severity, UrgencyLevel] = {
    Severity.NORMAL: UrgencyLevel.ROUTINE,
    Severity.MILD: UrgencyLevel.ROUTINE,
    Severity.MODERATE: UrgencyLevel.CONSULT_SOON,
    Severity.HIGH: UrgencyLevel.URGENT,
    Severity.CRITICAL: UrgencyLevel.IMMEDIATE,
}

# UrgencyLevel is a StrEnum, so comparing its members compares their STRING
# values ("consult_soon" < "routine" alphabetically) -- which is NOT the
# clinical order. So we give each level an explicit numeric RANK and take
# the maximum by rank. This is the single source of truth for "which
# urgency is worse".
_URGENCY_RANK: dict[UrgencyLevel, int] = {
    UrgencyLevel.ROUTINE: 0,
    UrgencyLevel.CONSULT_SOON: 1,
    UrgencyLevel.URGENT: 2,
    UrgencyLevel.IMMEDIATE: 3,
}

# The floor an un-assessable finding imposes: we cannot confirm it is safe,
# so it must at least prompt a soon-ish consult.
_UNASSESSABLE_FLOOR = UrgencyLevel.CONSULT_SOON


def _worse(a: UrgencyLevel, b: UrgencyLevel) -> UrgencyLevel:
    """Return whichever urgency level is more severe (higher rank)."""
    return a if _URGENCY_RANK[a] >= _URGENCY_RANK[b] else b


def assess_urgency(assessments: list[SeverityAssessment]) -> UrgencyAssessment:
    """Roll many per-test verdicts up into one report-level urgency.

    Pure: builds and returns a NEW UrgencyAssessment; mutates nothing.
    """
    overall = UrgencyLevel.ROUTINE
    reasons: list[str] = []
    contributing: list[str] = []

    for a in assessments:
        if a.severity is None:
            # Un-assessable: floor the report and explain why (#022).
            finding_level = _UNASSESSABLE_FLOOR
            reasons.append(
                f"{a.test_name} could not be assessed (no reference range) "
                f"— flagged for review."
            )
            contributing.append(a.test_name)
        else:
            finding_level = _SEVERITY_TO_URGENCY[a.severity]
            # Only findings that actually raise urgency above Routine are
            # worth naming as reasons for the level.
            if finding_level != UrgencyLevel.ROUTINE:
                reasons.append(describe_finding(a))
                contributing.append(a.test_name)

        overall = _worse(overall, finding_level)

    # The schema forbids an empty reasons list (explainability by
    # construction). If nothing raised urgency above Routine, say so.
    # NOTE: we deliberately do NOT say "all within normal limits" here —
    # a MILD finding maps to Routine but is still OUTSIDE its range, so
    # that phrasing would let a mild abnormality masquerade as normal
    # (#011). "No results require prompt attention" is true either way.
    if not reasons:
        if not assessments:
            reasons.append("No lab results were available to assess.")
        else:
            reasons.append("No results require prompt attention.")

    return UrgencyAssessment(
        level=overall,
        reasons=reasons,
        contributing_tests=contributing,
    )
