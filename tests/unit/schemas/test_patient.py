"""Tests for the PatientContext schema and the Sex enum."""

import pytest
from pydantic import ValidationError

from mediscan.schemas import PatientContext, Sex


def test_defaults_are_unknown_sex_and_no_age():
    pc = PatientContext()
    assert pc.sex is Sex.UNKNOWN
    assert pc.age is None


def test_accepts_valid_sex_and_age():
    pc = PatientContext(sex=Sex.FEMALE, age=27)
    assert pc.sex is Sex.FEMALE
    assert pc.age == 27


def test_rejects_out_of_range_age():
    with pytest.raises(ValidationError):
        PatientContext(age=-1)
    with pytest.raises(ValidationError):
        PatientContext(age=200)


def test_rejects_unknown_sex_value():
    with pytest.raises(ValidationError):
        PatientContext(sex="martian")


def test_rejects_extra_fields():
    # MediScanModel forbids unknown fields (#012).
    with pytest.raises(ValidationError):
        PatientContext(sex=Sex.MALE, pregnancy=True)
