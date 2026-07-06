"""Text extraction from born-digital PDFs via PyMuPDF.

WHY THIS FILE EXISTS
    Lab software emits "text PDFs": the characters are really in the
    file, extractable perfectly and instantly — no OCR needed. This
    engine handles exactly that case. Scanned PDFs and photos go to the
    OCR engines in Sprint 3; the router (ocr/router.py) decides which
    path a document takes.

"""

from pathlib import Path

from mediscan.ocr._pdf import open_pdf
from mediscan.ocr.base import OcrEngine
from mediscan.schemas import DocumentType, ExtractedDocument, PageText


class PyMuPdfEngine(OcrEngine):
    """Extracts per-page text from text-PDFs into an ExtractedDocument."""

    # Audit-trail name recorded in ExtractedDocument.extraction_method.
    method_name = "pymupdf"

    def extract(self, path: Path) -> ExtractedDocument:
        """Read every page's text. Raises CorruptDocumentError if unreadable.

        Note `raise ... from err` below: it CHAINS the original PyMuPDF
        error onto ours, so a debugger sees both our clean message and
        the library's raw reason. Chaining preserves evidence.
        """
        document = open_pdf(path)
        with document:  # pymupdf documents are context managers too
            pages: list[PageText] = []
            for index, page in enumerate(document, start=1):
                text = page.get_text()
                # char_count is computed by the schema (decision #014)
                pages.append(PageText(page_number=index, text=text))

        full_text = "\n".join(p.text for p in pages)
        return ExtractedDocument(
            doc_type=DocumentType.PDF_TEXT,
            pages=pages,
            full_text=full_text,
            extraction_method=self.method_name,
            # ocr_confidence stays None: no OCR ran (honesty rule)
        )
