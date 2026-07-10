"""Tests for the coverage schemas (AssessmentPolicy, AcknowledgedTest, ...)."""

import pytest
from pydantic import ValidationError

from mediscan.schemas import (
    AcknowledgeClass,
    AcknowledgedTest,
    AssessmentPolicy,
    AssessmentTier,
    CoverageResult,
)


def test_policy_assessable_is_true_only_for_tier_a():
    assert AssessmentPolicy(test_name="X", tier=AssessmentTier.ASSESSED).assessable
    assert not AssessmentPolicy(test_name="X", tier=AssessmentTier.DEFERRED).assessable
    assert not AssessmentPolicy(test_name="X", tier=AssessmentTier.EXCLUDED).assessable


def test_acknowledged_test_defaults_and_fields():
    a = AcknowledgedTest(
        test_name="PSA", value=5.2, classification=AcknowledgeClass.SENSITIVE
    )
    assert a.reference_range is None
    assert a.unit is None


def test_acknowledged_test_rejects_non_finite_value():
    with pytest.raises(ValidationError):
        AcknowledgedTest(
            test_name="X", value=float("inf"), classification=AcknowledgeClass.NUMERIC
        )


def test_coverage_result_defaults_to_empty_lists():
    cov = CoverageResult()
    assert cov.assessed == [] and cov.acknowledged == [] and cov.unparsed == []
