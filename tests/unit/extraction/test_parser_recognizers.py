"""Unit tests for the individual parser recognizers (Sprint 7.8).

The 7.8 refactor split parse_lab_text's inline logic into small recognizers.
The payoff is that each can now be tested in ISOLATION — the cases that were
previously only reachable through a full line now have direct, named tests.
(The whole-line behaviour is still pinned by test_parser.py, unchanged.)
"""

from mediscan.extraction.parser import (
    _recognize_flag,
    _recognize_name,
    _recognize_number,
    parse_reference_range,
)
from mediscan.schemas import ReferenceRange

# --- number recognizer -----------------------------------------------------


def test_number_strips_thousands_commas():
    assert _recognize_number("10,800") == "10800"
    assert _recognize_number("9.8") == "9.8"
    assert _recognize_number("250") == "250"


# --- name recognizer -------------------------------------------------------


def test_name_keeps_a_normal_single_spaced_name():
    assert _recognize_name("Total Leukocyte Count") == "Total Leukocyte Count"


def test_name_truncates_at_a_multi_space_gap():
    # a stray token glued across column padding is dropped
    assert _recognize_name("T3, Total          R") == "T3, Total"


def test_name_rejects_a_lone_character():
    # a one-letter leftover from a wrapped header is not a real name
    assert _recognize_name("R") is None
    assert _recognize_name("A          B") is None  # first segment "A" too short


def test_name_accepts_a_two_character_name():
    assert _recognize_name("Hb") == "Hb"


# --- flag recognizer -------------------------------------------------------


def test_flag_preflag_takes_precedence():
    assert _recognize_flag("H", "L") == "H"


def test_flag_reads_a_trailing_marker():
    assert _recognize_flag(None, "L") == "L"
    assert _recognize_flag(None, "HH") == "HH"
    assert _recognize_flag(None, "*") == "*"


def test_flag_ignores_a_method_column():
    # a long trailing token is a Method name, never a flag
    assert _recognize_flag(None, "Cyanide Free SLS") is None
    assert _recognize_flag(None, "GPO") is None


def test_flag_none_when_absent():
    assert _recognize_flag(None, None) is None


# --- range recognizer (a couple of direct cases) ---------------------------


def test_range_two_sided_and_one_sided():
    assert parse_reference_range("13.0 - 17.0") == ReferenceRange(low=13.0, high=17.0)
    assert parse_reference_range("< 100") == ReferenceRange(high=100.0)
    assert parse_reference_range("> 40") == ReferenceRange(low=40.0)


def test_range_unrecognized_is_none():
    assert parse_reference_range("not a range") is None
