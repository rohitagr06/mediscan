"""Patient context read from a report header (sex, and optionally age).

WHY THIS FILE EXISTS
    Some reference ranges differ by sex (Hemoglobin, Creatinine, Ferritin),
    so the medical engine needs to know the patient's sex to band those
    correctly. That sex is read FROM the report — never guessed.

    PatientContext lives in its OWN module (decision #030) because it will
    grow: pregnancy status, fasting state, collection time, menstrual phase,
    and sample type are all plausible future fields. Keeping it separate now
    means those additions don't bloat another schema file later.
"""

from enum import StrEnum

from pydantic import Field

from mediscan.schemas.base import MediScanModel


class Sex(StrEnum):
    """Biological sex as used for reference-range selection.

    UNKNOWN is a FIRST-CLASS value (#011): when the report doesn't state a
    sex, we record UNKNOWN and fall back conservatively — we never guess.
    """

    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class PatientContext(MediScanModel):
    """The patient facts that affect how results are interpreted.

    Attributes:
        sex: The patient's sex, or UNKNOWN when the report is silent.
        age: The patient's age in years, if the report states it. Optional —
            age-specific ranges are deferred (#027), but age is captured now
            because it is free to read and useful later.
    """

    sex: Sex = Field(
        default=Sex.UNKNOWN,
        description="Patient sex for sex-aware ranges; UNKNOWN if not stated.",
    )
    age: int | None = Field(
        default=None,
        ge=0,
        le=150,
        description="Patient age in years, if the report states it.",
    )
