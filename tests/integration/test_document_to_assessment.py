"""Integration test: a document becomes a medical assessment (task 4.10).

This is the Sprint-4 milestone in one file: the first test where a whole
*document* turns into a *medical verdict*. It exercises the full
deterministic chain that Sprints 2-4 built, with ZERO AI involved:

    text  ->  parse (extraction/parser)
          ->  resolve reference ranges (medical/ranges + normalization + KB)
          ->  severity per value (medical/severity)
          ->  one urgency roll-up for the report (medical/urgency)

There are two layers:

1. A TEXT-driven test that always runs. It feeds the exact rows that
   tests/fixtures/generate.py plants into cbc_report.pdf, so the medical
   chain is covered everywhere (including CI without native OCR libs).

2. A true end-to-end test (skipped when PyMuPDF is absent) that reads the
   REAL cbc_report.pdf through the ingestion + extraction pipeline and
   runs the same medical chain on the extracted text.

A NOTE ON WHAT THIS PROVES ABOUT RANGES
    Every row in a real report prints its own reference range, and the
    parser (decision #018) only recognizes rows that do. Range resolution
    is report-first, so the REPORT range drives normal/mild/moderate/high
    banding. But under decision #023 the KB's critical thresholds are now
    MERGED into report-ranged values (when they sit outside the report
    range), so a genuinely critical value still reaches CRITICAL end to end
    — see test_pipeline_reaches_critical_with_a_report_range below. The CBC
    fixture happens to contain no critical values, so its verdict is
    Consult Soon; the critical path is proven by its own regression test.
"""

from pathlib import Path

import pytest

from mediscan.extraction.parser import parse_lab_text
from mediscan.medical.severity import assess_results
from mediscan.medical.urgency import assess_urgency
from mediscan.schemas import AbnormalDirection, Severity, UrgencyLevel

FIXTURES = Path("tests/fixtures/files")

# The exact CBC rows generate.py plants in cbc_report.pdf. Keeping them
# here (rather than reading the PDF) lets the medical chain be tested with
# no native OCR/PDF dependency.
CBC_TEXT = """\
Complete Blood Count (CBC)
Hemoglobin 9.8 g/dL 13.0 - 17.0 L
Total Leukocyte Count 11.2 10^3/uL 4.0 - 11.0 H
Platelet Count 250 10^3/uL 150 - 410
Hematocrit 31.2 % 40 - 50 L
MCV 84.5 fL 83 - 101
SYNTHETIC DOCUMENT FOR SOFTWARE TESTING - NOT A REAL REPORT
"""

# The known-correct verdict for each CBC row, computed by hand and verified:
#   value vs its REPORT range, banded by the percentage rule (Option A).
EXPECTED_SEVERITY = {
    "Hemoglobin": (Severity.MODERATE, AbnormalDirection.LOW),  # 9.8 vs 13-17
    "Total Leukocyte Count": (Severity.MILD, AbnormalDirection.HIGH),  # 11.2 vs 4-11
    "Platelet Count": (Severity.NORMAL, None),  # 250 vs 150-410
    "Hematocrit": (Severity.MODERATE, AbnormalDirection.LOW),  # 31.2 vs 40-50
    "MCV": (Severity.NORMAL, None),  # 84.5 vs 83-101
}


def _assert_expected_cbc_verdict(assessments, urgency):
    """Assert the medical verdict matches the known CBC result.

    Looks up by test name (a dict), so it is robust to extra rows the
    parser might pick up and to ordering.
    """
    by_name = {a.test_name: a for a in assessments}

    for test_name, (severity, direction) in EXPECTED_SEVERITY.items():
        assert test_name in by_name, f"{test_name} was not parsed/assessed"
        got = by_name[test_name]
        assert got.severity is severity, f"{test_name}: {got.severity} != {severity}"
        assert (
            got.abnormal_direction is direction
        ), f"{test_name}: direction {got.abnormal_direction} != {direction}"

    # None of the CBC fixture's values is past a critical threshold, so none
    # is CRITICAL (the critical PATH is proven separately, below).
    assert all(a.severity is not Severity.CRITICAL for a in assessments)

    # Worst finding is MODERATE -> the whole report is Consult Soon.
    assert urgency.level is UrgencyLevel.CONSULT_SOON
    # The two moderate findings drove the level; the mild one did not.
    assert "Hemoglobin" in urgency.contributing_tests
    assert "Hematocrit" in urgency.contributing_tests
    assert "Total Leukocyte Count" not in urgency.contributing_tests
    # Explainability is mandatory (schema guarantees >= 1 reason).
    assert urgency.reasons


def test_cbc_text_becomes_expected_assessment():
    """Text of the CBC panel -> parse -> severity -> urgency, end to end."""
    outcome = parse_lab_text(CBC_TEXT)

    # The 5 lab rows parse; the two header lines are preserved as unparsed
    # (recorded, never silently dropped).
    assert len(outcome.results) == 5
    assert len(outcome.unparsed_lines) == 2

    assessments = assess_results(outcome.results)
    urgency = assess_urgency(assessments)

    _assert_expected_cbc_verdict(assessments, urgency)


def test_cbc_pdf_document_to_assessment_end_to_end():
    """The real milestone: a PDF file in -> a medical verdict out.

    Skipped where PyMuPDF is unavailable; runs the true ingestion +
    extraction pipeline, then the same medical chain, on the actual
    cbc_report.pdf fixture.
    """
    pytest.importorskip("pymupdf")

    from mediscan.ingestion.storage import SecureUploadDir
    from mediscan.ingestion.validators import validate_upload
    from mediscan.ocr.pymupdf_engine import PyMuPdfEngine
    from mediscan.schemas import DocumentType

    source = FIXTURES / "cbc_report.pdf"

    # front door -> secure storage -> extraction, exactly as production will
    assert validate_upload(source) is DocumentType.PDF_TEXT
    with SecureUploadDir() as upload_dir:
        stored = upload_dir.store(source)
        extracted = PyMuPdfEngine().extract(stored)

    # the document's text now flows through the medical chain
    outcome = parse_lab_text(extracted.full_text)
    assessments = assess_results(outcome.results)
    urgency = assess_urgency(assessments)

    _assert_expected_cbc_verdict(assessments, urgency)


def test_pipeline_reaches_critical_with_a_report_range():
    """Regression test for decision #023 (the safety fix).

    A report line that prints its OWN range but carries a critically low
    value must still reach CRITICAL -> Seek Immediate Care, because the KB's
    critical threshold is merged into the report-ranged value. Before #023
    this value banded as HIGH -> Urgent, under-warning on an emergency.

    If someone ever removes the merge from resolve_reference_range(), this
    test fails immediately.
    """
    # Hemoglobin 3.0 with a printed 13.0-17.0 range. KB critical_low is 7.0.
    text = "Hemoglobin 3.0 g/dL 13.0 - 17.0 L"

    outcome = parse_lab_text(text)
    assert len(outcome.results) == 1

    assessments = assess_results(outcome.results)
    urgency = assess_urgency(assessments)

    hb = assessments[0]
    assert hb.severity is Severity.CRITICAL
    assert hb.abnormal_direction is AbnormalDirection.LOW
    # the normal range still came from the report; the critical came from KB
    assert hb.range_resolution.reference_range_source.value == "report"
    assert hb.range_resolution.critical_thresholds.low == 7.0
    # and the whole report is escalated to the most urgent level
    assert urgency.level is UrgencyLevel.IMMEDIATE
