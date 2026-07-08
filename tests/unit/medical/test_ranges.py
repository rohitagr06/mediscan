"""Unit tests for reference-range resolution (report-first + KB criticals, #023)."""

from mediscan.medical.ranges import resolve_reference_range
from mediscan.schemas import (
    LabResult,
    RangeSource,
    ReferenceRange,
)


def test_report_reference_range_takes_precedence() -> None:
    """The report's range is used for banding; KB criticals are merged in (#023)."""
    result = LabResult(
        test_name="Hemoglobin",
        value=9.8,
        reference_range=ReferenceRange(low=13.0, high=17.0),
    )

    resolution = resolve_reference_range(result)

    assert resolution.reference_range_source == RangeSource.REPORT
    assert resolution.reference_range == result.reference_range
    # KB Hemoglobin criticals (7/20) sit outside 13-17, so they are merged in.
    assert resolution.critical_thresholds.low == 7.0
    assert resolution.critical_thresholds.high == 20.0
    assert resolution.critical_thresholds.source == RangeSource.KNOWLEDGE_BASE


def test_known_test_name_falls_back_to_knowledge_base() -> None:
    result = LabResult(test_name="Hb", value=9.8)

    resolution = resolve_reference_range(result)

    assert resolution.reference_range_source == RangeSource.KNOWLEDGE_BASE
    assert resolution.reference_range is not None
    assert resolution.reference_range.low == 13.0
    assert resolution.reference_range.high == 17.0
    assert resolution.critical_thresholds.low == 7.0
    assert resolution.critical_thresholds.high == 20.0


def test_unknown_test_name_returns_unknown_resolution() -> None:
    result = LabResult(test_name="Ferritin", value=200.0)

    resolution = resolve_reference_range(result)

    assert resolution.reference_range_source == RangeSource.UNKNOWN
    assert resolution.reference_range is None
    assert resolution.critical_thresholds.low is None
    assert resolution.critical_thresholds.high is None
    assert resolution.critical_thresholds.source == RangeSource.UNKNOWN


def test_report_reference_range_overrides_knowledge_base_range() -> None:
    """The report's NORMAL range wins; KB still contributes criticals (#023)."""
    result = LabResult(
        test_name="Hb",
        value=9.8,
        reference_range=ReferenceRange(low=12.0, high=18.0),
    )

    resolution = resolve_reference_range(result)

    assert resolution.reference_range_source == RangeSource.REPORT
    assert resolution.reference_range.low == 12.0  # report range, not KB's 13-17
    assert resolution.reference_range.high == 18.0
    # 7 < 12 and 20 > 18, so both KB criticals sit outside and are kept.
    assert resolution.critical_thresholds.low == 7.0
    assert resolution.critical_thresholds.high == 20.0


# --- #023 merge-guard tests -------------------------------------------------


def test_kb_critical_inside_report_range_is_dropped() -> None:
    """A KB critical that falls inside the report's range is ignored (report wins)."""
    # Report says normal is 5-17. KB Hb critical_low=7 sits INSIDE that range,
    # which is contradictory, so it must be dropped; critical_high=20 is
    # outside and is kept.
    result = LabResult(
        test_name="Hemoglobin",
        value=6.0,
        reference_range=ReferenceRange(low=5.0, high=17.0),
    )

    resolution = resolve_reference_range(result)

    assert resolution.critical_thresholds.low is None  # dropped (inside)
    assert resolution.critical_thresholds.high == 20.0  # kept (outside)


def test_one_sided_report_range_drops_unguardable_critical() -> None:
    """With no report low bound, a KB critical_low can't be guarded -> dropped."""
    result = LabResult(
        test_name="Hemoglobin",
        value=9.8,
        reference_range=ReferenceRange(high=17.0),  # low is None
    )

    resolution = resolve_reference_range(result)

    assert resolution.critical_thresholds.low is None  # no report.low to guard
    assert resolution.critical_thresholds.high == 20.0  # 20 > 17, kept
