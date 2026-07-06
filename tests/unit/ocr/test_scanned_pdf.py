"""Tests for the scanned-PDF OCR path — hardening and error handling.

The page-cap and corrupt tests do NOT run real OCR (they fail before
recognition), so they are fast and unmarked. They need pymupdf to open
PDFs, hence importorskip.
"""

import pytest

pytest.importorskip("pymupdf")

from pathlib import Path  # noqa: E402

from mediscan.config import settings  # noqa: E402
from mediscan.ocr.exceptions import (  # noqa: E402
    CorruptDocumentError,
    DocumentTooLargeError,
)
from mediscan.ocr.scanned_pdf import ScannedPdfEngine  # noqa: E402

FIXTURES = Path("tests/fixtures/files")


def test_page_cap_rejects_oversized_pdf(monkeypatch):
    # Hardening (audit): a PDF over the page cap fails FAST — before any
    # page is rendered or OCR'd — so a hostile many-page PDF can't DoS us.
    monkeypatch.setattr(settings, "max_pdf_pages", 0)
    with pytest.raises(DocumentTooLargeError):
        ScannedPdfEngine().extract(FIXTURES / "scanned_cbc.pdf")


def test_corrupt_pdf_raises_corrupt_error():
    # The shared open_pdf helper converts PyMuPDF's raw failure into ours.
    with pytest.raises(CorruptDocumentError):
        ScannedPdfEngine().extract(FIXTURES / "corrupt.pdf")
