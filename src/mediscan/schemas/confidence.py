from typing import Annotated

from pydantic import BaseModel, Field

Score = Annotated[float, Field(ge=0.0, le=1.0)]
"""A confidence score bounded to [0.0, 1.0]. Reused across all schema files."""


class ConfidenceBreakdown(BaseModel):
    """All scores are REQUIRED — no defaults, by design (decision #011).

    An unscored pipeline must never masquerade as a confident one. If a
    ConfidenceBreakdown exists at all, every score in it was set explicitly.
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


class ProcessingMetadata(BaseModel):
    duration_ms: float | None = Field(
        default=None, description="Total pipeline processing time in milliseconds."
    )
    models_used: list[str] = Field(
        default_factory=list,
        description="AI models actually invoked during processing, in order.",
    )
    fallback_count: int = Field(
        default=0,
        ge=0,
        description="How many times a fallback model or parser was triggered.",
    )
    ocr_engine: str | None = Field(
        default=None,
        description="Which OCR engine processed the document, if OCR ran.",
    )
