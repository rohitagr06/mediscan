"""Shared fixtures. `sample_cbc_report` is the canonical synthetic report
(task 1.10) — a realistic fake CBC panel reused by tests in every sprint.
Entirely synthetic: no real patient data (decision #010)."""

import pytest

from mediscan.schemas import (
    AbnormalDirection,
    AnalysisReport,
    ConfidenceBreakdown,
    DietaryConsideration,
    DoctorSummary,
    LabResult,
    PatientSummary,
    ProcessingMetadata,
    ReferenceRange,
    Severity,
    SpecialistSuggestion,
    UrgencyAssessment,
    UrgencyLevel,
)


@pytest.fixture
def sample_cbc_report() -> AnalysisReport:
    return AnalysisReport(
        lab_results=[
            LabResult(
                test_name="Hemoglobin",
                value=9.8,
                unit="g/dL",
                reference_range=ReferenceRange(low=13.0, high=17.0),
                severity=Severity.MODERATE,
                abnormal_direction=AbnormalDirection.LOW,
                flag_in_report="L",
                extraction_confidence=0.94,
            ),
            LabResult(
                test_name="Total Leukocyte Count",
                value=11.2,
                unit="10^3/uL",
                reference_range=ReferenceRange(low=4.0, high=11.0),
                severity=Severity.MILD,
                abnormal_direction=AbnormalDirection.HIGH,
                flag_in_report="H",
                extraction_confidence=0.91,
            ),
            LabResult(
                test_name="Platelet Count",
                value=250.0,
                unit="10^3/uL",
                reference_range=ReferenceRange(low=150.0, high=410.0),
                severity=Severity.NORMAL,
                extraction_confidence=0.97,
            ),
        ],
        urgency=UrgencyAssessment(
            level=UrgencyLevel.CONSULT_SOON,
            reasons=[
                "Hemoglobin 9.8 g/dL is moderately below the reference range "
                "(13.0-17.0).",
                "Total Leukocyte Count is mildly elevated.",
            ],
            contributing_tests=["Hemoglobin", "Total Leukocyte Count"],
        ),
        patient_summary=PatientSummary(
            text="Your hemoglobin is lower than the typical range, which can "
            "be associated with anemia. A doctor can help find the cause.",
            key_points=["Hemoglobin below range", "Mildly elevated WBC"],
        ),
        doctor_summary=DoctorSummary(
            text="Moderate normocytic anemia pattern with mild leukocytosis; "
            "suggest clinical correlation.",
            clinical_notes=["Hb 9.8 g/dL (ref 13.0-17.0)", "TLC 11.2 (ref 4-11)"],
        ),
        dietary_considerations=[
            DietaryConsideration(
                suggestion="Iron-rich foods (e.g. spinach, legumes) are often "
                "discussed in the context of low hemoglobin.",
                rationale="Low hemoglobin can be associated with iron "
                "deficiency; only a doctor can confirm the cause.",
            )
        ],
        specialist_suggestions=[
            SpecialistSuggestion(
                specialty="Hematologist",
                reason="Abnormal red and white blood cell counts.",
            )
        ],
        confidence=ConfidenceBreakdown(
            ocr=0.96, extraction=0.92, validation=1.0, grounding=0.88, overall=0.93
        ),
        metadata=ProcessingMetadata(
            duration_ms=1834.2,
            models_used=["gemini-flash"],
            fallback_count=0,
            ocr_engine="pymupdf",
        ),
    )
