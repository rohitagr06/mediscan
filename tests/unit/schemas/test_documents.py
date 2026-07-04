"""Tests for mediscan.schemas.documents.

The two rules under special guard here:
1. A blank page is REPRESENTABLE (text="", char_count=0) — reality must
   never be unrepresentable (see the option A vs B discussion, Sprint 2).
2. Validation errors must never leak page text — page content is patient
   data, and exceptions end up in logs.
"""

import pytest
from pydantic import ValidationError

from mediscan.schemas import DocumentType, ExtractedDocument, PageText

# ---------- DocumentType ----------


def test_document_types_exact():
    assert [d.value for d in DocumentType] == ["pdf_text", "pdf_scanned", "image"]


# ---------- PageText: happy paths ----------


def test_normal_page():
    p = PageText(page_number=1, text="Hemoglobin 9.8 g/dL", char_count=19)
    assert p.char_count == len(p.text)


def test_blank_page_is_representable():
    # A blank back side or cover sheet is a REAL extraction result.
    p = PageText(page_number=2, text="", char_count=0)
    assert p.text == ""
    assert p.char_count == 0


# ---------- PageText: rejections ----------


def test_page_zero_rejected():
    with pytest.raises(ValidationError):
        PageText(page_number=0, text="x", char_count=1)


def test_char_count_mismatch_rejected():
    with pytest.raises(ValidationError):
        PageText(page_number=1, text="hello", char_count=3)


def test_error_message_never_leaks_page_text():
    # SECURITY: page text is patient data. Force a validation failure and
    # prove the text itself does not appear anywhere in the exception.
    sensitive_text = "PATIENT NAME RAMESH HIV POSITIVE"
    with pytest.raises(ValidationError) as exc_info:
        PageText(page_number=1, text=sensitive_text, char_count=999)
    assert sensitive_text not in str(exc_info.value)
    assert "RAMESH" not in str(exc_info.value)


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        PageText(page_number=1, text="x", char_count=1, language="en")


# ---------- ExtractedDocument: happy paths ----------


def test_text_pdf_document():
    doc = ExtractedDocument(
        doc_type=DocumentType.PDF_TEXT,
        pages=[
            PageText(page_number=1, text="CBC REPORT", char_count=10),
            PageText(page_number=2, text="", char_count=0),  # blank page OK
        ],
        full_text="CBC REPORT",
        extraction_method="pymupdf",
    )
    assert doc.ocr_confidence is None  # no OCR ran — honestly absent
    assert len(doc.pages) == 2


def test_scanned_pdf_may_carry_ocr_confidence():
    doc = ExtractedDocument(
        doc_type=DocumentType.PDF_SCANNED,
        extraction_method="paddleocr",
        ocr_confidence=0.87,
    )
    assert doc.ocr_confidence == 0.87


def test_pages_default_lists_are_independent():
    a = ExtractedDocument(doc_type=DocumentType.IMAGE, extraction_method="x")
    b = ExtractedDocument(doc_type=DocumentType.IMAGE, extraction_method="x")
    a.pages.append(PageText(page_number=1, text="hi", char_count=2))
    assert b.pages == []


# ---------- ExtractedDocument: rejections ----------


def test_text_pdf_with_ocr_confidence_rejected():
    # The honesty rule: a confidence for OCR that never ran is a
    # fabricated number — reject, don't repair (guards, not janitors).
    with pytest.raises(ValidationError):
        ExtractedDocument(
            doc_type=DocumentType.PDF_TEXT,
            extraction_method="pymupdf",
            ocr_confidence=0.99,
        )


def test_duplicate_page_numbers_rejected():
    with pytest.raises(ValidationError):
        ExtractedDocument(
            doc_type=DocumentType.PDF_TEXT,
            extraction_method="pymupdf",
            pages=[
                PageText(page_number=1, text="a", char_count=1),
                PageText(page_number=1, text="b", char_count=1),
            ],
        )


def test_empty_extraction_method_rejected():
    with pytest.raises(ValidationError):
        ExtractedDocument(doc_type=DocumentType.PDF_TEXT, extraction_method="")


def test_ocr_confidence_out_of_bounds_rejected():
    with pytest.raises(ValidationError):
        ExtractedDocument(
            doc_type=DocumentType.IMAGE,
            extraction_method="paddleocr",
            ocr_confidence=1.2,
        )


def test_invalid_doc_type_rejected():
    with pytest.raises(ValidationError):
        ExtractedDocument(doc_type="pdf_image", extraction_method="pymupdf")
