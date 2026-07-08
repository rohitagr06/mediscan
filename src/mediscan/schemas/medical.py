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
from mediscan.schemas.labs import AbnormalDirection, ReferenceRange, Severity


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


class SeverityAssessment(MediScanModel):
    """A pure, immutable judgment about one lab value (decision #021).

    Self-contained audit record: which test, what value, our conclusion,
    and the range/source we judged against. The parser's LabResult is
    never mutated — this is a NEW value produced beside it.
    """

    test_name: str = Field(min_length=1, description="Test this judgment is about.")
    # allow_inf_nan=False for consistency with the #012 hardening: this
    # value always originates from an already-validated LabResult.value,
    # so it's defense-in-depth, but every numeric field in MediScan bans
    # NaN/Infinity so the rule holds uniformly across the codebase.
    value: float = Field(
        allow_inf_nan=False, description="The value that was assessed."
    )
    severity: Severity | None = Field(
        default=None, description="Assigned band; None means un-assessable (no range)."
    )
    abnormal_direction: AbnormalDirection | None = Field(
        default=None, description="Which way the value is abnormal, if any."
    )
    range_resolution: RangeResolution = Field(
        description="The range used and where it came from (provenance)."
    )
