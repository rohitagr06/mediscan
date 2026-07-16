"""Tests for the shared finding-phrasing helper (Sprint 8.6)."""

from mediscan.medical.phrasing import describe_finding
from mediscan.schemas.labs import AbnormalDirection, ReferenceRange, Severity
from mediscan.schemas.medical import (
    RangeResolution,
    RangeSource,
    SeverityAssessment,
)


def _assess(name, value, severity, direction):
    return SeverityAssessment(
        test_name=name,
        value=value,
        severity=severity,
        abnormal_direction=direction,
        range_resolution=RangeResolution(
            reference_range=ReferenceRange(low=1.0, high=2.0),
            reference_range_source=RangeSource.REPORT,
        ),
    )


def test_mild_high_reads_as_mildly_elevated():
    a = _assess("Creatinine", 1.33, Severity.MILD, AbnormalDirection.HIGH)
    assert describe_finding(a) == "Creatinine is mildly elevated at 1.33."


def test_high_severity_low_direction_reads_clearly():
    # The old bug: "is high (low)". Now: severity adverb + direction word.
    a = _assess("Absolute Basophil Count", 0.01, Severity.HIGH, AbnormalDirection.LOW)
    assert describe_finding(a) == "Absolute Basophil Count is markedly low at 0.01."
    # The confusing "(low)" parenthetical must be gone.
    assert "(low)" not in describe_finding(a)


def test_moderate_high():
    a = _assess("Uric Acid", 8.5, Severity.MODERATE, AbnormalDirection.HIGH)
    assert describe_finding(a) == "Uric Acid is moderately elevated at 8.5."


def test_critical_low():
    a = _assess("Potassium", 2.1, Severity.CRITICAL, AbnormalDirection.LOW)
    assert describe_finding(a) == "Potassium is critically low at 2.1."


def test_unassessable_severity_none():
    a = SeverityAssessment(
        test_name="Mystery",
        value=5.0,
        severity=None,
        abnormal_direction=None,
        range_resolution=RangeResolution(reference_range_source=RangeSource.UNKNOWN),
    )
    assert "could not be assessed" in describe_finding(a)
