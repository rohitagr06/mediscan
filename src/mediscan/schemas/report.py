from pydantic import Field

from mediscan.schemas.base import MediScanModel
from mediscan.schemas.confidence import ConfidenceBreakdown, ProcessingMetadata
from mediscan.schemas.labs import LabResult
from mediscan.schemas.summaries import (
    DietaryConsideration,
    DoctorSummary,
    PatientSummary,
    SpecialistSuggestion,
)
from mediscan.schemas.urgency import UrgencyAssessment

DEFAULT_DISCLAIMER = (
    "MediScan is an informational tool and does not provide medical advice, "
    "diagnosis, or treatment. Always consult a qualified healthcare professional."
)


class AnalysisReport(MediScanModel):
    """The master schema: every MediScan pipeline run produces exactly one of these.

    UI rendering, PDF generation, tests, evaluations, and the future RC2
    database layer all consume this object. Change it here, and everything
    stays consistent.
    """

    lab_results: list[LabResult] = Field(
        default_factory=list,
        description="All lab rows extracted from the document.",
    )
    urgency: UrgencyAssessment | None = Field(
        default=None,
        description="Deterministic urgency assessment; None until the engine runs.",
    )
    patient_summary: PatientSummary | None = Field(
        default=None, description="Plain-language summary for the patient."
    )
    doctor_summary: DoctorSummary | None = Field(
        default=None, description="Clinically oriented summary for a physician."
    )
    dietary_considerations: list[DietaryConsideration] = Field(
        default_factory=list,
        description="Informational-only dietary and lifestyle considerations.",
    )
    specialist_suggestions: list[SpecialistSuggestion] = Field(
        default_factory=list,
        description="Suggested specialist categories with reasons.",
    )
    confidence: ConfidenceBreakdown | None = Field(
        default=None,
        description="Hybrid confidence scores; None means not yet scored.",
    )
    metadata: ProcessingMetadata | None = Field(
        default=None, description="Audit trail of the processing run."
    )
    disclaimer: str = Field(
        default=DEFAULT_DISCLAIMER,
        min_length=1,
        description="Medical disclaimer; present on every report by construction.",
    )
