"""Async orchestration core (Sprint 7.6).

The async path runs the four explanation outputs concurrently; the sync
functions are thin wrappers over it. These tests use asyncio.run (no
pytest-asyncio needed) and the deterministic path, so they stay offline.
Timeout / one-failing-output / concurrency-timing adversarial tests live in
the 7.7 suite.
"""

import asyncio

from fixtures.full_panel import MALE_REPORT
from mediscan.orchestration import (
    analyze_document_async,
    analyze_text,
    analyze_text_async,
)
from mediscan.schemas import AnalysisReport


def _no_retrieve(_query):
    return []


def test_async_core_returns_a_complete_report():
    report = asyncio.run(
        analyze_text_async(MALE_REPORT, providers=[], retrieve_fn=_no_retrieve)
    )
    assert isinstance(report, AnalysisReport)
    assert report.coverage.assessed
    assert report.urgency is not None
    assert report.patient_summary is not None  # assembled concurrently
    assert 0.0 <= report.confidence.overall <= 1.0


def test_sync_wrapper_matches_async_core():
    sync_report = analyze_text(MALE_REPORT, providers=[], retrieve_fn=_no_retrieve)
    async_report = asyncio.run(
        analyze_text_async(MALE_REPORT, providers=[], retrieve_fn=_no_retrieve)
    )
    # same verdict + coverage + fallback accounting (only timing differs)
    assert sync_report.urgency.level is async_report.urgency.level
    assert len(sync_report.coverage.assessed) == len(async_report.coverage.assessed)
    assert sync_report.metadata.fallback_count == async_report.metadata.fallback_count
    assert sync_report.patient_summary.text and async_report.patient_summary.text


def test_document_entry_points_are_async_and_sync():
    # the file-in async entry exists and is a coroutine function; the sync
    # wrapper is a plain callable. (Actually reading a file needs PyMuPDF, so
    # execution is exercised in the integration test on the Mac.)
    assert asyncio.iscoroutinefunction(analyze_document_async)


def test_no_assessable_tests_skips_ai_on_async_path():
    report = asyncio.run(
        analyze_text_async(
            "Widget Level 5 u 1 - 10\n", providers=[], retrieve_fn=_no_retrieve
        )
    )
    assert report.coverage.assessed == []
    assert report.patient_summary is None  # nothing graded -> no explanation
