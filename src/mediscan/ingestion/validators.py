"""Secure upload validation: the front door of MediScan.

WHY THIS FILE EXISTS
    Every file MediScan touches passes through validate_upload() first.
    Until it returns, the file is treated as hostile. Four checks run in
    a deliberate order — each check is cheaper than the next, so an
    attack is rejected at the lowest possible cost:

    1. SIZE     — read from filesystem metadata, without opening the
                  file at all. A 2 GB upload is refused for free; the
                  defense must never be more expensive than the attack.
    2. EXTENSION — allowlist, not blocklist: we name what is permitted
                  and refuse everything else by default.
    3. MAGIC BYTES — the first bytes of the file identify its REAL type;
                  the filename is just a label anyone can change.
    4. CROSS-CHECK — if the extension's claim and the bytes' evidence
                  disagree, the file is spoofed or corrupt. Honest files
                  never disagree with their own name.

SECURITY RULE
    Nothing in this module ever logs or embeds a filename in an error —
    patient-named files are PHI (see ingestion/exceptions.py).
"""

from pathlib import Path

from mediscan.config import settings
from mediscan.ingestion.exceptions import (
    FileTooLargeError,
    SpoofedFileTypeError,
    UnsupportedFileTypeError,
)
from mediscan.schemas import DocumentType

# Allowlist of accepted file extensions (lower-case, with the dot).
_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}

# Published file-format signatures ("magic bytes") -> what they prove.
# JPEG is matched on 3 bytes only: the 4th byte varies by JPEG flavor
# (e.g. ffd8ffe0 = JFIF, ffd8ffe1 = EXIF), so we match the stable prefix.
_MAGIC_SIGNATURES: dict[bytes, DocumentType] = {
    b"%PDF-": DocumentType.PDF_TEXT,
    b"\x89PNG\r\n\x1a\n": DocumentType.IMAGE,
    b"\xff\xd8\xff": DocumentType.IMAGE,
}

# What DocumentType each allowed extension CLAIMS to be. Used by the
# cross-check: extension claim vs magic-byte evidence must agree.
_EXPECTED_TYPES: dict[str, DocumentType] = {
    ".pdf": DocumentType.PDF_TEXT,
    ".png": DocumentType.IMAGE,
    ".jpg": DocumentType.IMAGE,
    ".jpeg": DocumentType.IMAGE,
}

_BYTES_PER_MB = 1024 * 1024

# 8 bytes covers our longest signature (PNG). Reading more gains nothing.
_HEADER_LENGTH = 8


def _detect_type_from_bytes(head: bytes) -> DocumentType | None:
    """Return the DocumentType the magic bytes prove, or None if unknown.

    Returns None instead of raising: a helper DETECTS, the orchestrator
    (validate_upload) JUDGES which exception the situation deserves.
    """
    for signature, document_type in _MAGIC_SIGNATURES.items():
        if head.startswith(signature):
            return document_type
    return None


def validate_upload(path: Path) -> DocumentType:
    """Validate an uploaded file and return its verified DocumentType.

    Runs the four checks described in the module docstring, in order.

    Boundary rule: a file of EXACTLY the configured limit is accepted;
    only strictly larger files are rejected.

    Note: PDFs are returned as PDF_TEXT at this stage. Whether a PDF
    actually contains text or is a scan needing OCR is decided later by
    the router (ocr/router.py) — validation proves safety, not content.

    Raises:
        FileTooLargeError: file exceeds settings.max_upload_mb.
        UnsupportedFileTypeError: empty file, unknown extension, or
            unrecognized magic bytes.
        SpoofedFileTypeError: extension and magic bytes disagree.
    """
    # -- Check 1: size, from filesystem metadata (file stays unopened) --
    file_size = path.stat().st_size
    max_size_bytes = settings.max_upload_mb * _BYTES_PER_MB

    # An empty file matches no known signature and can contain no report,
    # so it is classified as an unsupported type rather than given its
    # own exception; "empty file" appears as the detected type.
    if file_size == 0:
        raise UnsupportedFileTypeError("empty file", _ALLOWED_EXTENSIONS)

    if file_size > max_size_bytes:
        raise FileTooLargeError(
            size_mb=file_size / _BYTES_PER_MB,
            limit_mb=settings.max_upload_mb,
        )

    # -- Check 2: extension allowlist (case-insensitive) --
    extension = path.suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(extension, _ALLOWED_EXTENSIONS)

    # -- Check 3: magic bytes — what the file's contents actually are --
    with path.open("rb") as file:
        head = file.read(_HEADER_LENGTH)

    detected_type = _detect_type_from_bytes(head)
    if detected_type is None:
        raise UnsupportedFileTypeError("unknown signature", _ALLOWED_EXTENSIONS)

    # -- Check 4: cross-check — claim vs evidence must agree --
    # Keyword arguments on purpose: claimed/actual are both strings and
    # would silently swap if passed positionally (house rule).
    expected_type = _EXPECTED_TYPES[extension]
    if detected_type is not expected_type:
        raise SpoofedFileTypeError(
            claimed_type=expected_type,  # what the extension promised
            actual_type=detected_type,  # what the bytes revealed
        )

    return detected_type
