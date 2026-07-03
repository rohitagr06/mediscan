"""Lab-result schemas: the shape of one row of a laboratory report.

WHY THIS FILE EXISTS
    A line like "Hemoglobin  9.8  g/dL  (13.0 - 17.0)  L" on a printed
    report becomes a validated `LabResult` object here. Every later stage
    (severity engine, summaries, PDF) consumes these objects, so the rules
    in this file are the single source of truth for what a lab value IS.

KEY DESIGN DECISIONS ENFORCED HERE
    - severity=None means "not yet assessed" and is DIFFERENT from
      Severity.NORMAL ("assessed and fine"). Unknown must never look good.
    - NaN/Infinity and booleans are rejected as numeric values (#012):
      they are always signs of upstream garbage, never real measurements.
    - A result claiming to be normal AND abnormally low/high at the same
      time is contradictory and impossible to construct.
"""

from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from mediscan.schemas.base import MediScanModel
from mediscan.schemas.confidence import Score


class Severity(StrEnum):
    """How far outside its reference range a lab value sits.

    A StrEnum is a fixed menu of allowed string values. Using an enum
    (instead of a plain string) means a typo like "criticl" is an instant
    error, and every possible severity is listed in exactly one place.
    """

    NORMAL = "normal"
    MILD = "mild"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class AbnormalDirection(StrEnum):
    """Which side of the reference range an abnormal value falls on."""

    LOW = "low"  # value is below the reference range
    HIGH = "high"  # value is above the reference range


def _reject_bool(value: object) -> object:
    """Refuse booleans before Pydantic can coerce them into numbers.

    In Python, True is literally the number 1 (bool is a subclass of int),
    so without this guard `value=True` would silently become the lab value
    1.0 — data corruption with no error. This runs in mode="before", i.e.
    BEFORE type coercion, while the boolean is still recognisable.

    The leading underscore in the name is Python convention for "internal
    helper — not part of this module's public interface".
    """
    if isinstance(value, bool):
        raise ValueError("a boolean is not a valid numeric value")
    return value  # returning the value unchanged means "no objection"


class ReferenceRange(MediScanModel):
    """The healthy interval for a test, e.g. 13.0-17.0 g/dL.

    Both bounds are optional because real reports print one-sided ranges
    like "< 200" (only an upper bound) — but at least one must exist,
    and when both exist, low must be strictly below high.
    """

    # "float | None = None" reads as: a decimal number, OR None (missing),
    # and it defaults to None when not provided.
    # allow_inf_nan=False rejects the special float values NaN/Infinity.
    low: float | None = Field(
        default=None,
        allow_inf_nan=False,
        description="Lower bound of the reference range, if given.",
    )
    high: float | None = Field(
        default=None,
        allow_inf_nan=False,
        description="Upper bound of the reference range, if given.",
    )

    # Attach the boolean guard to both bounds. field_validator returns a
    # decorator, which we apply to the shared helper function directly —
    # this reuses one function instead of copy-pasting it per model.
    _no_bool_bounds = field_validator("low", "high", mode="before")(_reject_bool)

    @model_validator(mode="after")
    def reference_bounds(self):
        """Cross-field rules that need to see the WHOLE object.

        mode="after" means: run this once all individual fields have
        already passed their own checks. Raising ValueError here rejects
        the object; returning self approves it.
        """
        if self.low is None and self.high is None:
            raise ValueError("at least one of 'low' or 'high' must be set")
        if self.low is not None and self.high is not None:
            if self.low >= self.high:
                # f"..." is an f-string: the {curly} parts are replaced by
                # live values. Error messages that SHOW the bad values turn
                # a debugging session into a single glance.
                raise ValueError(
                    f"low ({self.low}) must be less than high ({self.high})"
                )
        return self


class LabResult(MediScanModel):
    """One measured value from a lab report, fully validated.

    Example:
        LabResult(
            test_name="Hemoglobin",
            value=9.8,
            unit="g/dL",
            reference_range=ReferenceRange(low=13.0, high=17.0),
            flag_in_report="L",
        )
    """

    # min_length / max_length bound the string size: an empty name is
    # meaningless, and a huge one is OCR garbage or abuse (#012).
    test_name: str = Field(
        min_length=1,
        max_length=200,
        description="Name of the laboratory analyte.",
    )
    value: float = Field(
        allow_inf_nan=False,
        description="Raw extracted biomarker measured value.",
    )
    unit: str | None = Field(
        default=None,
        max_length=50,
        description="Measurement unit for the biomarker.",
    )
    # A nested model: the range is itself a validated ReferenceRange.
    # None is allowed because some reports omit ranges — the knowledge
    # base supplies a fallback range later (Sprint 4).
    reference_range: ReferenceRange | None = Field(
        default=None, description="Reference range provided by the laboratory."
    )
    # None = "not yet assessed by the medical engine". This is deliberately
    # different from Severity.NORMAL — see the module docstring.
    severity: Severity | None = Field(
        default=None,
        description="Severity classification; None means not yet assessed.",
    )
    abnormal_direction: AbnormalDirection | None = Field(
        default=None,
        description="Direction of abnormality (low or high), if any.",
    )
    # What the document itself printed (e.g. "L", "H"). We keep the
    # document's claim separate from OUR conclusion — an audit-trail habit.
    flag_in_report: str | None = Field(
        default=None,
        max_length=20,
        description="Raw flag marker exactly as printed in the report.",
    )
    # Score is a reusable "float between 0.0 and 1.0" type defined in
    # confidence.py — the bounds rule lives in exactly one place (DRY).
    extraction_confidence: Score = Field(
        default=1.0,
        description="Confidence score for biomarker extraction.",
    )

    _no_bool_value = field_validator("value", mode="before")(_reject_bool)

    @model_validator(mode="after")
    def check_severity_consistency(self):
        """Forbid the self-contradictory state 'normal but abnormally low'."""
        if self.severity is Severity.NORMAL and self.abnormal_direction is not None:
            raise ValueError(
                f"inconsistent result for '{self.test_name}': severity is "
                f"'normal' but abnormal_direction is '{self.abnormal_direction}' "
                f"— a normal value cannot have an abnormal direction"
            )
        return self
