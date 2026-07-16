"""Tests for the extraction-recall harness (Sprint 8.9)."""

from mediscan.evaluation.extraction import (
    ExtractionMetrics,
    evaluate_extraction,
    format_extraction_report,
    run_extraction_eval,
)


def test_recall_math():
    m = ExtractionMetrics(
        label="x", expected=4, matched=2, missed=("A", "B"), unexpected=()
    )
    assert m.recall == 0.5
    assert m.false_positives == 0


def test_zero_expected_is_full_recall():
    m = ExtractionMetrics(
        label="x", expected=0, matched=0, missed=(), unexpected=("Junk",)
    )
    assert m.recall == 1.0
    assert m.false_positives == 1


def test_clean_rows_full_recall():
    text = "Hemoglobin 12.5 g/dL 13.0 - 17.0\nCreatinine 0.9 mg/dL 0.7 - 1.3\n"
    m = evaluate_extraction("clean", text, {"Hemoglobin", "Creatinine"})
    assert m.matched == 2
    assert m.recall == 1.0
    assert m.missed == ()


def test_missing_expected_is_reported():
    # An expected test that isn't recovered shows up in `missed`, lowering recall.
    text = "Hemoglobin 12.5 g/dL 13.0 - 17.0\n"
    m = evaluate_extraction("partial", text, {"Hemoglobin", "Ghost Test"})
    assert m.matched == 1
    assert m.recall == 0.5
    assert m.missed == ("Ghost Test",)


def test_runner_and_formatter_work():
    results = run_extraction_eval()
    assert len(results) == 4
    labels = {r.label for r in results}
    assert labels == {
        "clean_multipanel",
        "real_world_messy",
        "real_world_multiline",
        "real_world_noise",
    }

    report = format_extraction_report(results)
    assert "Extraction-recall evaluation" in report
    assert "clean_multipanel" in report
    assert "real_world_messy" in report
    assert "Overall recall" in report


def test_noise_case_yields_no_false_positives():
    # PRECISION: real boilerplate/marketing/pregnancy-table lines must parse
    # to ZERO findings — a false finding is worse than a miss (#006).
    results = run_extraction_eval()
    noise = next(r for r in results if r.label == "real_world_noise")
    assert noise.false_positives == 0, noise.unexpected
