"""Exhaustive truth-table tests for the deterministic severity engine.

WHY THIS FILE MATTERS MOST
    `medical/severity.py` is the safety heart of MediScan (decision #006):
    it is what turns a number into "mild / moderate / high / critical".
    If this logic is wrong, the whole product is wrong in the most
    dangerous possible way -- it could tell someone a critical value is
    fine. So this is the single most heavily tested module in the project.

HOW THESE TESTS ARE ORGANISED (read top to bottom)
    1. Small helpers that build `RangeResolution` objects by hand, so each
       test controls the range + critical thresholds exactly.
    2. The `_band` truth table: for a fixed Hb-like range (13-17, criticals
       7/20) we pin the expected band for representative values on BOTH
       sides -- this is the "Option B, criticals present" path.
    3. Boundary-exact tests: the values that live EXACTLY on an edge
       (13.0, 17.0 -> NORMAL because the range test is strict; 7.0, 20.0
       -> CRITICAL because the critical test is inclusive). Edges are where
       `<` vs `<=` bugs hide.
    4. The "Option A, no criticals" path, whose defining safety property is
       CAP-AT-HIGH: without a sourced critical threshold we NEVER invent a
       CRITICAL verdict, no matter how far out the value is (decision #020).
    5. The un-assessable path: no range at all -> severity is None, never a
       reassuring NORMAL.
    6. The float-safe zero-boundary guard.
    7. End-to-end `assess_lab_result` through the real KB, plus a purity
       check (the input LabResult is never mutated -- decision #021).
    8. Proof the config cutoffs are LIVE (change the setting, the band
       moves), and that inverted cutoffs are rejected at Settings load.

A NOTE ON TEST STYLE
    `@pytest.mark.parametrize` runs the same test body once per row in a
    table. Each row is (inputs..., expected) -- so the test reads like the
    truth table it is, and a failure names the exact row that broke.
"""

import pytest
from pydantic import ValidationError

from mediscan.config import settings
from mediscan.medical.severity import _band, assess_lab_result, assess_results
from mediscan.schemas import (
    AbnormalDirection,
    LabResult,
    RangeResolution,
    ReferenceRange,
    Severity,
    SeverityAssessment,
)

# CriticalThresholds/RangeSource live in the medical schema module.
from mediscan.schemas.medical import CriticalThresholds, RangeSource

# ---------------------------------------------------------------------------
# Helpers: build a RangeResolution by hand so each test controls everything.
# ---------------------------------------------------------------------------


def res_with_criticals(low, high, critical_low, critical_high) -> RangeResolution:
    """A KB-style resolution: a range PLUS sourced critical thresholds.

    This is the 'Option B' path -- because critical thresholds exist, the
    engine bands by fraction-of-the-way-toward-critical and CAN reach
    CRITICAL.
    """
    return RangeResolution(
        reference_range=ReferenceRange(low=low, high=high),
        reference_range_source=RangeSource.KNOWLEDGE_BASE,
        critical_thresholds=CriticalThresholds(low=critical_low, high=critical_high),
    )


def res_no_criticals(low=None, high=None) -> RangeResolution:
    """A range with NO critical thresholds -- the 'Option A' path.

    Bands by percentage-from-the-boundary and is CAPPED at HIGH: it must
    never produce CRITICAL, because no sourced critical line exists.
    """
    return RangeResolution(
        reference_range=ReferenceRange(low=low, high=high),
        reference_range_source=RangeSource.REPORT,
    )


def res_unknown() -> RangeResolution:
    """No range at all -- the value is un-assessable."""
    return RangeResolution(reference_range_source=RangeSource.UNKNOWN)


# A single fixed range reused across the Option-B truth table:
# Hemoglobin-like. normal 13.0-17.0, critical at/below 7.0, at/above 20.0.
HB = dict(low=13.0, high=17.0, critical_low=7.0, critical_high=20.0)


# ---------------------------------------------------------------------------
# 1. Option B truth table (criticals present) -- LOW side.
#    frac = (low - value) / (low - critical_low) = (13 - value) / 6
#    cutoffs (defaults): frac_mild=0.33, frac_moderate=0.66
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected_sev, expected_dir",
    [
        # --- inside the range -> NORMAL, no direction ---
        (15.0, Severity.NORMAL, None),
        (13.0, Severity.NORMAL, None),  # exactly on low edge: strict < -> inside
        (17.0, Severity.NORMAL, None),  # exactly on high edge: strict > -> inside
        # --- LOW side bands ---
        (12.5, Severity.MILD, AbnormalDirection.LOW),  # frac 0.083
        (9.8, Severity.MODERATE, AbnormalDirection.LOW),  # frac 0.533
        (8.0, Severity.HIGH, AbnormalDirection.LOW),  # frac 0.833
        (7.01, Severity.HIGH, AbnormalDirection.LOW),  # just ABOVE critical -> HIGH
        (7.0, Severity.CRITICAL, AbnormalDirection.LOW),
        # exactly critical: <= -> CRITICAL
        (6.0, Severity.CRITICAL, AbnormalDirection.LOW),  # below critical
        (0.5, Severity.CRITICAL, AbnormalDirection.LOW),  # far below
        # --- HIGH side bands ---
        # frac = (value - 17) / (20 - 17) = (value - 17) / 3
        (17.4, Severity.MILD, AbnormalDirection.HIGH),  # frac 0.133
        (18.5, Severity.MODERATE, AbnormalDirection.HIGH),  # frac 0.5
        (19.5, Severity.HIGH, AbnormalDirection.HIGH),  # frac 0.833
        (19.99, Severity.HIGH, AbnormalDirection.HIGH),  # just BELOW critical -> HIGH
        (20.0, Severity.CRITICAL, AbnormalDirection.HIGH),
        # exactly critical: >= -> CRITICAL
        (25.0, Severity.CRITICAL, AbnormalDirection.HIGH),  # above critical
    ],
)
def test_band_option_b_with_criticals(value, expected_sev, expected_dir):
    """Full band table for a range that carries sourced critical thresholds."""
    sev, direction = _band(value, res_with_criticals(**HB))
    assert sev is expected_sev
    assert direction is expected_dir


# ---------------------------------------------------------------------------
# 2. Boundary-exact behaviour, isolated and named (the reviewer's ask #8).
#    These pin the deliberate asymmetry in our comparison operators:
#    range edges use strict < / > ; critical edges use inclusive <= / >=.
# ---------------------------------------------------------------------------


def test_range_edges_are_normal_strict_comparison():
    """A value exactly on a reference-range edge counts as INSIDE (NORMAL)."""
    res = res_with_criticals(**HB)
    assert _band(13.0, res) == (Severity.NORMAL, None)
    assert _band(17.0, res) == (Severity.NORMAL, None)


def test_critical_edges_are_critical_inclusive_comparison():
    """A value exactly on a critical threshold IS critical (round toward danger)."""
    res = res_with_criticals(**HB)
    assert _band(7.0, res) == (Severity.CRITICAL, AbnormalDirection.LOW)
    assert _band(20.0, res) == (Severity.CRITICAL, AbnormalDirection.HIGH)


# ---------------------------------------------------------------------------
# 3. Option A (no criticals): CAP-AT-HIGH is the safety property.
#    range 40-50, no criticals. dev = |value - boundary| / |boundary|
#    cutoffs (defaults): pct_mild=0.15, pct_moderate=0.30
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected_sev, expected_dir",
    [
        (45.0, Severity.NORMAL, None),
        (40.0, Severity.NORMAL, None),  # low edge inside
        (50.0, Severity.NORMAL, None),  # high edge inside
        # LOW side (boundary 40)
        (38.0, Severity.MILD, AbnormalDirection.LOW),  # dev 0.050
        (33.0, Severity.MODERATE, AbnormalDirection.LOW),  # dev 0.175
        (26.0, Severity.HIGH, AbnormalDirection.LOW),  # dev 0.350
        (1.0, Severity.HIGH, AbnormalDirection.LOW),  # dev 0.975 -> STILL only HIGH
        # HIGH side (boundary 50)
        (53.0, Severity.MILD, AbnormalDirection.HIGH),  # dev 0.060
        (58.0, Severity.MODERATE, AbnormalDirection.HIGH),  # dev 0.160
        (70.0, Severity.HIGH, AbnormalDirection.HIGH),  # dev 0.400
        (200.0, Severity.HIGH, AbnormalDirection.HIGH),  # dev 3.0 -> STILL only HIGH
    ],
)
def test_band_option_a_no_criticals_caps_at_high(value, expected_sev, expected_dir):
    """Without sourced criticals, the engine NEVER invents CRITICAL (#020)."""
    sev, direction = _band(value, res_no_criticals(low=40.0, high=50.0))
    assert sev is expected_sev
    assert direction is expected_dir


def test_option_a_never_returns_critical_even_at_extremes():
    """Belt-and-braces: sweep absurd values, assert CRITICAL never appears."""
    res = res_no_criticals(low=40.0, high=50.0)
    for value in (0.001, 5.0, 1_000.0, 1_000_000.0):
        sev, _ = _band(value, res)
        assert sev is not Severity.CRITICAL


# ---------------------------------------------------------------------------
# 4. Un-assessable: no range -> severity is None (NOT NORMAL).
#    "Unknown must never masquerade as fine."
# ---------------------------------------------------------------------------


def test_band_unknown_range_is_unassessable():
    sev, direction = _band(9.8, res_unknown())
    assert sev is None
    assert direction is None


# ---------------------------------------------------------------------------
# 5. One-sided ranges must not crash on the missing bound.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected_sev",
    [
        (150.0, Severity.NORMAL),  # below the only (high) bound -> inside
        (250.0, Severity.MODERATE),  # dev 50/200 = 0.25 -> MODERATE
        (300.0, Severity.HIGH),  # dev 100/200 = 0.50, no criticals -> capped HIGH
    ],
)
def test_band_one_sided_high_only_range(value, expected_sev):
    """
    A '< 200'-style range (only high set) bands the high side,
    low side is 'inside'.
    """
    res = res_no_criticals(high=200.0)  # low is None
    sev, _ = _band(value, res)
    assert sev is expected_sev


# ---------------------------------------------------------------------------
# 6. Float-safe zero-boundary guard (the reviewer's ask #1).
#    A boundary of 0 can't be a denominator; the guard must catch it even
#    when the zero arrived as float dust (2e-17), and return a conservative
#    HIGH rather than dividing by ~zero.
# ---------------------------------------------------------------------------


def test_zero_boundary_is_guarded_conservatively():
    res = res_no_criticals(low=0.0, high=10.0)
    # value below a zero low-boundary: can't take a percentage of zero.
    sev, direction = _band(-0.5, res)
    assert sev is Severity.HIGH
    assert direction is AbnormalDirection.LOW


def test_zero_boundary_guard_survives_float_dust():
    """A boundary that is 'zero' only to within float error is still caught."""
    res = res_no_criticals(low=1e-17, high=10.0)  # ~0 but not exactly
    sev, _ = _band(-1.0, res)
    assert sev is Severity.HIGH  # guard fired; no divide-by-almost-zero blowup


# ---------------------------------------------------------------------------
# 7. End-to-end assess_lab_result through the REAL knowledge base + purity.
# ---------------------------------------------------------------------------


def test_assess_lab_result_uses_kb_when_report_has_no_range():
    """No report range -> KB fallback fires, criticals come along."""
    result = LabResult(test_name="Hemoglobin", value=9.8, unit="g/dL")
    assessment = assess_lab_result(result)

    assert isinstance(assessment, SeverityAssessment)
    assert assessment.severity is Severity.MODERATE
    assert assessment.abnormal_direction is AbnormalDirection.LOW
    assert (
        assessment.range_resolution.reference_range_source is RangeSource.KNOWLEDGE_BASE
    )
    # the assessment carries the value + name so it is self-contained
    assert assessment.test_name == "Hemoglobin"
    assert assessment.value == 9.8


def test_assess_report_range_keeps_normal_band_but_merges_kb_criticals():
    """#023: the report's range wins for banding, but a value past a MERGED
    KB critical threshold still reaches CRITICAL."""
    result = LabResult(
        test_name="Hemoglobin",
        value=6.0,
        unit="g/dL",
        reference_range=ReferenceRange(low=13.0, high=17.0),
    )
    assessment = assess_lab_result(result)
    # the NORMAL range still comes from the report...
    assert assessment.range_resolution.reference_range_source is RangeSource.REPORT
    # ...but the KB critical_low (7.0) was merged in, so 6.0 is CRITICAL, not
    # merely HIGH. This is the safety fix of decision #023.
    assert assessment.severity is Severity.CRITICAL
    assert assessment.abnormal_direction is AbnormalDirection.LOW
    assert assessment.range_resolution.critical_thresholds.low == 7.0


def test_assess_unknown_test_is_unassessable():
    """A test the KB doesn't know, with no report range -> severity None."""
    result = LabResult(test_name="Zorblaxine", value=42.0, unit="mg/dL")
    assessment = assess_lab_result(result)
    assert assessment.severity is None
    assert assessment.abnormal_direction is None
    assert assessment.range_resolution.reference_range_source is RangeSource.UNKNOWN


def test_assess_lab_result_does_not_mutate_input():
    """Purity (decision #021): the input LabResult is untouched."""
    result = LabResult(test_name="Hemoglobin", value=9.8, unit="g/dL")
    _ = assess_lab_result(result)
    # severity/direction on the INPUT stay None -- the verdict lives only
    # on the returned SeverityAssessment, never back-written onto the input.
    assert result.severity is None
    assert result.abnormal_direction is None


def test_assess_results_aligns_positionally():
    """assess_results returns one verdict per input, in order."""
    results = [
        LabResult(test_name="Hemoglobin", value=15.0, unit="g/dL"),  # NORMAL
        LabResult(test_name="Hemoglobin", value=9.8, unit="g/dL"),  # MODERATE low
        LabResult(test_name="Hemoglobin", value=6.0, unit="g/dL"),  # CRITICAL low
    ]
    out = assess_results(results)
    assert [a.severity for a in out] == [
        Severity.NORMAL,
        Severity.MODERATE,
        Severity.CRITICAL,
    ]
    assert [a.value for a in out] == [15.0, 9.8, 6.0]


# ---------------------------------------------------------------------------
# 8. The config cutoffs are LIVE, and inverted cutoffs are rejected.
# ---------------------------------------------------------------------------


def test_config_cutoffs_are_live(monkeypatch):
    """Proof the band actually reads settings: widen mild, MODERATE -> MILD.

    9.8 gives frac ~0.53. With the default frac_mild=0.33 that's MODERATE.
    If we move frac_mild up to 0.60, the SAME value must now band as MILD --
    demonstrating the cutoff is read live from settings, not baked in.
    """
    res = res_with_criticals(**HB)

    # baseline with real defaults
    assert _band(9.8, res)[0] is Severity.MODERATE

    monkeypatch.setattr(settings, "severity_frac_mild", 0.60)
    assert _band(9.8, res)[0] is Severity.MILD


def test_inverted_frac_cutoffs_are_rejected():
    """Settings refuses frac_mild >= frac_moderate (the Fix-2 guard)."""
    from mediscan.config import Settings

    with pytest.raises(ValidationError):
        Settings(severity_frac_mild=0.8, severity_frac_moderate=0.4)


def test_inverted_pct_cutoffs_are_rejected():
    """Settings refuses pct_mild >= pct_moderate."""
    from mediscan.config import Settings

    with pytest.raises(ValidationError):
        Settings(severity_pct_mild=0.5, severity_pct_moderate=0.2)
