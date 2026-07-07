"""Medical reasoning schemas.

WHY THIS FILE EXISTS
    Parsing extracts raw laboratory observations. Before those
    observations can be evaluated, the medical engine must determine
    which reference range applies. These schemas represent that
    deterministic decision without performing any medical judgment.
"""

from enum import StrEnum

from pydantic import Field

from mediscan.schemas.base import MediScanModel
from mediscan.schemas.labs import ReferenceRange


class RangeSource(StrEnum):
    """Where the effective reference range originated."""

    REPORT = "report"
    KNOWLEDGE_BASE = "knowledge_base"
    UNKNOWN = "unknown"


class RangeResolution(MediScanModel):
    """The resolved reference range for a laboratory result."""

    reference_range: ReferenceRange | None = Field(
        default=None,
        description="The effective reference range used for evaluation.",
    )

    critical_low: float | None = Field(
        default=None,
        description="Critical low threshold, if available.",
    )

    critical_high: float | None = Field(
        default=None,
        description="Critical high threshold, if available.",
    )

    source: RangeSource = Field(
        description="Where the effective reference range originated.",
    )
