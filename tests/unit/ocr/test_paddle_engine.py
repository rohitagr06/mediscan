"""Tests for the PaddleOCR engine.

TWO SPEEDS OF TEST LIVE HERE
    The contract test is fast (lazy loading means creating the engine
    costs nothing — no models load until extract() is called).
    The extraction tests run REAL OCR (seconds each), so they carry the
    @pytest.mark.slow sticker and are excluded from the default run:

        uv run pytest            -> fast suite (slow tests deselected)
        uv run pytest -m slow    -> only the OCR tests, when you choose

WHY ASSERTIONS ARE "KEY TOKENS", NOT EXACT TEXT
    OCR output is allowed to wobble at the edges (spacing, punctuation).
    Pinning the exact full text would make the test break on harmless
    wobble. We assert the tokens that MUST be present for the pipeline
    to work: the test name and the value.
"""

import pytest

pytest.importorskip("paddleocr")

from pathlib import Path  # noqa: E402

from mediscan.ocr.base import OcrEngine  # noqa: E402
from mediscan.ocr.paddle_engine import PaddleOcrEngine  # noqa: E402
from mediscan.schemas import DocumentType  # noqa: E402

FIXTURES = Path("tests/fixtures/files")


def test_engine_fits_the_contract():
    # FAST: thanks to lazy loading, constructing the engine loads
    # nothing — this test costs microseconds.
    engine = PaddleOcrEngine()
    assert isinstance(engine, OcrEngine)
    assert engine.method_name == "paddleocr"


@pytest.mark.slow
def test_reads_the_report_photo():
    doc = PaddleOcrEngine().extract(FIXTURES / "report_photo.png")

    assert doc.doc_type is DocumentType.IMAGE
    assert doc.extraction_method == "paddleocr"

    # real OCR must report real confidence — and on our clean synthetic
    # photo it should be high (your playground run showed ~0.98)
    assert doc.ocr_confidence is not None
    assert doc.ocr_confidence > 0.8

    # key tokens, not exact text (see module docstring)
    assert "Hemoglobin" in doc.full_text
    assert "9.8" in doc.full_text


@pytest.mark.slow
def test_blank_image_is_honestly_empty():
    doc = PaddleOcrEngine().extract(FIXTURES / "sample.png")

    # the honesty promise, pinned forever: OCR ran, found nothing,
    # says so with 0.0 — never None (None means "no OCR happened")
    assert doc.ocr_confidence == 0.0
    assert doc.full_text == ""
    assert len(doc.pages) == 1
    assert doc.pages[0].char_count == 0
