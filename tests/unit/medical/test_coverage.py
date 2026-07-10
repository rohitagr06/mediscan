"""Tests for coverage classification + the assessment allowlist (6.5.7).

The core guarantee (#006/#011/#030): every parsed test is accounted for —
graded ONLY if policy allows, otherwise acknowledged — and acknowledged tests
never influence the urgency verdict.
"""

from mediscan.medical.coverage import classify_coverage, policy_for
from mediscan.medical.urgency import assess_urgency
from mediscan.schemas import (
    AcknowledgeClass,
    AssessmentTier,
    LabResult,
    ParseOutcome,
    ReferenceRange,
    Sex,
    UrgencyLevel,
)


def _lab(name, value, low=None, high=None, unit="unit"):
    rng = None
    if low is not None or high is not None:
        rng = ReferenceRange(low=low, high=high)
    return LabResult(test_name=name, value=value, unit=unit, reference_range=rng)


# --- policy lookup ---------------------------------------------------------


def test_policy_tiers_and_assessable_flag():
    assert policy_for("Hemoglobin").assessable is True
    assert policy_for("Hemoglobin").tier is AssessmentTier.ASSESSED
    assert policy_for("PSA").assessable is False
    assert policy_for("PSA").tier is AssessmentTier.EXCLUDED
    assert policy_for("hs-CRP").tier is AssessmentTier.DEFERRED
    assert policy_for("Nonexistent Test") is None


# --- the docs/14 done-when scenario ----------------------------------------


def test_mixed_report_is_split_and_urgency_ignores_acknowledged():
    outcome = ParseOutcome(
        results=[
            _lab("Hemoglobin", 8.0, 13.0, 17.0, "g/dL"),  # assessed (LOW, abnormal)
            _lab("PSA", 5.2, high=4.0, unit="ng/mL"),  # acknowledged-sensitive
            _lab("Widget Level", 42.0, 10.0, 20.0, "wu"),  # unknown -> ack-numeric
        ],
        unparsed_lines=["-- some header --"],
    )
    cov = classify_coverage(outcome)

    # exactly one graded finding
    assert len(cov.assessed) == 1
    assert cov.assessed[0].test_name == "Hemoglobin"

    # two acknowledged, correctly classified
    assert len(cov.acknowledged) == 2
    by_name = {a.test_name: a for a in cov.acknowledged}
    assert by_name["PSA"].classification is AcknowledgeClass.SENSITIVE
    assert by_name["PSA"].reference_range is None  # sensitive: no range shown
    assert by_name["Widget Level"].classification is AcknowledgeClass.NUMERIC
    assert by_name["Widget Level"].reference_range is not None  # numeric: range kept

    # unparsed line preserved
    assert cov.unparsed == ["-- some header --"]

    # urgency built ONLY from the assessed bucket reflects the abnormal Hb,
    # and the acknowledged PSA cannot have influenced it.
    urgency = assess_urgency(cov.assessed)
    assert urgency.level is not UrgencyLevel.ROUTINE


def test_parsed_psa_is_never_graded_even_with_a_range():
    # a PSA line that parses (it has a one-sided range) must NOT become a
    # SeverityAssessment — the allowlist gate is the whole point.
    outcome = ParseOutcome(results=[_lab("Total PSA", 9.9, high=4.0, unit="ng/mL")])
    cov = classify_coverage(outcome)
    assert cov.assessed == []
    assert len(cov.acknowledged) == 1
    assert cov.acknowledged[0].classification is AcknowledgeClass.SENSITIVE


def test_lipid_name_variant_is_assessed_via_normalization():
    # "Cholesterol - LDL" normalizes to the assessable "LDL Cholesterol".
    outcome = ParseOutcome(
        results=[_lab("Cholesterol - LDL", 82.0, high=100.0, unit="mg/dL")]
    )
    cov = classify_coverage(outcome)
    assert len(cov.assessed) == 1
    assert cov.assessed[0].test_name == "Cholesterol - LDL"  # engine keeps raw name


def test_empty_outcome_is_empty_coverage():
    cov = classify_coverage(ParseOutcome())
    assert cov.assessed == [] and cov.acknowledged == [] and cov.unparsed == []


def test_sex_is_passed_through_to_assessment():
    # a non-sex-aware test behaves the same, but the arg must be accepted.
    outcome = ParseOutcome(results=[_lab("Hemoglobin", 8.0, 13.0, 17.0, "g/dL")])
    cov = classify_coverage(outcome, Sex.MALE)
    assert len(cov.assessed) == 1
