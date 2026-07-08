"""Medical reasoning schemas.

WHY THIS FILE EXISTS
    Parsing extracts raw laboratory observations. Before those observations
    can be judged, the medical engine must decide which reference range
    applies AND which critical thresholds (if any) guard it. These schemas
    represent that deterministic resolution and record its provenance for
    explainability — they perform no medical judgment themselves.

DECISION #023
    A report owns its printed normal range, but reports never print the
    life-threatening "critical" thresholds. Those come from the curated
    knowledge base. So a resolution may carry a normal range from one place
    (the report) and critical thresholds from another (the KB) — and the
    schema records each provenance separately instead of pretending a single
    `source` covers both.
"""

from enum import StrEnum

from pydantic import Field, computed_field

from mediscan.schemas.base import MediScanModel
from mediscan.schemas.labs import AbnormalDirection, ReferenceRange, Severity


class RangeSource(StrEnum):
    """Where a resolved value (a range or a threshold) originated."""

    REPORT = "report"
    KNOWLEDGE_BASE = "knowledge_base"
    UNKNOWN = "unknown"


class CriticalThresholds(MediScanModel):
    """The critical (life-threatening) thresholds for one lab value (#023).

    Grouped as ONE concept so future work (RC2 age/sex/pregnancy-specific
    thresholds) can extend this object instead of adding loose fields to
    RangeResolution. `low` means "at or below this is critical"; `high`
    means "at or above this is critical". Either may be absent.

    `source` is DERIVED, not stored: in RC1 critical thresholds only ever
    come from the KB (reports don't print them), so any threshold present is
    KNOWLEDGE_BASE and none means UNKNOWN. Deriving it means the source can
    never drift out of sync with the numbers.
    """

    low: float | None = Field(
        default=None,
        allow_inf_nan=False,
        description="Value at/below which the result is critical, if known.",
    )
    high: float | None = Field(
        default=None,
        allow_inf_nan=False,
        description="Value at/above which the result is critical, if known.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def source(self) -> RangeSource:
        """Provenance of the thresholds, derived from whether any exist."""
        if self.low is None and self.high is None:
            return RangeSource.UNKNOWN
        return RangeSource.KNOWLEDGE_BASE


class RangeResolution(MediScanModel):
    """The resolved reference range + critical thresholds for one lab value.

    The normal range and the critical thresholds can come from different
    places (#023), so their provenance is recorded separately:
    `reference_range_source` for the range, `critical_thresholds.source`
    (derived) for the thresholds.
    """

    reference_range: ReferenceRange | None = Field(
        default=None,
        description="The effective normal range used for banding, or None.",
    )
    reference_range_source: RangeSource = Field(
        description="Where the normal range came from (report / KB / unknown).",
    )
    critical_thresholds: CriticalThresholds = Field(
        default_factory=CriticalThresholds,
        description="Absolute critical thresholds, with derived provenance.",
    )


class SeverityAssessment(MediScanModel):
    """A pure, immutable judgment about one lab value (decision #021).

    Self-contained audit record: which test, what value, our conclusion,
    and the range/thresholds we judged against. The parser's LabResult is
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
        description="The range/thresholds used and where they came from."
    )
