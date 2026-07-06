"""Exceptions raised while parsing/extracting documents.

Separate family from ingestion's UploadValidationError on purpose:
validation failures mean "we refuse this file"; extraction failures mean
"we accepted it, but could not read it". Different walls, different
reactions upstream (the UI will phrase them differently).
"""


class DocumentExtractionError(Exception):
    """Base class: any failure while extracting content from a document."""


class CorruptDocumentError(DocumentExtractionError):
    """The file passed validation but its internals are unreadable.

    NO filename in the message (PHI rule) — only facts about the failure.
    """

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"document is corrupt or unreadable: {detail}")


class DocumentTooLargeError(DocumentExtractionError):
    """The document has more pages than the configured limit."""

    def __init__(self, pages: int, limit: int):
        self.pages = pages
        self.limit = limit
        super().__init__(f"document has {pages} pages; the limit is {limit}")
