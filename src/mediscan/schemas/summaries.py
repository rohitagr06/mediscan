from typing import Literal

from pydantic import BaseModel, Field


class PatientSummary(BaseModel):
    text: str = Field(
        min_length=1,
        description="Plain-language summary of the report for the patient.",
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="Short bullet-style highlights in patient-friendly language.",
    )


class DoctorSummary(BaseModel):
    text: str = Field(
        min_length=1,
        description="Clinically oriented summary of the report for a physician.",
    )
    clinical_notes: list[str] = Field(
        default_factory=list,
        description="Concise clinical observations relevant to a physician.",
    )


class DietaryConsideration(BaseModel):
    suggestion: str = Field(
        min_length=1,
        description="Informational dietary or lifestyle consideration.",
    )
    rationale: str | None = Field(
        default=None,
        description="Grounded explanation of why this consideration is relevant.",
    )
    informational_only: Literal[True] = Field(
        default=True,
        description=(
            "Constitutional guarantee: dietary content is informational only, "
            "never medical advice. This field cannot be set to False."
        ),
    )


class SpecialistSuggestion(BaseModel):
    specialty: str = Field(
        min_length=1,
        description="Suggested specialist category, e.g. 'Hematologist'.",
    )
    reason: str = Field(
        min_length=1,
        description="Explanation of why this specialist category is suggested.",
    )
