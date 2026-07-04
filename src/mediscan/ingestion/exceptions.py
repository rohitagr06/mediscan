"""Custom exceptions for upload validation.

WHY THIS FILE EXISTS
    Distinct exception TYPES let calling code react differently to
    different problems (the type is for code; the message is for humans).
    All types inherit from UploadValidationError, so a caller may catch
    the whole family with one line, or a single specific problem.

SECURITY RULE
    Messages carry sizes, types and limits — NEVER filenames. Patients
    name files things like "ramesh_hiv_report.pdf"; a filename in an
    error message is PHI in a log file.
"""


class UploadValidationError(Exception):
    """Base class: any reason an uploaded file was refused."""


class FileTooLargeError(UploadValidationError):
    """The uploaded file exceeds the configured size limit."""

    def __init__(self, size_mb: float, limit_mb: int):
        self.size_mb = size_mb
        self.limit_mb = limit_mb
        super().__init__(f"file is {size_mb:.1f} MB; the limit is {limit_mb} MB")


class UnsupportedFileTypeError(UploadValidationError):
    """The file's type is not on the allowlist (PDF, PNG, JPEG)."""

    def __init__(self, detect_file_type: str, allowed_file_type: set[str]):
        self.detect_file_type = detect_file_type
        self.allowed_file_type = allowed_file_type

        allowed = ", ".join(sorted(allowed_file_type))
        super().__init__(
            f"file type '{detect_file_type}' is not supported; allowed: {allowed}"
        )


class SpoofedFileTypeError(UploadValidationError):
    """The extension claims one type but the file's bytes say another."""

    def __init__(self, claimed_type: str, actual_type: str):
        self.claimed_type = claimed_type
        self.actual_type = actual_type
        super().__init__(
            f"possible tampering or corruption: extension claims "
            f"'{claimed_type}' but file bytes are '{actual_type}'"
        )
