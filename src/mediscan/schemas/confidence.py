"""Confidence schemas: how sure MediScan is about its own output.

WHY THIS FILE EXISTS
    A medical tool must communicate uncertainty honestly. Confidence is
    tracked per pipeline stage (OCR, extraction, validation, grounding)
    plus an overall blend — never as a single naive number.

DECISION #011 (raised by Rohit)
    No score has a default value. A default like 1.0 could silently
    present UNSCORED output as fully confident. If a ConfidenceBreakdown
    exists, every number in it was set on purpose; "not scored yet" is
    expressed by the AnalysisReport.confidence field being None instead.
"""

from typing import Annotated

from pydantic import Field

from mediscan.schemas.base import MediScanModel

# A reusable type alias: "a float that must be between 0.0 and 1.0".
# Annotated[float, ...] means "a float, carrying extra rules with it".
# Defining the rule ONCE and importing it elsewhere (labs.py uses it too)
# is the DRY principle — Don't Repeat Yourself — applied to types.
Score = Annotated[float, Field(ge=0.0, le=1.0)]
"""A confidence score bounded to [0.0, 1.0]. Reused across all schema files."""


class ConfidenceBreakdown(MediScanModel):
    """Per-stage confidence scores. ALL fields are required — no defaults.

    See the module docstring (decision #011) for why omitting any score
    is a validation error rather than a silent optimistic default.
    """

    ocr: Score = Field(description="Confidence of the OCR / text extraction stage.")
    extraction: Score = Field(description="Confidence of structured field extraction.")
    validation: Score = Field(description="Schema validation success signal.")
    grounding: Score = Field(
        description="Degree of RAG grounding behind AI explanations."
    )
    overall: Score = Field(
        description="Weighted overall confidence, computed by the scoring engine."
    )


class ProcessingMetadata(MediScanModel):
    """Audit trail of one pipeline run: what ran, how long, what fell back."""

    duration_ms: float | None = Field(
        default=None, description="Total pipeline processing time in milliseconds."
    )
    models_used: list[str] = Field(
        default_factory=list,  # fresh list per object
        description="AI models actually invoked during processing, in order.",
    )
    # ge=0: a negative count is impossible; the schema refuses it.
    fallback_count: int = Field(
        default=0,
        ge=0,
        description="How many times a fallback model or parser was triggered.",
    )
    ocr_engine: str | None = Field(
        default=None,
        description="Which OCR engine processed the document, if OCR ran.",
    )
