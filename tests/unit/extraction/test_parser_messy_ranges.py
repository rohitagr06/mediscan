"""Parser tests for messy real-world range formats (Sprint 8.9).

The real Tata 1mg report prints ranges with descriptive prefixes and glued
units that the strict grammar missed. These lock the recall fix in — and one
precision test guards against the relaxed descriptor eating ordinary prose.
"""

from mediscan.extraction.parser import parse_lab_text


def _names(text: str) -> set[str]:
    return {r.test_name for r in parse_lab_text(text).results}


def test_word_prefixed_two_sided_range_parses():
    # Real glucose row: range prefixed with a word + trailing comma.
    outcome = parse_lab_text("Glucose- Random 80 mg/dL Normal - 70 - 140,")
    names = {r.test_name for r in outcome.results}
    assert "Glucose- Random" in names
    row = next(r for r in outcome.results if r.test_name == "Glucose- Random")
    assert row.value == 80.0
    assert row.reference_range is not None
    assert row.reference_range.low == 70.0
    assert row.reference_range.high == 140.0


def test_descriptive_wrapped_glued_one_sided_range_parses():
    # Real HDL row: descriptive prefix + one-sided range with a GLUED unit.
    outcome = parse_lab_text(
        "Cholesterol - HDL 47 mg/dL Undesirable/high risk <40mg/dL"
    )
    names = {r.test_name for r in outcome.results}
    assert "Cholesterol - HDL" in names
    row = next(r for r in outcome.results if r.test_name == "Cholesterol - HDL")
    assert row.value == 47.0
    assert row.reference_range is not None
    assert row.reference_range.high == 40.0  # "< 40" -> upper bound


def test_prose_sentence_is_not_parsed_as_a_lab_row():
    # PRECISION: a comment sentence with numbers must NOT become a finding.
    assert _names("The variation is of the order of 50%, hence time of day.") == set()
    assert _names("1st trimester 0.1-2.5 0.81-1.90 7.33-14.8") == set()
