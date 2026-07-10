"""Adversarial + happy-path tests for the deterministic lab parser.

The parser must be TOLERANT: it turns recognizable rows into LabResults
(severity still None — parsing never judges) and everything else into
unparsed_lines, without ever crashing. These tests pin that contract,
including the lowercase-flag regression that adversarial testing caught.
"""

from mediscan.extraction.parser import parse_lab_text, parse_reference_range
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
    # a row still needs SOME printed range to be recognized (#018); one-sided
    # ranges are now allowed too (#027), but "no range at all" stays unparsed.
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


# ---------- one-sided ranges (Sprint 6.5) ----------


def test_range_helper_reads_two_sided():
    r = parse_reference_range("13.0 - 17.0")
    assert (r.low, r.high) == (13.0, 17.0)


def test_range_helper_upper_limit_only():
    # "< N" means normal is BELOW N -> N is the upper limit (high), no low.
    for token in ("< 100", "<100", "<= 100"):
        r = parse_reference_range(token)
        assert r.low is None and r.high == 100.0, token


def test_range_helper_lower_limit_only():
    # "> N" means normal is ABOVE N -> N is the lower limit (low), no high.
    for token in ("> 40", ">= 40"):
        r = parse_reference_range(token)
        assert r.low == 40.0 and r.high is None, token


def test_range_helper_tolerates_percent_unit():
    r = parse_reference_range("< 5.7 %")
    assert r.low is None and r.high == 5.7


def test_range_helper_rejects_inverted_and_negative_and_garbage():
    # inverted two-sided fails ReferenceRange validation -> None (not a crash);
    # a negative or unrecognized token is simply not a range.
    assert parse_reference_range("17 - 13") is None
    assert parse_reference_range("< -3") is None
    assert parse_reference_range("not a range") is None


def test_one_sided_upper_line_parses():
    r = parse_lab_text("LDL Cholesterol 82 mg/dL < 100").results[0]
    assert r.test_name == "LDL Cholesterol"
    assert r.value == 82.0
    assert r.reference_range.low is None
    assert r.reference_range.high == 100.0


def test_one_sided_lower_line_parses_with_flag():
    r = parse_lab_text("HDL Cholesterol 34 mg/dL > 40 L").results[0]
    assert r.reference_range.low == 40.0
    assert r.reference_range.high is None
    assert r.flag_in_report == "L"


def test_one_sided_range_does_not_swallow_a_trailing_flag():
    # REGRESSION guard: the "%"/")" optional bits must not eat the space that
    # separates a trailing flag, or a flagged one-sided row would vanish.
    r = parse_lab_text("Triglycerides 210 mg/dL < 150 H").results[0]
    assert r.reference_range.high == 150.0
    assert r.flag_in_report == "H"


def test_percent_unit_line_with_percent_in_range():
    r = parse_lab_text("Glycohemoglobin 5.4 % < 5.7 %").results[0]
    assert r.unit == "%"
    assert r.reference_range.high == 5.7


# ---------- names with digits / hyphens (Sprint 6.5) ----------


def test_name_with_digits_parses():
    # HbA1c and Free T3 contain digits — the name pattern must allow them.
    r = parse_lab_text("HbA1c 5.4 % < 5.7").results[0]
    assert r.test_name == "HbA1c"
    assert r.value == 5.4
    assert r.reference_range.high == 5.7

    r2 = parse_lab_text("Free T3 2.8 pg/mL 2.0 - 4.4").results[0]
    assert r2.test_name == "Free T3"
    assert r2.reference_range.low == 2.0
    assert r2.reference_range.high == 4.4


def test_hyphenated_name_parses():
    r = parse_lab_text("Non-HDL Cholesterol 145 mg/dL < 130 H").results[0]
    assert r.test_name == "Non-HDL Cholesterol"
    assert r.reference_range.high == 130.0
    assert r.flag_in_report == "H"


def test_numeric_header_still_unparsed():
    # widening names to allow digits must NOT start matching page headers:
    # "Page 1 of 2" has no valid value+unit+range, so it stays unparsed.
    outcome = parse_lab_text("Page 1 of 2")
    assert outcome.results == []
    assert outcome.unparsed_lines == ["Page 1 of 2"]


# ---------- real-report robustness (Sprint 6.5.2c) ----------
# These pin the formats found in a real Tata 1mg report: a trailing Method
# column, parenthesised names, an interpretive "Desirable:" descriptor before
# the range, typographic dashes, and a trailing comma.


def test_trailing_method_column_is_ignored():
    r = parse_lab_text("Hemoglobin 15.3 g/dL 13.0-17.0 Cyanide Free SLS").results[0]
    assert r.test_name == "Hemoglobin"
    assert (r.reference_range.low, r.reference_range.high) == (13.0, 17.0)
    assert r.flag_in_report is None  # "Cyanide Free SLS" is a method, not a flag


def test_parenthesised_name_parses():
    r = parse_lab_text(
        "Glycosylated Hemoglobin (HbA1c) 5.4 % 4-5.6 HPLC (NGSP certified)"
    ).results[0]
    assert r.test_name == "Glycosylated Hemoglobin (HbA1c)"
    assert (r.reference_range.low, r.reference_range.high) == (4.0, 5.6)


def test_colon_descriptor_before_range_is_ignored():
    r = parse_lab_text(
        "Cholesterol - LDL 131 mg/dL Desirable: <100 Calculated"
    ).results[0]
    assert r.test_name == "Cholesterol - LDL"
    assert r.reference_range.low is None
    assert r.reference_range.high == 100.0


def test_typographic_en_dash_range():
    # the range uses an en-dash "–" (not a hyphen); it must normalise and parse.
    r = parse_lab_text(
        "Bilirubin-Total 0.63 mg/dL 0.3 – 1.2 Vanadate oxidation"
    ).results[0]
    assert (r.reference_range.low, r.reference_range.high) == (0.3, 1.2)


def test_trailing_comma_after_range_and_short_method_not_a_flag():
    r = parse_lab_text("Triglycerides 89 mg/dL Normal: <150, GPO").results[0]
    assert r.reference_range.high == 150.0
    # "GPO" is a 3-letter METHOD, not a high/low flag — must not be captured.
    assert r.flag_in_report is None


def test_real_high_low_flag_still_detected():
    assert (
        parse_lab_text("Hemoglobin 9.8 g/dL 13.0-17.0 H").results[0].flag_in_report
        == "H"
    )
    assert (
        parse_lab_text("Hemoglobin 9.8 g/dL 13.0-17.0 L").results[0].flag_in_report
        == "L"
    )


def test_qualitative_and_prose_stay_unparsed():
    # these SHOULD NOT parse: a qualitative value, a non-numeric range, a
    # risk-word range, and ordinary comment prose. Never force a lab row.
    lines = [
        "Glucose Negative Negative GOD-POD",  # value is "Negative", not numeric
        "Estimated average glucose (eAG) 108.28 mg/dL Not established Calculated",
        "Cholesterol - HDL 47 mg/dL Undesirable/high risk Accelerator Selective",
        "As per the recommendation of International council for Standardization",
    ]
    for line in lines:
        outcome = parse_lab_text(line)
        assert outcome.results == [], line
        assert outcome.unparsed_lines == [line], line
