"""OCR extraction from images via PaddleOCR.

WHY THIS FILE EXISTS
    Photos and scans contain text as PIXELS. PaddleOCR (decision #015)
    recognizes characters in those pixels and — crucially — reports a
    confidence score per recognized line. This engine turns that raw
    output into our honest ExtractedDocument shape: real text, real
    confidence, blank results represented truthfully.

WHY THE ENGINE LOADS LAZILY
    Constructing PaddleOCR loads ~200 MB of models into memory and takes
    seconds. We delay that until the first extract() call, so importing
    this module (which every test run does) stays instant, and programs
    that never OCR anything never pay the cost.

"""

from pathlib import Path

from mediscan.ocr.base import OcrEngine
from mediscan.ocr.exceptions import CorruptDocumentError
from mediscan.schemas import DocumentType, ExtractedDocument, PageText


class PaddleOcrEngine(OcrEngine):
    """Reads text out of images (PNG/JPEG) with per-line confidence."""

    method_name = "paddleocr"

    def __init__(self) -> None:
        # None means "models not loaded yet" — see module docstring.
        self._ocr = None

    def _engine(self):
        """Load PaddleOCR on first use, then reuse it (lazy initialization)."""
        if self._ocr is None:
            # Import inside the method for the same lazy reason: even
            # importing paddleocr is slow, so only OCR users pay for it.
            from paddleocr import PaddleOCR

            # The MODERN parameter names (the deprecation warnings we saw
            # in the 3.1 experiment told us the old ones are dying).
            self._ocr = PaddleOCR(use_textline_orientation=True, lang="en")
        return self._ocr

    def extract(self, path: Path) -> ExtractedDocument:
        """OCR one image file into an ExtractedDocument.

        Contract promises honored here:
        - a blank/unreadable-but-valid image yields one PageText with
          empty text and ocr_confidence 0.0 (honest emptiness);
        - real OCR ALWAYS sets ocr_confidence (never None here — this
          engine is actual OCR, unlike PyMuPDF);
        - unreadable files raise CorruptDocumentError.
        """
        try:
            results = self._engine().predict(str(path))
        except Exception as err:
            raise CorruptDocumentError(
                f"PaddleOCR could not process the image ({type(err).__name__})"
            ) from err

        # results is a list with ONE entry for a single image. That entry
        # behaves like a dict with parallel lists:
        #   result["rec_texts"]  -> ["Hemoglobin", "9.8 g/dL", ...]
        #   result["rec_scores"] -> [0.98, 0.95, ...]  (same order/length)
        # Unexpected shapes (a future PaddleOCR version changing its
        # output) must become OUR error family, not a raw KeyError.
        try:
            result = results[0]
            texts = result["rec_texts"]
            scores = result["rec_scores"]
        except (IndexError, KeyError, TypeError) as err:
            raise CorruptDocumentError(
                f"PaddleOCR returned unexpected output shape " f"({type(err).__name__})"
            ) from err

        # Silent-truncation guard: plain zip() would quietly drop the
        # tail of the longer list — a discarded lab value with no error.
        if len(texts) != len(scores):
            raise CorruptDocumentError(
                f"PaddleOCR returned mismatched output: {len(texts)} texts "
                f"but {len(scores)} scores"
            )

        filtered_texts = []
        filtered_scores = []

        for text, score in zip(texts, scores, strict=True):
            cleaned_text = text.strip()

            if cleaned_text:
                filtered_texts.append(cleaned_text)
                filtered_scores.append(score)

        page_text = "\n".join(filtered_texts)

        if filtered_scores:
            confidence = sum(filtered_scores) / len(filtered_scores)
        else:
            confidence = 0.0

        return ExtractedDocument(
            doc_type=DocumentType.IMAGE,
            pages=[
                PageText(
                    page_number=1,
                    text=page_text,
                )
            ],
            full_text=page_text,
            extraction_method=self.method_name,
            ocr_confidence=confidence,
        )
