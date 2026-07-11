"""Integration: a document becomes a full AnalysisReport (Sprint 7.5).

The Sprint-7 milestone in one file — the whole pipeline, one call, one master
object. Two layers, mirroring test_document_to_assessment.py:

1. A TEXT-driven test that always runs: analyze_text on the exact CBC rows
   the fixture contains, so the orchestration is covered everywhere (incl. CI
   without PyMuPDF).
2. A true end-to-end test (skipped when PyMuPDF is absent) that drives
   analyze_document on the REAL cbc_report.pdf.

Both use providers=[] (deterministic path — no AI, no keys) and a no-op
retriever (no vector DB), so they are fast and offline. Grounding and the real
model are covered by the RAG suite; this file proves the WIRING.
"""

from pathlib import Path

import pytest

from mediscan.orchestration import analyze_text
from mediscan.schemas import AnalysisReport, Severity, UrgencyLevel

FIXTURES = Path("tests/fixtures/files")

# The exact CBC rows generate.py plants in cbc_report.pdf (same as the
# Sprint-4 integration test). Two non-lab lines (header + sentinel) become
# unparsed — recorded, never dropped.
CBC_TEXT = """\
Complete Blood Count (CBC)
Hemoglobin 9.8 g/dL 13.0 - 17.0 L
Total Leukocyte Count 11.2 10^3/uL 4.0 - 11.0 H
Platelet Count 250 10^3/uL 150 - 410
Hematocrit 31.2 % 40 - 50 L
MCV 84.5 fL 83 - 101
SYNTHETIC DOCUMENT FOR SOFTWARE TESTING - NOT A REAL REPORT
"""


def _no_retrieve(_query):
    return []


def _assert_cbc_report(report: AnalysisReport) -> None:
    """The known-correct AnalysisReport for the CBC fixture."""
    assert isinstance(report, AnalysisReport)

    # coverage: all 5 CBC rows are Tier-A (assessed), none acknowledged, and
    # the 2 non-lab lines are preserved as unparsed (accounted for, not lost).
    assert report.coverage is not None
    assessed = {a.test_name for a in report.coverage.assessed}
    assert {
        "Hemoglobin",
        "Total Leukocyte Count",
        "Platelet Count",
        "Hematocrit",
        "MCV",
    } <= assessed
    assert report.coverage.acknowledged == []
    assert report.coverage.unparsed  # header + sentinel recorded

    # verdict: worst finding is MODERATE -> Consult Soon; the two moderate
    # findings drove it, the mild TLC did not; nothing critical.
    assert report.urgency is not None
    assert report.urgency.level is UrgencyLevel.CONSULT_SOON
    assert "Hemoglobin" in report.urgency.contributing_tests
    assert "Hematocrit" in report.urgency.contributing_tests
    assert "Total Leukocyte Count" not in report.urgency.contributing_tests
    assert all(a.severity is not Severity.CRITICAL for a in report.coverage.assessed)

    # explanations were assembled (deterministic templates on the no-AI path)
    assert report.patient_summary is not None and report.patient_summary.text
    assert report.doctor_summary is not None

    # confidence + audit trail present and sane
    assert report.confidence is not None
    assert 0.0 <= report.confidence.overall <= 1.0
    assert report.metadata is not None
    assert report.metadata.duration_ms is not None and report.metadata.duration_ms >= 0
    assert report.disclaimer  # present by construction


def test_cbc_text_becomes_a_full_report():
    """Text -> analyze_text -> a complete AnalysisReport."""
    report = analyze_text(CBC_TEXT, providers=[], retrieve_fn=_no_retrieve)
    _assert_cbc_report(report)


def test_cbc_pdf_document_to_report_end_to_end():
    """The milestone: a PDF file in -> a full AnalysisReport out.

    Skipped where PyMuPDF is unavailable (CI, cloud sandbox); runs the true
    ingestion + extraction front, then the whole pipeline, on the real fixture.
    """
    pytest.importorskip("pymupdf")

    from mediscan.orchestration import analyze_document

    source = FIXTURES / "cbc_report.pdf"
    report = analyze_document(source, providers=[], retrieve_fn=_no_retrieve)
    _assert_cbc_report(report)
