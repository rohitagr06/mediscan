"""Tests for the shared open_pdf helper (the 3x-refactor, audit)."""

import pytest

pytest.importorskip("pymupdf")

from pathlib import Path  # noqa: E402

from mediscan.ocr._pdf import open_pdf  # noqa: E402
from mediscan.ocr.exceptions import CorruptDocumentError  # noqa: E402

FIXTURES = Path("tests/fixtures/files")


def test_open_valid_pdf_returns_document():
    with open_pdf(FIXTURES / "cbc_report.pdf") as doc:
        assert len(doc) == 2


def test_open_corrupt_pdf_raises_our_error():
    with pytest.raises(CorruptDocumentError):
        open_pdf(FIXTURES / "corrupt.pdf")
