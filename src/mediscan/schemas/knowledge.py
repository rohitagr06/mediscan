"""Knowledge-base schemas: validated reference-range facts.

WHY THIS FILE EXISTS
    The medical engine falls back to curated generalized adult reference
    ranges when a report omits its own. Those ranges are medical facts,
    so they are stored as reviewable JSON and VALIDATED at load time:
    a malformed entry (low >= high, a critical threshold on the wrong
    side of the normal bound) fails loudly on startup, never silently
    mis-ranging a value.
"""

from pydantic import Field, model_validator

from mediscan.schemas.base import MediScanModel


class ReferenceRangeEntry(MediScanModel):
    """One curated reference-range fact for a single lab test.

    test_name MUST match the canonical output of normalize_test_name so
    the engine's lookup succeeds. Critical thresholds are optional and,
    when present, must sit OUTSIDE the normal range (a critical-low is
    below the normal low; a critical-high is above the normal high).
    """

    test_name: str = Field(
        min_length=1, description="Canonical test name (matches normalization output)."
    )
    unit: str | None = Field(
        default=None, description="Canonical unit for this test, if any."
    )
    # allow_inf_nan=False rejects NaN/Infinity. Without it a NaN bound
    # would slip through the check_bounds comparison below (every
    # comparison with NaN is False), silently disabling that bound — an
    # "unknown masquerades as fine" hole (#011) hiding inside the KB.
    low: float = Field(
        allow_inf_nan=False, description="Lower bound of the normal adult range."
    )
    high: float = Field(
        allow_inf_nan=False, description="Upper bound of the normal adult range."
    )
    critical_low: float | None = Field(
        default=None,
        allow_inf_nan=False,
        description="Value at/below which the result is critical.",
    )
    critical_high: float | None = Field(
        default=None,
        allow_inf_nan=False,
        description="Value at/above which the result is critical.",
    )
    source: str = Field(
        min_length=1,
        description="Citation for these numbers — mandatory (no anonymous facts).",
    )

    @model_validator(mode="after")
    def check_bounds(self):
        if self.low >= self.high:
            raise ValueError(
                f"{self.test_name}: low ({self.low}) must be < high ({self.high})"
            )
        if self.critical_low is not None and self.critical_low >= self.low:
            raise ValueError(
                f"{self.test_name}: critical_low ({self.critical_low}) must be "
                f"below the normal low ({self.low})"
            )
        if self.critical_high is not None and self.critical_high <= self.high:
            raise ValueError(
                f"{self.test_name}: critical_high ({self.critical_high}) must be "
                f"above the normal high ({self.high})"
            )
        return self
