"""Factory for selecting the correct OCR engine based on document type.

WHY THIS FILE EXISTS
    The document router determines WHAT kind of document was uploaded
    (PDF with text, scanned PDF, or image). This factory bridges that
    decision to the appropriate OCR engine so callers do not need to know
    how to construct or select engines themselves.

WHY THIS DESIGN
    Decision #017:
    The factory is keyed by DocumentType rather than OCR backend.
    Decision #015 standardized PaddleOCR as the only OCR backend, so a
    backend-selection factory would be premature abstraction. Instead,
    this factory solves the real runtime problem of mapping routed
    document types to their extraction engines.
"""

from mediscan.ocr.base import OcrEngine
from mediscan.ocr.paddle_engine import PaddleOcrEngine
from mediscan.ocr.pymupdf_engine import PyMuPdfEngine
from mediscan.ocr.scanned_pdf import ScannedPdfEngine
from mediscan.schemas import DocumentType

_ENGINE_FOR_TYPE: dict[DocumentType, type[OcrEngine]] = {
    DocumentType.PDF_TEXT: PyMuPdfEngine,
    DocumentType.PDF_SCANNED: ScannedPdfEngine,
    DocumentType.IMAGE: PaddleOcrEngine,
}


def get_engine_for(doc_type: DocumentType) -> OcrEngine:
    """Return the OCR engine responsible for the given document type.

    Each supported DocumentType has exactly one registered extraction
    engine. A ValueError is raised if no engine is registered because
    that indicates a programming/configuration error rather than a user
    error.
    """
    try:
        engine_class = _ENGINE_FOR_TYPE[doc_type]
    except KeyError as err:
        raise ValueError(
            f"No OCR engine registered for document type {doc_type!r}."
        ) from err

    return engine_class()
