"""Text extraction from born-digital PDFs via PyMuPDF.

WHY THIS FILE EXISTS
    Lab software emits "text PDFs": the characters are really in the
    file, extractable perfectly and instantly — no OCR needed. This
    engine handles exactly that case. Scanned PDFs and photos go to the
    OCR engines in Sprint 3; the router (ocr/router.py) decides which
    path a document takes.

ROW RECONSTRUCTION (Sprint 8, the real-PDF fix)
    `page.get_text()` returns characters in the PDF's internal stream
    order, which for a real tabular lab report (e.g. Tata 1mg) is
    COLUMN-major — breaking the row parser (it saw a name and its value on
    different lines, and parsed nothing). We instead take word boxes
    (`get_text("words")`) and rebuild the visual rows via
    ocr/_rows.reconstruct_lines. `parse_lab_text` is unchanged; we just
    feed it the horizontal layout it was always designed for.
"""

from pathlib import Path

from mediscan.ocr._pdf import open_pdf
from mediscan.ocr._rows import reconstruct_lines
from mediscan.ocr.base import OcrEngine
from mediscan.schemas import DocumentType, ExtractedDocument, PageText


class PyMuPdfEngine(OcrEngine):
    """Extracts per-page text from text-PDFs into an ExtractedDocument."""

    # Audit-trail name recorded in ExtractedDocument.extraction_method.
    method_name = "pymupdf"

    def extract(self, path: Path) -> ExtractedDocument:
        """Read every page's text. Raises CorruptDocumentError if unreadable.

        Opening (and its error handling) lives in the shared
        ocr/_pdf.open_pdf helper: it turns a raw PyMuPDF failure into a
        clean CorruptDocumentError while CHAINING the original error
        (raise ... from err), so a debugger still sees the library's raw
        reason. Chaining preserves evidence.

        Text is reconstructed into visual rows (see the module docstring),
        so a column-major PDF stream still yields row-per-line output.
        """
        document = open_pdf(path)
        with document:  # pymupdf documents are context managers too
            pages: list[PageText] = []
            for index, page in enumerate(document, start=1):
                text = reconstruct_lines(page.get_text("words"))
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
