"""Adversarial coverage tests (Sprint 6.5.12, Claude's half).

The happy-path coverage cases live in test_coverage.py. These are the ones
that try to BREAK the two safety guarantees Sprint 6.5 rests on:

  * #006 — an acknowledged (non-graded) test can NEVER influence the verdict,
           no matter how alarming its value. This is the single most important
           safety property of the scope split: a sensitive tumour marker or a
           deferred test we haven't vetted must not be able to raise OR lower
           urgency.
  * sex plumbing — the patient's sex must thread all the way through
           classify_coverage into range resolution, so a sex-aware test with
           NO printed range falls back to the RIGHT sex's KB block (and to the
           widest union when sex is unknown, #029).

Everything here is deterministic and offline.
"""

from mediscan.medical.coverage import classify_coverage
from mediscan.medical.urgency import assess_urgency
from mediscan.schemas import (
    AbnormalDirection,
    AcknowledgeClass,
    LabResult,
    ParseOutcome,
    RangeSource,
    ReferenceRange,
    Severity,
    Sex,
    UrgencyLevel,
)


def _lab(name, value, low=None, high=None, unit="unit"):
    rng = None
    if low is not None or high is not None:
        rng = ReferenceRange(low=low, high=high)
    return LabResult(test_name=name, value=value, unit=unit, reference_range=rng)


# --- #006: an acknowledged value cannot move the verdict --------------------


def test_a_scary_acknowledged_sensitive_value_cannot_escalate_urgency():
    """A wildly abnormal SENSITIVE test must not raise urgency (#006).

    PSA is 50x its upper limit — the kind of number that screams "emergency".
    But PSA is Tier-C (acknowledged, never graded), and the only assessed test
    is a perfectly normal Hemoglobin. The verdict MUST stay ROUTINE: the
    acknowledged value never reaches the roll-up. If the allowlist gate ever
    leaks, this test flips to URGENT/IMMEDIATE and fails loudly.
    """
    outcome = ParseOutcome(
        results=[
            _lab("Hemoglobin", 15.0, 13.0, 17.0, "g/dL"),  # assessed, NORMAL
            _lab("PSA", 200.0, high=4.0, unit="ng/mL"),  # acknowledged, scary
        ]
    )
    cov = classify_coverage(outcome)

    assert [a.test_name for a in cov.assessed] == ["Hemoglobin"]
    assert cov.assessed[0].severity is Severity.NORMAL

    urgency = assess_urgency(cov.assessed)
    assert urgency.level is UrgencyLevel.ROUTINE  # the scary PSA changed nothing
    assert "PSA" not in urgency.contributing_tests


def test_a_scary_acknowledged_unknown_value_cannot_escalate_urgency():
    """Same guarantee for an UNKNOWN test (no policy row -> ack-numeric)."""
    outcome = ParseOutcome(
        results=[
            _lab("Hemoglobin", 15.0, 13.0, 17.0, "g/dL"),  # assessed, NORMAL
            _lab("Widget Level", 9999.0, 0.0, 10.0, "wu"),  # unknown, absurd value
        ]
    )
    cov = classify_coverage(outcome)
    urgency = assess_urgency(cov.assessed)

    assert urgency.level is UrgencyLevel.ROUTINE
    ack = {a.test_name: a for a in cov.acknowledged}
    assert ack["Widget Level"].classification is AcknowledgeClass.NUMERIC


def test_deferred_tier_b_is_acknowledged_numeric_and_never_graded():
    """A Tier-B DEFERRED numeric (hs-CRP) is shown WITH its range, not graded.

    Distinct from a sensitive test: the range IS kept (it's numeric, not
    hidden), but it still never enters the assessed set.
    """
    outcome = ParseOutcome(
        results=[_lab("hs-CRP", 9.0, high=3.0, unit="mg/L")]  # 3x the limit
    )
    cov = classify_coverage(outcome)

    assert cov.assessed == []  # never graded
    assert len(cov.acknowledged) == 1
    ack = cov.acknowledged[0]
    assert ack.classification is AcknowledgeClass.NUMERIC
    assert ack.reference_range is not None  # numeric: range kept


# --- sex threads through coverage into the KB fallback ----------------------


def test_sex_threads_through_coverage_into_the_kb_fallback():
    """A rangeless sex-aware test resolves to the RIGHT sex's KB block.

    The report omits Hemoglobin's range, so resolution falls back to the KB.
    The SAME 12.5 value must band differently per sex — LOW for a male
    (< 13.0), NORMAL for a female (within 12.0-15.0), NORMAL for unknown (the
    widest union 12.0-17.0 includes it, #029). Proves the sex argument is
    plumbed classify_coverage -> assess_lab_result -> resolve_reference_range.
    """
    expected = {
        Sex.MALE: (13.0, 17.0, Severity.MILD, AbnormalDirection.LOW),
        Sex.FEMALE: (12.0, 15.0, Severity.NORMAL, None),
        Sex.UNKNOWN: (12.0, 17.0, Severity.NORMAL, None),  # union of both
    }
    for sex, (low, high, severity, direction) in expected.items():
        outcome = ParseOutcome(
            results=[LabResult(test_name="Hemoglobin", value=12.5, unit="g/dL")]
        )
        cov = classify_coverage(outcome, sex)
        assert len(cov.assessed) == 1, sex
        a = cov.assessed[0]

        # the fallback came from the KB, for the right sex's bounds
        assert a.range_resolution.reference_range_source is RangeSource.KNOWLEDGE_BASE
        assert (
            a.range_resolution.reference_range.low,
            a.range_resolution.reference_range.high,
        ) == (
            low,
            high,
        ), sex
        # and the banding follows from those bounds
        assert a.severity is severity, sex
        assert a.abnormal_direction is direction, sex


def test_unknown_sex_defaults_when_no_sex_argument_is_given():
    """classify_coverage's sex defaults to UNKNOWN -> the union fallback."""
    outcome = ParseOutcome(
        results=[LabResult(test_name="Hemoglobin", value=12.5, unit="g/dL")]
    )
    cov = classify_coverage(outcome)  # no sex passed
    a = cov.assessed[0]
    assert (
        a.range_resolution.reference_range.low,
        a.range_resolution.reference_range.high,
    ) == (
        12.0,
        17.0,
    )
    assert a.severity is Severity.NORMAL
