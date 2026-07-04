"""Integration test: the complete Sprint 2 chain, one document at a time.

Unit tests interrogate each part alone; THIS file proves the parts hold
hands: validate -> store securely -> route -> extract, using the synthetic
fixtures. If a seam between components breaks (wrong type handed over,
storage renaming confusing the router), it fails here and nowhere else.
"""

import pytest

pytest.importorskip("pymupdf")

from pathlib import Path  # noqa: E402

from mediscan.ingestion.exceptions import SpoofedFileTypeError  # noqa: E402
from mediscan.ingestion.storage import SecureUploadDir  # noqa: E402
from mediscan.ingestion.validators import validate_upload  # noqa: E402
from mediscan.ocr.pymupdf_engine import PyMuPdfEngine  # noqa: E402
from mediscan.ocr.router import detect_document_type  # noqa: E402
from mediscan.schemas import DocumentType  # noqa: E402

FIXTURES = Path("tests/fixtures/files")


def test_text_pdf_flows_from_upload_to_extracted_text():
    """The happy path: a lab report PDF, end to end."""
    source = FIXTURES / "cbc_report.pdf"

    # 1. front door
    assert validate_upload(source) is DocumentType.PDF_TEXT

    # 2. secure storage (anonymized name), 3. routing, 4. extraction —
    # all on the STORED copy, exactly as the real pipeline will do it
    with SecureUploadDir() as upload_dir:
        stored = upload_dir.store(source)
        kept_dir = upload_dir.path

        assert detect_document_type(stored) is DocumentType.PDF_TEXT

        extracted = PyMuPdfEngine().extract(stored)

    # the values planted by generate.py came out the other end intact
    assert extracted.doc_type is DocumentType.PDF_TEXT
    assert len(extracted.pages) == 2
    assert "Hemoglobin" in extracted.full_text
    assert "9.8" in extracted.full_text
    assert "13.0 - 17.0" in extracted.full_text
    assert "SYNTHETIC" in extracted.full_text
    assert extracted.extraction_method == "pymupdf"
    assert extracted.ocr_confidence is None  # no OCR ran — honesty rule

    # and the secure directory self-destructed on exit
    assert not kept_dir.exists()


def test_scanned_pdf_is_routed_to_the_ocr_queue():
    """A scan passes validation but the router diverts it toward OCR."""
    source = FIXTURES / "scanned_report.pdf"
    assert validate_upload(source) is DocumentType.PDF_TEXT  # honest PDF...
    with SecureUploadDir() as upload_dir:
        stored = upload_dir.store(source)
        # ...but the router sees it has no text layer (Sprint 3's queue)
        assert detect_document_type(stored) is DocumentType.PDF_SCANNED


def test_spoofed_upload_is_stopped_at_the_front_door():
    """A spoofed file must never even reach storage."""
    with pytest.raises(SpoofedFileTypeError):
        validate_upload(FIXTURES / "spoofed.pdf")
