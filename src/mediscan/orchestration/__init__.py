"""Pipeline orchestration (Sprint 7).

The conductor that runs every stage end to end and assembles the single
`AnalysisReport`. `analyze_text` is the fully-testable core (text in, report
out, all deps injectable); `analyze_document` is the thin front that reads a
file into text first. See docs/15-sprint-7-plan.md.
"""

from mediscan.orchestration.pipeline import (
    analyze_document,
    analyze_document_async,
    analyze_text,
    analyze_text_async,
)

__all__ = [
    "analyze_text",
    "analyze_text_async",
    "analyze_document",
    "analyze_document_async",
]
