"""End-to-end tests for the synchronous orchestrator core (Sprint 7.4).

analyze_text runs the WHOLE pipeline on already-extracted text — parse ->
sex -> coverage -> urgency -> explanations -> confidence -> assembled
AnalysisReport. Everything here uses providers=[] (deterministic path, no AI)
and an injected no-op retriever, so it's fully offline.
"""

from fixtures.full_panel import MALE_REPORT
from mediscan.orchestration import analyze_text
from mediscan.schemas import AnalysisReport, UrgencyLevel


def _no_retrieve(_query):
    return []


def _run(text):
    return analyze_text(text, providers=[], retrieve_fn=_no_retrieve)


# --- the milestone: text -> a complete AnalysisReport ----------------------


def test_full_panel_becomes_a_complete_report():
    report = _run(MALE_REPORT)

    assert isinstance(report, AnalysisReport)
    assert report.lab_results  # raw audit rows present
    assert report.coverage is not None
    assert report.coverage.assessed  # graded findings
    assert report.urgency is not None
    assert report.confidence is not None
    assert 0.0 <= report.confidence.overall <= 1.0
    assert report.metadata is not None
    assert report.metadata.duration_ms is not None and report.metadata.duration_ms >= 0
    # assessed findings exist -> deterministic explanations were assembled
    assert report.patient_summary is not None
    assert report.doctor_summary is not None
    assert report.disclaimer  # never removable


def test_acknowledged_tests_are_surfaced_but_never_move_urgency():
    report = _run(MALE_REPORT)
    ack_names = {a.test_name for a in report.coverage.acknowledged}
    # CEA (sensitive), hs-CRP (deferred), Ferritin (unknown) are acknowledged
    assert "CEA" in ack_names
    # and none of them influenced the deterministic verdict (#006)
    assert "CEA" not in report.urgency.contributing_tests


def test_deterministic_path_confidence_reflects_full_fallback():
    report = _run(MALE_REPORT)
    # providers=[] -> all four explanations fell back to templates
    assert report.metadata.fallback_count == 4
    assert report.metadata.models_used == []  # no AI model answered
    # grounding stays high (no AI outputs to be ungrounded), but the fallback
    # penalty pulls overall below a perfect 1.0
    assert report.confidence.overall < 1.0


def test_report_with_no_assessable_tests_still_valid():
    # an unknown test -> acknowledged-numeric, nothing graded -> no AI, no
    # summaries, but a complete, valid report with a ROUTINE verdict.
    report = _run("Widget Level 5 u 1 - 10\n")

    assert report.coverage.assessed == []
    assert report.patient_summary is None
    assert report.dietary_considerations == []
    assert report.urgency.level is UrgencyLevel.ROUTINE
    assert report.confidence is not None


def test_provenance_is_deterministic_on_the_no_ai_path():
    # a sanity check that with no providers, explanations came from templates
    report = _run(MALE_REPORT)
    # patient_summary is a validated PatientSummary object with text
    assert report.patient_summary.text
    # (the provenance itself is asserted in the explanation-assembly tests;
    # here we just confirm the assembled report carries real content)
