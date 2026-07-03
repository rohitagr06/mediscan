from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

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


class ReferenceRange(BaseModel):
    low: float | None = Field(
        default=None, description="Lower bound of the reference range, if given."
    )
    high: float | None = Field(
        default=None, description="Upper bound of the reference range, if given."
    )

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


class LabResult(BaseModel):
    test_name: str = Field(min_length=1, description="Name of the laboratory analyte.")
    value: float = Field(description="Raw extracted biomarker measured value.")
    unit: str | None = Field(
        default=None, description="Measurement unit for the biomarker."
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
        description="Raw flag marker exactly as printed in the report.",
    )
    extraction_confidence: Score = Field(
        default=1.0,
        description="Confidence score for biomarker extraction.",
    )

    @model_validator(mode="after")
    def check_severity_consistency(self):
        if self.severity is Severity.NORMAL and self.abnormal_direction is not None:
            raise ValueError(
                f"inconsistent result for '{self.test_name}': severity is "
                f"'normal' but abnormal_direction is '{self.abnormal_direction}' "
                f"— a normal value cannot have an abnormal direction"
            )
        return self
