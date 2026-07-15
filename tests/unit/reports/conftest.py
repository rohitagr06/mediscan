"""Shared fixtures for the report-renderer tests (Sprint 8.3/8.4).

conftest.py is special: pytest imports it automatically and makes the
fixtures defined here available to EVERY test file in this directory,
with no import statement. That's the idiomatic way to share a fixture
across files — cross-file `from tests... import` does not work, because
pytest puts each test file's own directory on sys.path, not the repo root.
"""

import pytest

from mediscan.schemas.coverage import (
    AcknowledgeClass,
    AcknowledgedTest,
    CoverageResult,
)
from mediscan.schemas.labs import (
    AbnormalDirection,
    LabResult,
    ReferenceRange,
    Severity,
)
from mediscan.schemas.medical import (
    RangeResolution,
    RangeSource,
    SeverityAssessment,
)
from mediscan.schemas.report import AnalysisReport
from mediscan.schemas.summaries import DoctorSummary, PatientSummary
from mediscan.schemas.urgency import UrgencyAssessment, UrgencyLevel


def make_assessment(
    name: str,
    value: float,
    severity: Severity | None,
    direction: AbnormalDirection | None = None,
) -> SeverityAssessment:
    """Build a valid SeverityAssessment with a report-sourced range.

    A plain function (not a fixture) so tests that build their own custom
    reports can call it directly; the `full_report` fixture uses it too.
    """
    return SeverityAssessment(
        test_name=name,
        value=value,
        severity=severity,
        abnormal_direction=direction,
        range_resolution=RangeResolution(
            reference_range=ReferenceRange(low=13.0, high=17.0),
            reference_range_source=RangeSource.REPORT,
        ),
    )


def build_full_report() -> AnalysisReport:
    """A representative report exercising every section of the renderer."""
    return AnalysisReport(
        lab_results=[
            LabResult(
                test_name="Hemoglobin",
                value=9.8,
                unit="g/dL",
                reference_range=ReferenceRange(low=13.0, high=17.0),
            ),
            LabResult(
                test_name="LDL Cholesterol",
                value=180.0,
                unit="mg/dL",
                reference_range=ReferenceRange(high=100.0),  # one-sided
            ),
        ],
        coverage=CoverageResult(
            assessed=[
                make_assessment(
                    "Hemoglobin", 9.8, Severity.HIGH, AbnormalDirection.LOW
                ),
                make_assessment(
                    "LDL Cholesterol",
                    180.0,
                    Severity.MODERATE,
                    AbnormalDirection.HIGH,
                ),
            ],
            acknowledged=[
                AcknowledgedTest(
                    test_name="Vitamin D",
                    value=18.0,
                    unit="ng/mL",
                    reference_range=ReferenceRange(low=30.0, high=100.0),
                    classification=AcknowledgeClass.NUMERIC,
                ),
                AcknowledgedTest(
                    test_name="PSA",
                    value=250.0,
                    classification=AcknowledgeClass.SENSITIVE,
                ),
            ],
            unparsed=["?? garbled line 3 ??"],
        ),
        urgency=UrgencyAssessment(
            level=UrgencyLevel.URGENT,
            reasons=["Hemoglobin is highly abnormal (9.8 g/dL, low)"],
            contributing_tests=["Hemoglobin"],
        ),
        patient_summary=PatientSummary(
            text="Your hemoglobin is low.", key_points=["See a doctor promptly."]
        ),
        doctor_summary=DoctorSummary(
            text="Marked microcytic pattern.", clinical_notes=["Hb 9.8 g/dL"]
        ),
    )


@pytest.fixture
def full_report() -> AnalysisReport:
    """The shared full report, available to any test that names it."""
    return build_full_report()


@pytest.fixture
def assessment_factory():
    """Expose make_assessment as a fixture (factory pattern).

    Returning the FUNCTION itself lets a test call it with its own
    arguments — the way to share a helper across files without importing
    conftest (which isn't an importable module under pytest's default mode).
    """
    return make_assessment
