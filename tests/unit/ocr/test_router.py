"""Tests for the text-vs-scan router.

Uses the synthetic fixtures from tests/fixtures/files/: a known-text CBC
report, a known-empty "scanned" PDF, and a corrupt PDF. The monkeypatch
test proves the threshold is genuinely read from config, not decorative.
"""

import pytest

# The router imports PyMuPDF at module load; skip this whole file in
# environments that lack the library rather than erroring at collection.
pytest.importorskip("pymupdf")

from pathlib import Path  # noqa: E402

from mediscan.config import settings  # noqa: E402
from mediscan.ocr.exceptions import CorruptDocumentError  # noqa: E402
from mediscan.ocr.router import detect_document_type  # noqa: E402
from mediscan.schemas import DocumentType  # noqa: E402

FIXTURES = Path("tests/fixtures/files")


def test_text_pdf_routes_to_text():
    assert detect_document_type(FIXTURES / "cbc_report.pdf") is DocumentType.PDF_TEXT


def test_scanned_pdf_routes_to_scanned():
    assert (
        detect_document_type(FIXTURES / "scanned_report.pdf")
        is DocumentType.PDF_SCANNED
    )


def test_corrupt_pdf_raises_corrupt_error():
    with pytest.raises(CorruptDocumentError):
        detect_document_type(FIXTURES / "corrupt.pdf")


def test_threshold_is_read_from_config(monkeypatch):
    # With an absurd threshold, even the real CBC report must classify
    # as scanned — proving the knob is live, not decorative.
    monkeypatch.setattr(settings, "router_min_chars_per_page", 1_000_000)
    assert detect_document_type(FIXTURES / "cbc_report.pdf") is DocumentType.PDF_SCANNED
