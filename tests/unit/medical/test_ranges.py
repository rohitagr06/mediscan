"""Unit tests for reference-range resolution."""

from mediscan.medical.ranges import resolve_reference_range
from mediscan.schemas import (
    LabResult,
    RangeSource,
    ReferenceRange,
)


def test_report_reference_range_takes_precedence() -> None:
    result = LabResult(
        test_name="Hemoglobin",
        value=9.8,
        reference_range=ReferenceRange(
            low=13.0,
            high=17.0,
        ),
    )

    resolution = resolve_reference_range(result)

    assert resolution.source == RangeSource.REPORT
    assert resolution.reference_range == result.reference_range
    assert resolution.critical_low is None
    assert resolution.critical_high is None


def test_known_test_name_falls_back_to_knowledge_base() -> None:
    result = LabResult(
        test_name="Hb",
        value=9.8,
    )

    resolution = resolve_reference_range(result)

    assert resolution.source == RangeSource.KNOWLEDGE_BASE
    assert resolution.reference_range is not None
    assert resolution.reference_range.low == 13.0
    assert resolution.reference_range.high == 17.0
    assert resolution.critical_low == 7.0
    assert resolution.critical_high == 20.0


def test_unknown_test_name_returns_unknown_resolution() -> None:
    result = LabResult(
        test_name="Ferritin",
        value=200.0,
    )

    resolution = resolve_reference_range(result)

    assert resolution.source == RangeSource.UNKNOWN
    assert resolution.reference_range is None
    assert resolution.critical_low is None
    assert resolution.critical_high is None


def test_report_reference_range_overrides_knowledge_base() -> None:
    result = LabResult(
        test_name="Hb",
        value=9.8,
        reference_range=ReferenceRange(
            low=12.0,
            high=18.0,
        ),
    )

    resolution = resolve_reference_range(result)

    assert resolution.source == RangeSource.REPORT
    assert resolution.reference_range.low == 12.0
    assert resolution.reference_range.high == 18.0
