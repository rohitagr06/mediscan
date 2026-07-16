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

from mediscan.schemas.ai import (
    ExplanationProvenance,
    ExplanationSource,
    LLMRequest,
    LLMResponse,
)
from mediscan.schemas.base import MediScanModel
from mediscan.schemas.confidence import (
    ConfidenceBreakdown,
    ProcessingMetadata,
    Score,
)
from mediscan.schemas.coverage import (
    AcknowledgeClass,
    AcknowledgedTest,
    AssessmentPolicy,
    AssessmentTier,
    CoverageResult,
)
from mediscan.schemas.documents import DocumentType, ExtractedDocument, PageText
from mediscan.schemas.extraction import ParseOutcome
from mediscan.schemas.knowledge import (
    KnowledgeSnippet,
    RangeBounds,
    ReferenceRangeEntry,
    TestKnowledge,
)
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
from mediscan.schemas.patient import PatientContext, Sex
from mediscan.schemas.report import DEFAULT_DISCLAIMER, AnalysisReport
from mediscan.schemas.summaries import (
    DietaryConsideration,
    DoctorSummary,
    LifestyleConsideration,
    PatientSummary,
    SpecialistSuggestion,
)
from mediscan.schemas.urgency import UrgencyAssessment, UrgencyLevel

__all__ = [
    "DEFAULT_DISCLAIMER",
    "AbnormalDirection",
    "AcknowledgeClass",
    "AcknowledgedTest",
    "AnalysisReport",
    "AssessmentPolicy",
    "AssessmentTier",
    "ConfidenceBreakdown",
    "CoverageResult",
    "DietaryConsideration",
    "LifestyleConsideration",
    "DoctorSummary",
    "DocumentType",
    "ExplanationProvenance",
    "ExplanationSource",
    "ExtractedDocument",
    "LabResult",
    "LLMRequest",
    "LLMResponse",
    "MediScanModel",
    "PageText",
    "ParseOutcome",
    "PatientContext",
    "PatientSummary",
    "ProcessingMetadata",
    "CriticalThresholds",
    "RangeBounds",
    "RangeResolution",
    "RangeSource",
    "ReferenceRange",
    "KnowledgeSnippet",
    "ReferenceRangeEntry",
    "TestKnowledge",
    "Score",
    "Severity",
    "SeverityAssessment",
    "Sex",
    "SpecialistSuggestion",
    "UrgencyAssessment",
    "UrgencyLevel",
]
