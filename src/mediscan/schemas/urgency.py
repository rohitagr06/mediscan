"""Urgency schemas: how soon a doctor should be consulted, and WHY.

WHY THIS FILE EXISTS
    The urgency level is the single most consequential output MediScan
    shows a user. Two safety rules are enforced by the schema itself:

    1. The level must be one of exactly four allowed values (an enum —
       no invented levels possible).
    2. An assessment MUST carry at least one human-readable reason.
       An unexplained "URGENT" is forbidden by construction: this is the
       project's explainability requirement, enforced as physics rather
       than as a promise in documentation.
"""

from enum import StrEnum

from pydantic import Field

from mediscan.schemas.base import MediScanModel


class UrgencyLevel(StrEnum):
    """The four allowed urgency levels, mildest first."""

    ROUTINE = "routine"
    CONSULT_SOON = "consult_soon"
    URGENT = "urgent"
    IMMEDIATE = "seek_immediate_care"


class UrgencyAssessment(MediScanModel):
    """The overall urgency conclusion for one report."""

    level: UrgencyLevel = Field(
        description="Overall urgency level for the report, deterministically derived."
    )
    # On a LIST, min_length means "at least this many items" — so this
    # forbids an empty reasons list, not an empty string.
    reasons: list[str] = Field(
        min_length=1,
        description=(
            "Human-readable reasons explaining why this urgency level was "
            "chosen. At least one reason is mandatory: an unexplained "
            "urgency claim is not allowed anywhere in MediScan."
        ),
    )
    # default_factory=list builds a FRESH empty list for every object.
    # (A plain "default=[]" risks Python's infamous shared-mutable-default
    # trap, where many objects accidentally share one list.)
    contributing_tests: list[str] = Field(
        default_factory=list,
        description="Names of the lab tests that drove this urgency level.",
    )
