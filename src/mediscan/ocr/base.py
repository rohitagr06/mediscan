"""The OcrEngine contract: the shape every reading engine must match.

WHY THIS FILE EXISTS
    MediScan will have several engines that turn documents into text
    (PyMuPDF today, PaddleOCR next). The rest of the pipeline should
    never care which one is doing the reading — it just calls
    .extract() on "an engine". This class defines what "an engine"
    means, and Python enforces it: a class that inherits OcrEngine
    but forgets to implement extract() cannot even be created.

THE THREE PROMISES every engine makes:
    1. Every page of the input is represented — blank pages included
       (a blank page is a real result, never skipped).
    2. Engines that perform real OCR set ocr_confidence; engines that
       read true text (PyMuPDF) leave it None — no invented numbers.
    3. Unreadable input raises CorruptDocumentError, never a raw
       library exception — callers catch OUR error family only.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from mediscan.schemas import ExtractedDocument


class OcrEngine(ABC):
    """Contract for all document-reading engines."""

    # Every engine's audit-trail name (recorded in extraction_method).
    method_name: str = "abstract"

    @abstractmethod
    def extract(self, path: Path) -> ExtractedDocument:
        """Read the document at `path` into an ExtractedDocument.

        Must honor the three promises in the module docstring.
        """
        ...
