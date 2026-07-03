from enum import StrEnum

from pydantic import Field

from mediscan.schemas.base import MediScanModel


class UrgencyLevel(StrEnum):
    ROUTINE = "routine"
    CONSULT_SOON = "consult_soon"
    URGENT = "urgent"
    IMMEDIATE = "seek_immediate_care"


class UrgencyAssessment(MediScanModel):
    level: UrgencyLevel = Field(
        description="Overall urgency level for the report, deterministically derived."
    )
    reasons: list[str] = Field(
        min_length=1,
        description=(
            "Human-readable reasons explaining why this urgency level was chosen. "
            "At least one reason is mandatory: an unexplained urgency claim is "
            "not allowed anywhere in MediScan."
        ),
    )
    contributing_tests: list[str] = Field(
        default_factory=list,
        description="Names of the lab tests that drove this urgency level.",
    )
