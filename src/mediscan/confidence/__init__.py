"""Confidence scoring (Sprint 7).

The hybrid confidence blend: OCR quality, extraction method, validation
success, RAG grounding, and AI fallback depth combine into a populated
ConfidenceBreakdown. Deterministic — no AI decides how much to trust the
report (#011/#006).
"""

from mediscan.confidence.scoring import (
    extraction_confidence,
    grounding_confidence,
    score_confidence,
    validation_confidence,
)

__all__ = [
    "score_confidence",
    "extraction_confidence",
    "validation_confidence",
    "grounding_confidence",
]
