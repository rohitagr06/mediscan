"""Adversarial tests for the urgency roll-up (Claude's half of 4.9).

Rohit's test_urgency.py confirms the happy path: each band maps to the
right level. THIS file attacks the roll-up's guarantees -- the properties
that must hold no matter the input order, count, or mix:

  * the report is NEVER softer than its worst finding (conservative);
  * order of the findings does not change the verdict;
  * urgency is compared by clinical RANK, not by string order (the
    StrEnum trap);
  * a Critical always dominates an un-assessable floor;
  * an un-assessable finding raises a quiet report but never LOWERS a
    louder one;
  * the engine is pure (its inputs come back untouched).

Several tests build SeverityAssessment objects BY HAND so we can pin an
exact severity/direction without routing through the KB -- this isolates
the roll-up from how severity was derived, which is the whole point of a
layered design.
"""

import pytest

from mediscan.medical.severity import assess_results
from mediscan.medical.urgency import assess_urgency
from mediscan.schemas import (
    AbnormalDirection,
    LabResult,
    Severity,
    UrgencyLevel,
)
from mediscan.schemas.medical import RangeResolution, RangeSource, SeverityAssessment


def sa(test_name, severity, direction=None, value=1.0) -> SeverityAssessment:
    """Build a SeverityAssessment directly, bypassing the KB.

    range_resolution is a throwaway UNKNOWN here: the urgency layer only
    reads .severity / .abnormal_direction / .test_name / .value, so the
    resolution's contents are irrelevant to what we're testing.
    """
    return SeverityAssessment(
        test_name=test_name,
        value=value,
        severity=severity,
        abnormal_direction=direction,
        range_resolution=RangeResolution(reference_range_source=RangeSource.UNKNOWN),
    )


# ---------------------------------------------------------------------------
# Conservative roll-up: never softer than the worst finding.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "severities, expected",
    [
        # worst finding dictates the level, regardless of the rest
        ([Severity.NORMAL, Severity.MODERATE], UrgencyLevel.CONSULT_SOON),
        ([Severity.NORMAL, Severity.HIGH], UrgencyLevel.URGENT),
        ([Severity.MILD, Severity.CRITICAL], UrgencyLevel.IMMEDIATE),
        ([Severity.MODERATE, Severity.HIGH], UrgencyLevel.URGENT),
        ([Severity.HIGH, Severity.CRITICAL], UrgencyLevel.IMMEDIATE),
        # many mild/normal never accumulate into something louder
        ([Severity.MILD] * 10, UrgencyLevel.ROUTINE),
        # a lone critical among a crowd of normals still wins
        (
            [Severity.NORMAL] * 8 + [Severity.CRITICAL],
            UrgencyLevel.IMMEDIATE,
        ),
    ],
)
def test_worst_finding_dictates_level(severities, expected):
    # NORMAL must not carry a direction (the LabResult schema forbids it),
    # so give a direction only to the abnormal bands.
    assessments = [
        sa(f"T{i}", s, None if s is Severity.NORMAL else AbnormalDirection.HIGH)
        for i, s in enumerate(severities)
    ]
    assert assess_urgency(assessments).level is expected


def test_order_independence():
    """Shuffling the findings must not change the verdict."""
    findings = [
        sa("A", Severity.NORMAL),
        sa("B", Severity.MODERATE, AbnormalDirection.LOW),
        sa("C", Severity.CRITICAL, AbnormalDirection.HIGH),
        sa("D", Severity.MILD, AbnormalDirection.LOW),
    ]
    forward = assess_urgency(findings).level
    backward = assess_urgency(list(reversed(findings))).level
    assert forward is backward is UrgencyLevel.IMMEDIATE


def test_ties_do_not_escalate():
    """Two Moderate findings stay Consult Soon -- severities don't add up."""
    findings = [
        sa("A", Severity.MODERATE, AbnormalDirection.LOW),
        sa("B", Severity.MODERATE, AbnormalDirection.HIGH),
    ]
    assert assess_urgency(findings).level is UrgencyLevel.CONSULT_SOON


# ---------------------------------------------------------------------------
# The StrEnum rank trap: comparison must be by clinical rank, not string.
# ---------------------------------------------------------------------------


def test_rank_not_string_order():
    """A single Consult-Soon finding beats Routine.

    If the engine compared UrgencyLevel members as strings, max() of
    {"routine", "consult_soon"} would be "routine" ('r' > 'c') -- WRONG.
    This test fails loudly if anyone replaces the rank table with naive
    string/enum comparison.
    """
    findings = [
        sa("A", Severity.NORMAL),
        sa("B", Severity.MODERATE, AbnormalDirection.LOW),
    ]
    assert assess_urgency(findings).level is UrgencyLevel.CONSULT_SOON


# ---------------------------------------------------------------------------
# Un-assessable interplay.
# ---------------------------------------------------------------------------


def test_critical_dominates_unassessable_floor():
    """A Critical (Immediate) is not dragged down to the un-assessable floor."""
    findings = [sa("Mystery", None), sa("Hb", Severity.CRITICAL, AbnormalDirection.LOW)]
    result = assess_urgency(findings)
    assert result.level is UrgencyLevel.IMMEDIATE
    # both the mystery and the critical are named
    assert "Mystery" in result.contributing_tests
    assert "Hb" in result.contributing_tests


def test_unassessable_never_lowers_a_louder_report():
    """An un-assessable finding floors UP, never down: High stays Urgent."""
    findings = [sa("Hb", Severity.HIGH, AbnormalDirection.LOW), sa("Mystery", None)]
    assert assess_urgency(findings).level is UrgencyLevel.URGENT


def test_all_unassessable_is_consult_soon_and_lists_all():
    findings = [sa("X", None), sa("Y", None), sa("Z", None)]
    result = assess_urgency(findings)
    assert result.level is UrgencyLevel.CONSULT_SOON
    assert result.contributing_tests == ["X", "Y", "Z"]
    assert len(result.reasons) == 3


# ---------------------------------------------------------------------------
# Reasons & contributing content.
# ---------------------------------------------------------------------------


def test_reason_names_the_driver():
    findings = [sa("Hemoglobin", Severity.HIGH, AbnormalDirection.LOW, value=7.5)]
    result = assess_urgency(findings)
    joined = " ".join(result.reasons).lower()
    assert "hemoglobin" in joined
    assert "high" in joined
    assert "low" in joined


def test_contributing_excludes_normal_and_mild():
    """Only findings that raise urgency above Routine are 'contributing'."""
    findings = [
        sa("Normal1", Severity.NORMAL),
        sa("Mild1", Severity.MILD, AbnormalDirection.HIGH),
        sa("Mod1", Severity.MODERATE, AbnormalDirection.LOW),
    ]
    result = assess_urgency(findings)
    assert result.contributing_tests == ["Mod1"]


def test_direction_none_uses_abnormal_fallback():
    """Defensive branch: an abnormal finding with no recorded direction
    still produces a readable reason ('(abnormal)') and the right level."""
    findings = [sa("Weird", Severity.HIGH, direction=None, value=9.0)]
    result = assess_urgency(findings)
    assert result.level is UrgencyLevel.URGENT
    assert "(abnormal)" in " ".join(result.reasons)


# ---------------------------------------------------------------------------
# Purity: inputs come back untouched (decision #021 spirit).
# ---------------------------------------------------------------------------


def test_engine_does_not_mutate_inputs():
    findings = [
        sa("Hb", Severity.CRITICAL, AbnormalDirection.LOW),
        sa("Plt", Severity.NORMAL),
    ]
    before_len = len(findings)
    before_sev = [f.severity for f in findings]
    _ = assess_urgency(findings)
    assert len(findings) == before_len
    assert [f.severity for f in findings] == before_sev


def test_reasons_never_empty_even_all_normal():
    """Schema forbids empty reasons; the engine must always supply one."""
    result = assess_urgency([sa("A", Severity.NORMAL), sa("B", Severity.NORMAL)])
    assert result.level is UrgencyLevel.ROUTINE
    assert result.reasons  # non-empty positive statement
    assert result.contributing_tests == []


# ---------------------------------------------------------------------------
# End-to-end through the real severity engine (one integration-ish check).
# ---------------------------------------------------------------------------


def test_rollup_through_real_engine_critical_wins():
    """Two Platelet-panel values: one normal, one critically high -> Immediate."""
    labs = [
        LabResult(test_name="Platelet Count", value=250.0),  # NORMAL
        LabResult(test_name="Platelet Count", value=2500.0),  # past critical_high
    ]
    result = assess_urgency(assess_results(labs))
    assert result.level is UrgencyLevel.IMMEDIATE
