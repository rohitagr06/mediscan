"""MediScan master schema package.

Everything the pipeline produces or consumes is defined in this package.

WHAT THIS FILE DOES
    An __init__.py runs when the package is imported. By re-importing the
    important names here, we let the rest of the codebase write short
    imports like:

        from mediscan.schemas import LabResult

    instead of remembering which submodule each class lives in.

    __all__ is the package's official public list: it documents (and
    controls, for `from ... import *`) exactly what we consider public.
"""

from mediscan.schemas.base import MediScanModel
from mediscan.schemas.confidence import (
    ConfidenceBreakdown,
    ProcessingMetadata,
    Score,
)
from mediscan.schemas.documents import DocumentType, ExtractedDocument, PageText
from mediscan.schemas.extraction import ParseOutcome
from mediscan.schemas.knowledge import ReferenceRangeEntry
from mediscan.schemas.labs import (
    AbnormalDirection,
    LabResult,
    ReferenceRange,
    Severity,
)
from mediscan.schemas.medical import (
    CriticalThresholds,
    RangeResolution,
    RangeSource,
    SeverityAssessment,
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
    "MediScanModel",
    "AbnormalDirection",
    "AnalysisReport",
    "ConfidenceBreakdown",
    "DietaryConsideration",
    "DoctorSummary",
    "DocumentType",
    "ExtractedDocument",
    "LabResult",
    "PageText",
    "ParseOutcome",
    "PatientSummary",
    "ProcessingMetadata",
    "CriticalThresholds",
    "RangeResolution",
    "RangeSource",
    "ReferenceRange",
    "ReferenceRangeEntry",
    "Score",
    "Severity",
    "SeverityAssessment",
    "SpecialistSuggestion",
    "UrgencyAssessment",
    "UrgencyLevel",
]
