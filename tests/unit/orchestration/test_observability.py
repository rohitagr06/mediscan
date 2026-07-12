"""Observability wiring through the orchestrator (Sprint 7.12).

The pipeline emits a metrics trail — parse counts, coverage counts, fallback
depth, final confidence, duration — but it must NEVER log Protected Health
Information: no report text, test names, or patient values (#010). This proves
both: the metrics event IS logged, and NO PHI ever lands in a log record.
"""

import logging

from fixtures.full_panel import MALE_REPORT
from mediscan.orchestration import analyze_text


def _no_retrieve(_query):
    return []


def _run_and_capture(caplog):
    with caplog.at_level(logging.DEBUG, logger="mediscan"):
        analyze_text(MALE_REPORT, providers=[], retrieve_fn=_no_retrieve)
    return "\n".join(r.getMessage() for r in caplog.records)


def test_completion_metrics_are_logged(caplog):
    blob = _run_and_capture(caplog)
    assert "analysis complete" in blob
    assert "overall_confidence=" in blob
    assert "duration_ms=" in blob
    # stage debug lines are present too
    assert "parsed" in blob and "coverage:" in blob


def test_no_phi_in_any_log_record(caplog):
    blob = _run_and_capture(caplog)
    # MALE_REPORT contains these patient values, test names, and header text —
    # none of them may EVER appear in a log line (events/metrics only, #010).
    for needle in (
        "12.5",  # a Hemoglobin value
        "245",  # a Total Cholesterol value
        "165",  # an LDL value
        "Synthetic Patient",  # the report's name header
        "Hemoglobin",  # a test name
        "CEA",  # an acknowledged (sensitive) test name
    ):
        assert needle not in blob, f"PHI leak: {needle!r} found in a log record"


def test_counts_not_values_in_the_coverage_log(caplog):
    # the coverage line reports how MANY tests, never WHICH tests
    blob = _run_and_capture(caplog)
    assert "assessed=" in blob and "acknowledged=" in blob
