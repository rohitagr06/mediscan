"""Tests for mediscan.schemas.urgency.

The key rule under guard: an UrgencyAssessment without at least one
human-readable reason must be impossible (explainability by construction).
"""

import pytest
from pydantic import ValidationError

from mediscan.schemas import UrgencyAssessment, UrgencyLevel


def test_urgency_levels_exact():
    assert [u.value for u in UrgencyLevel] == [
        "routine",
        "consult_soon",
        "urgent",
        "seek_immediate_care",
    ]


def test_valid_assessment():
    ua = UrgencyAssessment(
        level=UrgencyLevel.URGENT,
        reasons=["Hemoglobin critically low at 6.2 g/dL"],
        contributing_tests=["Hemoglobin"],
    )
    assert ua.level is UrgencyLevel.URGENT
    assert len(ua.reasons) == 1


def test_invalid_level_rejected():
    with pytest.raises(ValidationError):
        UrgencyAssessment(level="panic", reasons=["x"])


def test_zero_reasons_rejected():
    # Explainability is mandatory at the schema level
    with pytest.raises(ValidationError):
        UrgencyAssessment(level=UrgencyLevel.ROUTINE, reasons=[])


def test_contributing_tests_lists_are_independent():
    # default_factory must give each instance its OWN list
    a = UrgencyAssessment(level=UrgencyLevel.ROUTINE, reasons=["r"])
    b = UrgencyAssessment(level=UrgencyLevel.ROUTINE, reasons=["r"])
    a.contributing_tests.append("Hemoglobin")
    assert b.contributing_tests == []


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        UrgencyAssessment(level=UrgencyLevel.ROUTINE, reasons=["r"], diagnosis="anemia")
