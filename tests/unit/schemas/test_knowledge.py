"""Tests for the ReferenceRangeEntry knowledge-base schema."""

import pytest
from pydantic import ValidationError

from mediscan.schemas import ReferenceRangeEntry


def test_valid_entry():
    e = ReferenceRangeEntry(
        test_name="Hemoglobin",
        unit="g/dL",
        low=13.0,
        high=17.0,
        critical_low=7.0,
        critical_high=20.0,
        source="ref",
    )
    assert e.low == 13.0 and e.critical_low == 7.0


def test_entry_without_critical_thresholds_is_valid():
    e = ReferenceRangeEntry(test_name="MCV", low=83.0, high=101.0, source="ref")
    assert e.critical_low is None


def test_backwards_range_rejected():
    with pytest.raises(ValidationError):
        ReferenceRangeEntry(test_name="X", low=17.0, high=13.0, source="ref")


def test_critical_low_inside_range_rejected():
    # a critical-low must be BELOW the normal low, not inside the range
    with pytest.raises(ValidationError):
        ReferenceRangeEntry(
            test_name="X", low=13.0, high=17.0, critical_low=15.0, source="ref"
        )


def test_critical_high_inside_range_rejected():
    with pytest.raises(ValidationError):
        ReferenceRangeEntry(
            test_name="X", low=13.0, high=17.0, critical_high=15.0, source="ref"
        )


def test_source_is_mandatory():
    with pytest.raises(ValidationError):
        ReferenceRangeEntry(test_name="X", low=13.0, high=17.0, source="")


# --- one-sided + sex-aware entries (Sprint 6.5.5) ---


def test_range_bounds_one_sided_upper_and_lower():
    from mediscan.schemas import RangeBounds

    upper = RangeBounds(high=100.0)  # LDL "< 100"
    assert upper.low is None and upper.high == 100.0
    lower = RangeBounds(low=40.0)  # HDL "> 40"
    assert lower.low == 40.0 and lower.high is None


def test_range_bounds_needs_at_least_one_bound():
    from mediscan.schemas import RangeBounds

    with pytest.raises(ValidationError):
        RangeBounds()


def test_range_bounds_rejects_inverted_and_bad_criticals():
    from mediscan.schemas import RangeBounds

    with pytest.raises(ValidationError):
        RangeBounds(low=17.0, high=13.0)  # inverted
    with pytest.raises(ValidationError):
        RangeBounds(high=100.0, critical_low=5.0)  # critical_low but no low
    with pytest.raises(ValidationError):
        RangeBounds(low=13.0, high=17.0, critical_high=16.0)  # not above high


def test_entry_one_sided_default_is_valid():
    e = ReferenceRangeEntry(test_name="LDL Cholesterol", high=100.0, source="NCEP")
    assert e.default_bounds().high == 100.0
    assert e.default_bounds().low is None


def test_entry_with_male_female_blocks_and_no_default():
    e = ReferenceRangeEntry(
        test_name="Hemoglobin",
        male={"low": 13.0, "high": 17.0},
        female={"low": 12.0, "high": 15.0},
        source="Example Lab",
    )
    assert e.default_bounds() is None
    assert e.male.low == 13.0 and e.female.high == 15.0


def test_entry_without_default_or_both_sexes_is_rejected():
    with pytest.raises(ValidationError):
        # only a male block, no default and no female block -> not resolvable
        ReferenceRangeEntry(
            test_name="Hemoglobin", male={"low": 13.0, "high": 17.0}, source="X"
        )
