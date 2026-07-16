"""Summary schemas: the human-facing text MediScan produces.

WHY THIS FILE EXISTS
    The same analysis is explained twice — once in plain language for the
    patient, once in clinical language for a doctor — plus informational
    dietary notes and specialist suggestions. These models define the shape
    of that text and hard-wire one safety guarantee: dietary content can
    NEVER present itself as medical advice (see DietaryConsideration).
"""

from typing import Literal

from pydantic import Field

from mediscan.schemas.base import MediScanModel


class PatientSummary(MediScanModel):
    """Plain-language explanation of the report for the patient."""

    text: str = Field(
        min_length=1,
        description="Plain-language summary of the report for the patient.",
    )
    key_points: list[str] = Field(
        default_factory=list,  # fresh list per object — see urgency.py note
        description="Short bullet-style highlights in patient-friendly language.",
    )


class DoctorSummary(MediScanModel):
    """Clinically oriented summary for a physician."""

    text: str = Field(
        min_length=1,
        description="Clinically oriented summary of the report for a physician.",
    )
    clinical_notes: list[str] = Field(
        default_factory=list,
        description="Concise clinical observations relevant to a physician.",
    )


class DietaryConsideration(MediScanModel):
    """One informational-only dietary or lifestyle note.

    THE CONSTITUTIONAL FIELD
        `informational_only` uses Literal[True], meaning the ONLY legal
        value is True. Passing False is a validation error — an object
        claiming to be dietary ADVICE cannot exist in this system. The
        safety rule is enforced by the type system, not by trust.
    """

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


class LifestyleConsideration(MediScanModel):
    """One informational-only lifestyle / daily-habit note.

    Same constitutional guarantee as DietaryConsideration: ``informational_only``
    is ``Literal[True]``, so a lifestyle note can never present itself as
    medical advice. Covers everyday habits — activity, sleep, stress, hydration.
    """

    suggestion: str = Field(
        min_length=1,
        description="Informational lifestyle or daily-habit consideration.",
    )
    rationale: str | None = Field(
        default=None,
        description="Grounded explanation of why this consideration is relevant.",
    )
    informational_only: Literal[True] = Field(
        default=True,
        description=(
            "Constitutional guarantee: lifestyle content is informational only, "
            "never medical advice. This field cannot be set to False."
        ),
    )


class SpecialistSuggestion(MediScanModel):
    """A suggested category of doctor to consult — always with a reason.

    The mandatory `reason` is the same explainability rule as in
    urgency.py: no unexplained recommendations, enforced by the schema.
    """

    specialty: str = Field(
        min_length=1,
        description="Suggested specialist category, e.g. 'Hematologist'.",
    )
    reason: str = Field(
        min_length=1,
        description="Explanation of why this specialist category is suggested.",
    )
