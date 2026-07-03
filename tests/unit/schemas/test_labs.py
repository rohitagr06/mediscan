"""Tests for mediscan.schemas.labs — the LabResult family.

HOW TO READ THESE TESTS
    Happy-path tests prove correct data gets through. Rejection tests use
    `with pytest.raises(ValidationError):` which INVERTS the pass rule:
    the code inside the block MUST raise that error — if it runs without
    complaint, the test FAILS. Every rejection test below guards a rule
    we decided on purpose (see docs/04-decision-log.md #011-#013).
"""

import pytest
from pydantic import ValidationError

from mediscan.schemas import (
    AbnormalDirection,
    LabResult,
    ReferenceRange,
    Severity,
)

# ---------- enums ----------


def test_severity_has_exactly_five_levels():
    assert [s.value for s in Severity] == [
        "normal",
        "mild",
        "moderate",
        "high",
        "critical",
    ]


def test_abnormal_direction_values():
    assert {d.value for d in AbnormalDirection} == {"low", "high"}


# ---------- ReferenceRange: happy paths ----------


def test_two_sided_range():
    r = ReferenceRange(low=13.0, high=17.0)
    assert (r.low, r.high) == (13.0, 17.0)


def test_one_sided_ranges_allowed():
    assert ReferenceRange(high=200.0).low is None
    assert ReferenceRange(low=0.5).high is None


# ---------- ReferenceRange: rejections ----------


def test_backwards_range_rejected():
    with pytest.raises(ValidationError):
        ReferenceRange(low=17.0, high=13.0)


def test_equal_bounds_rejected():
    with pytest.raises(ValidationError):
        ReferenceRange(low=13.0, high=13.0)


def test_empty_range_rejected():
    with pytest.raises(ValidationError):
        ReferenceRange()


def test_nan_and_inf_bounds_rejected():
    with pytest.raises(ValidationError):
        ReferenceRange(low=float("nan"), high=17.0)
    with pytest.raises(ValidationError):
        ReferenceRange(low=13.0, high=float("inf"))


def test_bool_bound_rejected():
    with pytest.raises(ValidationError):
        ReferenceRange(low=True, high=17.0)


# ---------- LabResult: happy paths ----------


def test_minimal_lab_result_defaults():
    lr = LabResult(test_name="Hemoglobin", value=9.8)
    assert lr.severity is None  # None means NOT YET ASSESSED, never "normal"
    assert lr.abnormal_direction is None
    assert lr.extraction_confidence == 1.0


def test_ocr_string_value_coerced_to_float():
    lr = LabResult(test_name="Hemoglobin", value="9.8")
    assert lr.value == 9.8
    assert isinstance(lr.value, float)


def test_flag_preserved_verbatim():
    lr = LabResult(test_name="Hb", value=9.8, flag_in_report="H*")
    assert lr.flag_in_report == "H*"


def test_nested_range_from_dict():
    lr = LabResult(
        test_name="Hb", value=9.8, reference_range={"low": 13.0, "high": 17.0}
    )
    assert isinstance(lr.reference_range, ReferenceRange)


# ---------- LabResult: rejections ----------


def test_empty_test_name_rejected():
    with pytest.raises(ValidationError):
        LabResult(test_name="", value=1.0)


def test_whitespace_only_test_name_rejected():
    with pytest.raises(ValidationError):
        LabResult(test_name="   ", value=1.0)


def test_oversized_test_name_rejected():
    with pytest.raises(ValidationError):
        LabResult(test_name="A" * 201, value=1.0)


def test_non_numeric_value_rejected():
    with pytest.raises(ValidationError):
        LabResult(test_name="Hb", value="lots")


def test_nan_and_inf_values_rejected():
    for evil in ("nan", "inf", "-inf"):
        with pytest.raises(ValidationError):
            LabResult(test_name="Hb", value=float(evil))


def test_bool_value_rejected():
    # bool would silently coerce to 1.0 — schema must refuse
    with pytest.raises(ValidationError):
        LabResult(test_name="Hb", value=True)


def test_confidence_out_of_bounds_rejected():
    with pytest.raises(ValidationError):
        LabResult(test_name="Hb", value=1.0, extraction_confidence=1.5)
    with pytest.raises(ValidationError):
        LabResult(test_name="Hb", value=1.0, extraction_confidence=-0.1)


def test_normal_severity_with_direction_contradiction_rejected():
    with pytest.raises(ValidationError):
        LabResult(
            test_name="Hb",
            value=15.0,
            severity=Severity.NORMAL,
            abnormal_direction=AbnormalDirection.LOW,
        )


def test_extra_field_rejected():
    # e.g. a hallucinated LLM field must be an error, never silently dropped
    with pytest.raises(ValidationError):
        LabResult(test_name="Hb", value=9.8, diagnosis="anemia")


# ---------- post-construction mutation (decision #013) ----------


def test_mutation_is_validated_not_bypassed():
    # validate_assignment=True: assignments re-run ALL validators
    lr = LabResult(test_name="Hb", value=9.8)
    with pytest.raises(ValidationError):
        lr.value = float("nan")
    with pytest.raises(ValidationError):
        lr.extraction_confidence = 47.0


def test_cannot_mutate_into_contradiction():
    lr = LabResult(
        test_name="Hb",
        value=9.8,
        severity=Severity.MILD,
        abnormal_direction=AbnormalDirection.LOW,
    )
    with pytest.raises(ValidationError):
        lr.severity = Severity.NORMAL  # contradicts the existing direction


def test_legitimate_enrichment_allowed():
    # the Sprint 4 medical-engine flow: assess, then set
    lr = LabResult(test_name="Hb", value=9.8)
    lr.severity = Severity.MODERATE
    lr.abnormal_direction = AbnormalDirection.LOW
    assert lr.severity is Severity.MODERATE
