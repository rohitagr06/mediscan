"""MediScan master schema package.

Everything the pipeline produces or consumes is defined here.
Import from this package directly: `from mediscan.schemas import LabResult`.
"""

from mediscan.schemas.confidence import (
    ConfidenceBreakdown,
    ProcessingMetadata,
    Score,
)
from mediscan.schemas.labs import (
    AbnormalDirection,
    LabResult,
    ReferenceRange,
    Severity,
)
from mediscan.schemas.report import DEFAULT_DISCLAIMER, AnalysisReport
from mediscan.schemas.summaries import (
    DietaryConsideration,
    DoctorSummary,
    PatientSummary,
    SpecialistSuggestion,
)
from mediscan.schemas.urgency import UrgencyAssessment, UrgencyLevel

__all__ = [
    "DEFAULT_DISCLAIMER",
    "AbnormalDirection",
    "AnalysisReport",
    "ConfidenceBreakdown",
    "DietaryConsideration",
    "DoctorSummary",
    "LabResult",
    "PatientSummary",
    "ProcessingMetadata",
    "ReferenceRange",
    "Score",
    "Severity",
    "SpecialistSuggestion",
    "UrgencyAssessment",
    "UrgencyLevel",
]
