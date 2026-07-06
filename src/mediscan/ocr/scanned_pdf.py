"""OCR for scanned PDFs: pages rendered to images, then recognized.

WHY THIS FILE EXISTS
    A scanned PDF is a book of photographs wearing a PDF coat. No text
    layer exists, so the PyMuPDF engine finds nothing and the router
    sends these documents HERE. The recipe: render each page back into
    an image file (get_pixmap = "screenshot the page at a chosen
    sharpness"), clean each image (preprocessing, decision #016), OCR
    each cleaned image (PaddleOCR, decision #015), then assemble the
    per-page results into one multi-page ExtractedDocument.

WHY THE OCR ENGINE IS PASSED IN (dependency injection)
    __init__ accepts any OcrEngine rather than hardcoding PaddleOCR.
    Default behavior is unchanged (a PaddleOcrEngine is built if none
    is given), but tests can hand in a FAKE engine and verify this
    module's plumbing in milliseconds without loading 200 MB of models.
    "Depend on the contract, not the concrete engine" — the base.py
    philosophy, applied one level up.
"""

import tempfile
from pathlib import Path

from mediscan.config import settings
from mediscan.ocr._pdf import open_pdf
from mediscan.ocr.base import OcrEngine
from mediscan.ocr.exceptions import DocumentTooLargeError
from mediscan.ocr.paddle_engine import PaddleOcrEngine
from mediscan.ocr.preprocessing import prepare_image
from mediscan.schemas import (
    DocumentType,
    ExtractedDocument,
    PageText,
)


class ScannedPdfEngine(OcrEngine):
    """Turns scanned PDFs into text via render -> clean -> recognize."""

    method_name = "paddleocr-scanned-pdf"

    def __init__(self, ocr_engine: OcrEngine | None = None) -> None:
        # Injection point: any contract-honoring engine works here.
        self._ocr_engine = ocr_engine or PaddleOcrEngine()

    def extract(self, path: Path) -> ExtractedDocument:
        """OCR every page of a scanned PDF into one ExtractedDocument."""
        document = open_pdf(path)

        # TemporaryDirectory: the standard library's own self-destructing
        # folder (same guarantee as our SecureUploadDir, no upload rules).
        # EVERYTHING below must happen inside this block — the rendered
        # images vanish the moment it ends.
        with tempfile.TemporaryDirectory(prefix="mediscan_render_") as tmp:
            workdir = Path(tmp)

            # ---- render each page to a PNG at configured DPI ----
            page_images: list[Path] = []
            with document:
                if len(document) > settings.max_pdf_pages:
                    raise DocumentTooLargeError(
                        pages=len(document), limit=settings.max_pdf_pages
                    )
                for index, page in enumerate(document, start=1):
                    pixmap = page.get_pixmap(dpi=settings.render_dpi)
                    image_path = workdir / f"page_{index}.png"
                    pixmap.save(image_path)
                    page_images.append(image_path)

            # ---- clean each rendered page, OCR it, assemble results ----
            pages: list[PageText] = []
            confidences: list[float] = []
            for index, image_path in enumerate(page_images, start=1):
                cleaned = prepare_image(image_path, workdir)
                page_doc = self._ocr_engine.extract(cleaned)
                pages.append(PageText(page_number=index, text=page_doc.full_text))
                # None -> 0.0 (not skipped): an absent confidence can only
                # LOWER the average, never inflate it. Unknown is not "good".
                confidences.append(
                    page_doc.ocr_confidence
                    if page_doc.ocr_confidence is not None
                    else 0.0
                )

            full_text = "\n".join(page.text for page in pages)

            if confidences:
                document_confidence = sum(confidences) / len(confidences)
            else:
                document_confidence = 0.0

            return ExtractedDocument(
                doc_type=DocumentType.PDF_SCANNED,
                pages=pages,
                full_text=full_text,
                extraction_method=self.method_name,
                ocr_confidence=document_confidence,
            )
