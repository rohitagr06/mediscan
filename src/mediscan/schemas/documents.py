"""Document extraction schemas: from validated upload to extracted text.

WHY THIS FILE EXISTS
    These schemas are the handoff shape between ingestion (Sprint 2),
    the text-vs-scan router, and the OCR engines (Sprint 3). A document
    leaves this stage as an ExtractedDocument: typed, page-structured,
    and honest about how its text was obtained.
"""

from enum import StrEnum

from pydantic import Field, model_validator

from mediscan.schemas.base import MediScanModel
from mediscan.schemas.confidence import Score


class DocumentType(StrEnum):
    """How an uploaded document should be (or was) processed.

    An enum instead of a plain string: a typo like "pdf_image" is an
    instant error, and every allowed type is listed in exactly one place.
    """

    PDF_TEXT = "pdf_text"  # real text inside — extract directly
    PDF_SCANNED = "pdf_scanned"  # pixels only — needs OCR (Sprint 3)
    IMAGE = "image"  # photo of a report — needs OCR (Sprint 3)


class PageText(MediScanModel):
    """The extracted text of ONE page of a document.

    text has NO minimum length on purpose: a blank page (cover sheet,
    empty back side) is a real, legitimate extraction result. Refusing
    to represent it would force upstream code to lie.
    """

    page_number: int = Field(
        ge=1,  # pages are counted by humans: 1, 2, 3...
        description="1-based page number within the source document.",
    )
    text: str = Field(
        description="Extracted text of this page; may be empty for blank pages.",
    )
    char_count: int = Field(
        ge=0,
        description="Number of characters in `text`; must match exactly.",
    )

    @model_validator(mode="after")
    def check_char_count(self):
        """An object whose bookkeeping disagrees with its contents is corrupt.

        SECURITY NOTE: the error reports LENGTHS only, never the text
        itself — page text is patient data and must never leak into
        exceptions or logs.
        """
        if self.char_count != len(self.text):
            raise ValueError(
                f"char_count ({self.char_count}) does not match the actual "
                f"text length ({len(self.text)}) on page {self.page_number}"
            )
        return self


class ExtractedDocument(MediScanModel):
    """The full text-extraction result for one uploaded document."""

    doc_type: DocumentType = Field(
        description="How this document was classified and processed.",
    )
    pages: list[PageText] = Field(
        default_factory=list,  # fresh list per object
        description="Per-page extraction results, in page order.",
    )
    full_text: str = Field(
        default="",
        description="All pages' text joined together, for whole-document use.",
    )
    extraction_method: str = Field(
        min_length=1,
        description="Which engine produced this text, e.g. 'pymupdf'. Audit trail.",
    )
    ocr_confidence: Score | None = Field(
        default=None,
        description=(
            "OCR engine confidence, 0.0-1.0. None when no OCR ran — a "
            "text-PDF extraction has no OCR step to be confident about."
        ),
    )

    @model_validator(mode="after")
    def check_consistency(self):
        """Guards, not janitors: reject contradictions, never repair them.

        Silently 'fixing' a bad combination would hide the upstream bug
        that produced it (same philosophy as decision #011).
        """
        if self.doc_type is DocumentType.PDF_TEXT and self.ocr_confidence is not None:
            raise ValueError(
                f"doc_type is '{self.doc_type}' but ocr_confidence is set "
                f"({self.ocr_confidence}) — no OCR runs for text PDFs, so "
                f"this confidence value must be a mistake upstream"
            )
        page_numbers = [p.page_number for p in self.pages]
        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError(f"duplicate page numbers in pages: {sorted(page_numbers)}")
        return self
