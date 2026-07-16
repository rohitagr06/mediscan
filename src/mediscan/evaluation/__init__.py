"""Evaluation harness (Sprint 8.9): honest, repeatable quality metrics."""

from mediscan.evaluation.extraction import (
    EVAL_CASES,
    ExtractionMetrics,
    evaluate_extraction,
    format_extraction_report,
    run_extraction_eval,
)

__all__ = [
    "EVAL_CASES",
    "ExtractionMetrics",
    "evaluate_extraction",
    "format_extraction_report",
    "run_extraction_eval",
]
