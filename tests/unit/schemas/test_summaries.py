import pytest
from pydantic import ValidationError

from mediscan.schemas import (
    DietaryConsideration,
    DoctorSummary,
    PatientSummary,
    SpecialistSuggestion,
)


def test_valid_summaries():
    assert PatientSummary(text="All values look typical.").key_points == []
    assert DoctorSummary(text="Unremarkable panel.").clinical_notes == []


def test_empty_summary_text_rejected():
    with pytest.raises(ValidationError):
        PatientSummary(text="")
    with pytest.raises(ValidationError):
        DoctorSummary(text="   ")


def test_dietary_consideration_is_informational_only():
    d = DietaryConsideration(suggestion="Iron-rich foods are often discussed.")
    assert d.informational_only is True


def test_informational_only_cannot_be_disabled():
    # Constitutional guarantee: this object cannot exist with False
    with pytest.raises(ValidationError):
        DietaryConsideration(suggestion="x", informational_only=False)


def test_specialist_requires_reason():
    with pytest.raises(ValidationError):
        SpecialistSuggestion(specialty="Hematologist", reason="")


def test_empty_specialty_rejected():
    with pytest.raises(ValidationError):
        SpecialistSuggestion(specialty="", reason="Abnormal counts")


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        PatientSummary(text="ok", mood="cheerful")
