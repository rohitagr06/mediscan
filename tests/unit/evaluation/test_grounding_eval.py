"""Tests for the grounding + confidence-sanity eval (Sprint 8.9b).

These lock the two safety audits: the detector must pass a faithful
deterministic report and CATCH a tampered one, and the confidence-sanity
invariants must fire on the states they're meant to guard.
"""

from types import SimpleNamespace

from mediscan.evaluation.grounding import (
    audit_report,
    check_confidence_sanity,
    find_ungrounded_test_names,
    grounded_numbers,
    run_grounding_eval,
)
from mediscan.orchestration.pipeline import analyze_text


def _by_label(audits):
    return {a.label: a for a in audits}


# --- the end-to-end eval cases ---------------------------------------------


def test_faithful_deterministic_report_audits_clean():
    audits = _by_label(run_grounding_eval())
    faithful = audits["faithful_deterministic"]
    assert faithful.ungrounded_numbers == ()
    assert faithful.ungrounded_test_names == ()
    assert faithful.confidence_problems == ()
    assert faithful.is_clean


def test_tampered_report_is_caught():
    audits = _by_label(run_grounding_eval())
    tampered = audits["tampered_hallucination"]
    # the injected value 999.0 has no grounding
    assert 999.0 in tampered.ungrounded_numbers
    # PSA was never tested, yet the summary names it
    assert "PSA" in tampered.ungrounded_test_names
    assert not tampered.is_clean


# --- grounded_numbers content ----------------------------------------------


def test_grounded_numbers_includes_values_bounds_and_counts():
    report = analyze_text(
        "LDL Cholesterol 131 mg/dL < 100\nUric Acid 8.5 mg/dL 3.5 - 7.2\n",
        providers=[],
        retrieve_fn=lambda _q: [],
    )
    nums = grounded_numbers(report)
    assert 131.0 in nums and 8.5 in nums  # values
    assert 100.0 in nums and 7.2 in nums  # range bounds
    assert 2.0 in nums  # structural count: 2 abnormal findings


# --- test-name grounding does not false-positive on substrings -------------


def test_urea_not_flagged_inside_blood_urea_nitrogen():
    # "Blood Urea Nitrogen" is grounded; the vocabulary also contains the
    # distinct name "Urea". The word "Urea" appears inside the grounded name,
    # so it must NOT be reported as an ungrounded/hallucinated test.
    report = analyze_text(
        "Blood Urea Nitrogen 8 mg/dL 9 - 23\n",
        providers=[],
        retrieve_fn=lambda _q: [],
    )
    assert "Urea" not in find_ungrounded_test_names(report)


# --- confidence-sanity invariants (checker tested in isolation) ------------


def _conf(**kw):
    base = dict(ocr=1.0, extraction=1.0, validation=1.0, grounding=1.0, overall=1.0)
    base.update(kw)
    return SimpleNamespace(**base)


def test_confidence_sane_report_has_no_problems():
    rep = SimpleNamespace(confidence=_conf(overall=0.8), lab_results=[object()])
    assert check_confidence_sanity(rep) == ()


def test_confidence_empty_results_must_be_zero():
    rep = SimpleNamespace(confidence=_conf(overall=0.5), lab_results=[])
    problems = check_confidence_sanity(rep)
    assert any("must be 0.0" in p for p in problems)


def test_confidence_scores_must_be_in_range():
    rep = SimpleNamespace(confidence=_conf(overall=1.5), lab_results=[object()])
    problems = check_confidence_sanity(rep)
    assert any("outside [0, 1]" in p for p in problems)


def test_confidence_overall_cannot_exceed_best_component():
    rep = SimpleNamespace(
        confidence=_conf(
            ocr=0.2, extraction=0.2, validation=0.2, grounding=0.2, overall=0.9
        ),
        lab_results=[object()],
    )
    problems = check_confidence_sanity(rep)
    assert any("exceeds best component" in p for p in problems)


def test_audit_report_wraps_all_three_checks():
    report = analyze_text(
        "Hemoglobin 15.3 g/dL 13.0 - 17.0\n",
        providers=[],
        retrieve_fn=lambda _q: [],
    )
    audit = audit_report("smoke", report)
    assert audit.label == "smoke"
    assert audit.is_clean  # a single in-range value, faithful summary
