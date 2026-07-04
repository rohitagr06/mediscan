"""Tests for the OcrEngine contract (ocr/base.py).

These prove the contract MACHINERY works: the contract itself cannot
be built, forgetful engines are rejected at creation time, and the
real engine officially fits the socket.
"""

from pathlib import Path

import pytest

from mediscan.ocr.base import OcrEngine
from mediscan.ocr.pymupdf_engine import PyMuPdfEngine


def test_contract_itself_cannot_be_instantiated():
    # The contract is a shape, not a machine — building it must fail.
    with pytest.raises(TypeError):
        OcrEngine()


def test_forgetful_engine_rejected_at_creation():
    # A throwaway class defined right here in the test — totally legal,
    # and the standard way to test what happens to a BAD implementer
    # without polluting real code with one.
    class LazyEngine(OcrEngine):
        pass  # inherits the contract but implements nothing

    with pytest.raises(TypeError):
        LazyEngine()


def test_pymupdf_engine_fits_the_contract():
    engine = PyMuPdfEngine()

    # isinstance asks: "is this object officially an OcrEngine?"
    assert isinstance(engine, OcrEngine)

    # and the retrofit changed nothing about its actual behavior:
    doc = engine.extract(Path("tests/fixtures/files/cbc_report.pdf"))
    assert len(doc.pages) == 2
    assert doc.extraction_method == "pymupdf"
