"""Adversarial tests for upload validation (Sprint 2 threat model).

Every row of the threat-model table in docs/08-sprint-2-plan.md has at
least one test here. The `tmp_path` argument used throughout is a
built-in pytest fixture: a fresh, empty, auto-deleted directory per
test — perfect for fabricating hostile files without touching the repo.
"""

import pytest

from mediscan.config import settings
from mediscan.ingestion.exceptions import (
    FileTooLargeError,
    SpoofedFileTypeError,
    UnsupportedFileTypeError,
    UploadValidationError,
)
from mediscan.ingestion.validators import validate_upload
from mediscan.schemas import DocumentType

PDF_BYTES = b"%PDF-1.6 synthetic body"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG_BYTES = b"\xff\xd8\xff\xe1" + b"\x00" * 32

# ---------- happy paths ----------


def test_valid_pdf_accepted(tmp_path):
    f = tmp_path / "report.pdf"
    f.write_bytes(PDF_BYTES)
    assert validate_upload(f) is DocumentType.PDF_TEXT


def test_valid_png_accepted(tmp_path):
    f = tmp_path / "scan.png"
    f.write_bytes(PNG_BYTES)
    assert validate_upload(f) is DocumentType.IMAGE


def test_valid_jpeg_accepted(tmp_path):
    f = tmp_path / "photo.jpg"
    f.write_bytes(JPEG_BYTES)
    assert validate_upload(f) is DocumentType.IMAGE


def test_uppercase_extension_accepted(tmp_path):
    # attackers and aunties both use uppercase filenames
    f = tmp_path / "REPORT.PDF"
    f.write_bytes(PDF_BYTES)
    assert validate_upload(f) is DocumentType.PDF_TEXT


def test_exactly_at_limit_accepted(tmp_path, monkeypatch):
    # documented boundary rule: exactly the limit is ALLOWED.
    # monkeypatch shrinks the limit to 1 MB so the test writes 1 MB, not 20.
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    f = tmp_path / "exact.pdf"
    f.write_bytes(PDF_BYTES)
    with open(f, "r+b") as fh:
        fh.truncate(1024 * 1024)
    assert validate_upload(f) is DocumentType.PDF_TEXT


# ---------- threat model: size ----------


def test_one_byte_over_limit_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    f = tmp_path / "big.pdf"
    f.write_bytes(PDF_BYTES)
    with open(f, "r+b") as fh:
        fh.truncate(1024 * 1024 + 1)
    with pytest.raises(FileTooLargeError) as exc_info:
        validate_upload(f)
    # exception carries the raw facts as attributes, not just prose
    assert exc_info.value.size_bytes == 1024 * 1024 + 1
    assert exc_info.value.limit_mb == 1


def test_empty_file_rejected(tmp_path):
    f = tmp_path / "empty.pdf"
    f.write_bytes(b"")
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload(f)


# ---------- threat model: type allowlist ----------


def test_unknown_extension_rejected(tmp_path):
    f = tmp_path / "notes.docx"
    f.write_bytes(b"PK\x03\x04 zip container")
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        validate_upload(f)
    assert ".docx" in str(exc_info.value)


def test_unrecognized_magic_bytes_rejected(tmp_path):
    # right extension, garbage contents
    f = tmp_path / "garbage.pdf"
    f.write_bytes(b"\x00\x01\x02\x03\x04\x05\x06\x07")
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload(f)


# ---------- threat model: spoofing (both directions) ----------


def test_png_bytes_in_pdf_clothing_rejected(tmp_path):
    f = tmp_path / "fake.pdf"
    f.write_bytes(PNG_BYTES)
    with pytest.raises(SpoofedFileTypeError) as exc_info:
        validate_upload(f)
    # the accusation must point the right way (the 2.3 review bug)
    assert exc_info.value.claimed_type is DocumentType.PDF_TEXT
    assert exc_info.value.actual_type is DocumentType.IMAGE


def test_pdf_bytes_in_png_clothing_rejected(tmp_path):
    f = tmp_path / "fake.png"
    f.write_bytes(PDF_BYTES)
    with pytest.raises(SpoofedFileTypeError) as exc_info:
        validate_upload(f)
    assert exc_info.value.claimed_type is DocumentType.IMAGE
    assert exc_info.value.actual_type is DocumentType.PDF_TEXT


# ---------- threat model: PHI in diagnostics ----------


def test_error_messages_never_contain_the_filename(tmp_path):
    # patients name files after their conditions; filenames are PHI and
    # must never appear in exception text (which lands in logs).
    f = tmp_path / "ramesh_hiv_report.docx"
    f.write_bytes(b"PK\x03\x04")
    with pytest.raises(UploadValidationError) as exc_info:
        validate_upload(f)
    assert "ramesh" not in str(exc_info.value).lower()
