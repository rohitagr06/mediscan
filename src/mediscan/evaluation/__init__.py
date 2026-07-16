"""Evaluation harness (Sprint 8.9): honest, repeatable quality metrics.

Two families of offline, synthetic checks:
- extraction: parser recall/precision (8.9)
- grounding:  hallucination + confidence sanity over finished reports (8.9b)
"""

from mediscan.evaluation.extraction import (
    EVAL_CASES,
    ExtractionMetrics,
    evaluate_extraction,
    format_extraction_report,
    run_extraction_eval,
)
from mediscan.evaluation.grounding import (
    GroundingAudit,
    audit_report,
    check_confidence_sanity,
    find_ungrounded_numbers,
    find_ungrounded_test_names,
    format_grounding_report,
    grounded_numbers,
    run_grounding_eval,
)

__all__ = [
    "EVAL_CASES",
    "ExtractionMetrics",
    "evaluate_extraction",
    "format_extraction_report",
    "run_extraction_eval",
    "GroundingAudit",
    "audit_report",
    "check_confidence_sanity",
    "find_ungrounded_numbers",
    "find_ungrounded_test_names",
    "format_grounding_report",
    "grounded_numbers",
    "run_grounding_eval",
]
