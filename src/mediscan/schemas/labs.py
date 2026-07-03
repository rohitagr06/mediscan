from enum import StrEnum

from pydantic import BaseModel, model_validator


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
    low: float | None = None
    high: float | None = None

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
