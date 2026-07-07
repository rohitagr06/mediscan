"""Parser output schemas.

WHY THIS FILE EXISTS
    Parsing and medical judgment are intentionally separated in
    MediScan. The parser extracts raw laboratory observations from text
    without deciding whether they are normal or abnormal.

    ParseOutcome represents both the successfully extracted laboratory
    results and the lines that could not be interpreted. Unparsed lines
    are preserved because they contribute to confidence scoring,
    explainability, and debugging rather than being silently discarded.
"""

from pydantic import Field

from mediscan.schemas.base import MediScanModel
from mediscan.schemas.labs import LabResult


class ParseOutcome(MediScanModel):
    """The raw output produced by the extraction pipeline."""

    results: list[LabResult] = Field(
        default_factory=list,
        description=(
            "Laboratory results successfully extracted from the document. "
            "These are raw observations only and have not yet been "
            "evaluated by the deterministic medical engine."
        ),
    )

    unparsed_lines: list[str] = Field(
        default_factory=list,
        description=(
            "Lines that could not be interpreted by the parser. These "
            "are preserved for confidence scoring, explainability, and "
            "debugging instead of being silently discarded."
        ),
    )
