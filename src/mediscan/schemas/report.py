"""The master schema: one object representing one complete analysis.

WHY THIS FILE EXISTS
    Every MediScan pipeline run produces exactly one AnalysisReport.
    The UI renders it, the PDF generator prints it, tests assert on it,
    and the future RC2 database will store it. One schema, many consumers:
    change it here and every surface stays consistent.

DESIGN NOTES
    - Most fields default to None or an empty list: a report is built up
      stage by stage (extraction fills lab_results, the medical engine
      fills urgency, and so on). "Not filled yet" is always explicit.
    - The disclaimer has a default and can never be emptied: no code path
      can produce a report without it.
"""

from pydantic import Field

from mediscan.schemas.base import MediScanModel
from mediscan.schemas.confidence import ConfidenceBreakdown, ProcessingMetadata
from mediscan.schemas.coverage import CoverageResult
from mediscan.schemas.labs import LabResult
from mediscan.schemas.summaries import (
    DietaryConsideration,
    DoctorSummary,
    PatientSummary,
    SpecialistSuggestion,
)
from mediscan.schemas.urgency import UrgencyAssessment

# A module-level CONSTANT (UPPER_CASE name by convention). The PDF
# generator and UI import this same constant, so the disclaimer wording
# can never drift between different surfaces of the product.
DEFAULT_DISCLAIMER = (
    "MediScan is an informational tool and does not provide medical advice, "
    "diagnosis, or treatment. Always consult a qualified healthcare professional."
)


class AnalysisReport(MediScanModel):
    """Everything MediScan concluded about one uploaded document."""

    lab_results: list[LabResult] = Field(
        default_factory=list,
        description="All lab rows extracted from the document (raw audit rows).",
    )
    # The Sprint-6.5 coverage split carried into the final report: which tests
    # were ASSESSED (graded), ACKNOWLEDGED (shown, not graded — out-of-scope or
    # sensitive), and which lines were unparsed. None until coverage runs.
    coverage: CoverageResult | None = Field(
        default=None,
        description="Assessed/acknowledged/unparsed coverage split (#030).",
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
    # None here means "not yet scored" — see decision #011 in confidence.py.
    confidence: ConfidenceBreakdown | None = Field(
        default=None,
        description="Hybrid confidence scores; None means not yet scored.",
    )
    metadata: ProcessingMetadata | None = Field(
        default=None, description="Audit trail of the processing run."
    )
    # min_length=1 means the disclaimer can be replaced but never removed.
    disclaimer: str = Field(
        default=DEFAULT_DISCLAIMER,
        min_length=1,
        description="Medical disclaimer; present on every report by construction.",
    )
