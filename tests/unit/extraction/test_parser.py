"""Adversarial + happy-path tests for the deterministic lab parser.

The parser must be TOLERANT: it turns recognizable rows into LabResults
(severity still None — parsing never judges) and everything else into
unparsed_lines, without ever crashing. These tests pin that contract,
including the lowercase-flag regression that adversarial testing caught.
"""

from mediscan.extraction.parser import parse_lab_text
from mediscan.schemas import ParseOutcome

# ---------- happy paths ----------


def test_parses_a_full_cbc_panel():
    text = (
        "Hemoglobin 9.8 g/dL (13.0 - 17.0) L\n"
        "Total Leukocyte Count 11.2 10^3/uL (4.0 - 11.0) H\n"
        "Platelet Count 250 10^3/uL (150 - 410)"
    )
    outcome = parse_lab_text(text)
    assert isinstance(outcome, ParseOutcome)
    assert len(outcome.results) == 3
    assert outcome.unparsed_lines == []


def test_parser_never_judges():
    # every parsed result must have severity STILL None (parse != judge)
    outcome = parse_lab_text("Hemoglobin 9.8 g/dL (13.0 - 17.0) L")
    assert outcome.results[0].severity is None


def test_extracts_fields_correctly():
    r = parse_lab_text("Hemoglobin 9.8 g/dL (13.0 - 17.0) L").results[0]
    assert r.test_name == "Hemoglobin"
    assert r.value == 9.8
    assert r.unit == "g/dL"
    assert r.reference_range.low == 13.0
    assert r.reference_range.high == 17.0
    assert r.flag_in_report == "L"


def test_integer_value_coerced_to_float():
    r = parse_lab_text("Platelet Count 250 10^3/uL (150 - 410)").results[0]
    assert r.value == 250.0
    assert r.flag_in_report is None


def test_tolerates_extra_whitespace_and_missing_parens():
    a = parse_lab_text("Hemoglobin    9.8   g/dL   ( 13.0 - 17.0 )  L")
    b = parse_lab_text("Hemoglobin 9.8 g/dL 13.0 - 17.0 L")  # no parens
    assert len(a.results) == 1
    assert len(b.results) == 1


# ---------- tolerance / adversarial ----------


def test_lowercase_flag_does_not_drop_the_row():
    # REGRESSION: a lowercase flag once dropped the entire row (a lab
    # value lost over a case quirk in an OPTIONAL field). Must not recur.
    outcome = parse_lab_text("Hemoglobin 9.8 g/dL (13.0 - 17.0) h")
    assert len(outcome.results) == 1
    assert outcome.results[0].flag_in_report == "h"


def test_headers_and_page_numbers_are_unparsed_not_results():
    text = (
        "DipsAl Diagnostics (SYNTHETIC)\n" "COMPLETE BLOOD COUNT (CBC)\n" "Page 1 of 2"
    )
    outcome = parse_lab_text(text)
    assert outcome.results == []
    assert len(outcome.unparsed_lines) == 3


def test_backwards_range_becomes_unparsed_not_crash():
    # matched the shape but failed ReferenceRange validation -> unparsed,
    # never an exception (parse/judge boundary defends itself)
    outcome = parse_lab_text("Hemoglobin 9.8 g/dL (17.0 - 13.0) L")
    assert outcome.results == []
    assert len(outcome.unparsed_lines) == 1


def test_empty_and_blank_input_is_empty_outcome():
    assert parse_lab_text("") == ParseOutcome()
    assert parse_lab_text("\n   \n\t\n") == ParseOutcome()


def test_line_without_reference_range_is_unparsed():
    # documented RC1 limitation (decision #018): rows need a two-sided
    # range to be recognized.
    outcome = parse_lab_text("Hemoglobin 9.8 g/dL")
    assert outcome.results == []
    assert outcome.unparsed_lines == ["Hemoglobin 9.8 g/dL"]


def test_mixed_document_parses_only_the_lab_rows():
    text = (
        "PATIENT: TEST (SYNTHETIC)\n"
        "Hemoglobin 9.8 g/dL (13.0 - 17.0) L\n"
        "-- method notes --\n"
        "Platelet Count 250 10^3/uL (150 - 410)\n"
        "Page 2 of 2"
    )
    outcome = parse_lab_text(text)
    assert len(outcome.results) == 2
    assert len(outcome.unparsed_lines) == 3
    # parsing never judges: severities remain None
    assert all(r.severity is None for r in outcome.results)
