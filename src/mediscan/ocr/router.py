"""Text-vs-scan routing for validated PDFs.

WHY THIS FILE EXISTS
    Two species of PDF look identical but need different handling.
    Born-digital PDFs (from lab software) contain real text characters —
    the PyMuPDF engine extracts them directly. Scanned PDFs contain only
    a photograph of the page — zero characters — and must go to OCR
    (Sprint 3). The validator cannot tell them apart (both are honest,
    safe PDFs); this router is the signpost at the fork.

HOW IT DECIDES
    It counts extractable characters per page. Real text pages carry
    hundreds; scans carry ~0 (plus occasional stray stamps/whitespace).
    The dividing line lives in config (router_min_chars_per_page) because
    it is a tunable judgment, not a law of nature.

CONSERVATIVE CHOICES
    - A zero-page PDF routes to PDF_SCANNED: "no text found" is exactly
      the case OCR exists for, and never worth crashing over.
    - Whitespace is stripped before counting: stray blanks are not
      evidence of text.
"""

from pathlib import Path

import pymupdf

from mediscan.config import settings
from mediscan.ocr.exceptions import CorruptDocumentError
from mediscan.schemas import DocumentType


def detect_document_type(path: Path) -> DocumentType:
    """Classify a validated PDF as born-digital text or a scan needing OCR.

    Rule: if the document's average extractable characters per page
    reach settings.router_min_chars_per_page, it is PDF_TEXT; below
    that, PDF_SCANNED. An average EXACTLY at the threshold classifies
    as PDF_TEXT. A zero-page document classifies as PDF_SCANNED
    (conservative: route "nothing found" toward OCR, never crash on
    a division by zero).

    OPTIMIZATION — early exit: "average >= threshold" is the same
    question as "total >= threshold * page_count" (multiply both sides
    by page_count). So we accumulate a running total and stop reading
    the moment it crosses that bar — a 200-page text report is decided
    within its first pages. The asymmetry is deliberate: PDF_TEXT can
    be proven early (later pages only ever ADD characters), but
    PDF_SCANNED can only be concluded after every page has been seen.

    Raises:
        CorruptDocumentError: the file could not be opened as a PDF.
    """
    try:
        document = pymupdf.open(path)
    except Exception as err:
        raise CorruptDocumentError(
            f"PyMuPDF could not open the file ({type(err).__name__})"
        ) from err

    with document:
        page_count = len(document)
        if page_count == 0:  # decided BEFORE any arithmetic on pages
            return DocumentType.PDF_SCANNED

        # total needed for the average to reach the threshold
        required_total = settings.router_min_chars_per_page * page_count

        total_chars = 0
        for page in document:
            total_chars += len(page.get_text().strip())
            if total_chars >= required_total:
                return DocumentType.PDF_TEXT  # proven early — stop reading

    return DocumentType.PDF_SCANNED
