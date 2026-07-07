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
