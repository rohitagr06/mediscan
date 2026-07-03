from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from mediscan.schemas.base import MediScanModel
from mediscan.schemas.confidence import Score


class Severity(StrEnum):
    NORMAL = "normal"
    MILD = "mild"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class AbnormalDirection(StrEnum):
    LOW = "low"
    HIGH = "high"


def _reject_bool(value: object) -> object:
    """Booleans coerce to 1.0/0.0 as floats — silent data corruption for a
    lab value. Reject them before coercion runs (security hardening #012)."""
    if isinstance(value, bool):
        raise ValueError("a boolean is not a valid numeric value")
    return value


class ReferenceRange(MediScanModel):
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

    _no_bool_bounds = field_validator("low", "high", mode="before")(_reject_bool)

    @model_validator(mode="after")
    def reference_bounds(self):
        if self.low is None and self.high is None:
            raise ValueError("at least one of 'low' or 'high' must be set")
        if self.low is not None and self.high is not None:
            if self.low >= self.high:
                raise ValueError(
                    f"low ({self.low}) must be less than high ({self.high})"
                )
        return self


class LabResult(MediScanModel):
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
    reference_range: ReferenceRange | None = Field(
        default=None, description="Reference range provided by the laboratory."
    )
    severity: Severity | None = Field(
        default=None,
        description="Severity classification; None means not yet assessed.",
    )
    abnormal_direction: AbnormalDirection | None = Field(
        default=None,
        description="Direction of abnormality (low or high), if any.",
    )
    flag_in_report: str | None = Field(
        default=None,
        max_length=20,
        description="Raw flag marker exactly as printed in the report.",
    )
    extraction_confidence: Score = Field(
        default=1.0,
        description="Confidence score for biomarker extraction.",
    )

    _no_bool_value = field_validator("value", mode="before")(_reject_bool)

    @model_validator(mode="after")
    def check_severity_consistency(self):
        if self.severity is Severity.NORMAL and self.abnormal_direction is not None:
            raise ValueError(
                f"inconsistent result for '{self.test_name}': severity is "
                f"'normal' but abnormal_direction is '{self.abnormal_direction}' "
                f"— a normal value cannot have an abnormal direction"
            )
        return self
