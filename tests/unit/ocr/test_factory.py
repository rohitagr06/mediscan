"""Unit tests for the OCR engine factory.

These tests verify that every supported DocumentType is mapped to the
correct extraction engine and that unsupported document types fail
loudly instead of silently selecting an incorrect engine.
"""

import pytest

from mediscan.ocr.base import OcrEngine
from mediscan.ocr.factory import get_engine_for
from mediscan.ocr.paddle_engine import PaddleOcrEngine
from mediscan.ocr.pymupdf_engine import PyMuPdfEngine
from mediscan.ocr.scanned_pdf import ScannedPdfEngine
from mediscan.schemas import DocumentType


@pytest.mark.parametrize(
    ("document_type", "expected_engine"),
    [
        (DocumentType.PDF_TEXT, PyMuPdfEngine),
        (DocumentType.IMAGE, PaddleOcrEngine),
        (DocumentType.PDF_SCANNED, ScannedPdfEngine),
    ],
)
def test_get_engine_for_returns_expected_engine(
    document_type: DocumentType,
    expected_engine: type[OcrEngine],
) -> None:
    """Each document type should return its registered OCR engine."""
    engine = get_engine_for(document_type)

    assert isinstance(engine, expected_engine)


def test_every_document_type_has_registered_engine() -> None:
    """Every DocumentType enum member must have a registered engine."""
    for document_type in DocumentType:
        engine = get_engine_for(document_type)

        assert isinstance(engine, OcrEngine)


def test_unknown_document_type_raises_value_error() -> None:
    """Unknown document types should fail loudly."""
    with pytest.raises(
        ValueError,
        match="No OCR engine registered",
    ):
        get_engine_for("bmp")


def test_all_registered_engines_define_method_name() -> None:
    """Every registered OCR engine should expose a non-empty method name."""
    for document_type in DocumentType:
        engine = get_engine_for(document_type)

        assert engine.method_name
