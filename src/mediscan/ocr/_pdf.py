"""Shared PDF-opening helper.

WHY THIS FILE EXISTS
    Three call sites (pymupdf_engine, router, scanned_pdf) each need to
    open a PDF and convert any failure into CorruptDocumentError. That
    try/except was duplicated three times; per the Sprint 2 retro
    tripwire ("third occurrence triggers the refactor"), it lives here
    once now. One place to fix, one place to test.
"""

from pathlib import Path

import pymupdf

from mediscan.ocr.exceptions import CorruptDocumentError


def open_pdf(path: Path) -> pymupdf.Document:
    """Open a PDF, turning any failure into our CorruptDocumentError."""
    try:
        return pymupdf.open(path)
    except Exception as err:
        raise CorruptDocumentError(
            f"PyMuPDF could not open the file ({type(err).__name__})"
        ) from err
