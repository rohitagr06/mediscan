"""Unit tests for normalization helpers."""

from mediscan.extraction.normalization import (
    normalize_test_name,
    normalize_unit,
)


def test_known_test_name_synonyms_normalize() -> None:
    assert normalize_test_name("Hb") == "Hemoglobin"
    assert normalize_test_name("HGB") == "Hemoglobin"
    assert normalize_test_name("haemoglobin") == "Hemoglobin"
    assert normalize_test_name("WBC") == "Total Leukocyte Count"
    assert normalize_test_name("PLT") == "Platelet Count"


def test_normalize_test_name_is_case_and_whitespace_insensitive() -> None:
    assert normalize_test_name("  hGb  ") == "Hemoglobin"


def test_unknown_test_name_passes_through_unchanged() -> None:
    assert normalize_test_name("Ferritin") == "Ferritin"


def test_known_units_normalize() -> None:
    assert normalize_unit("gm/dl") == "g/dL"
    assert normalize_unit("10*3/uL") == "10^3/uL"
    assert normalize_unit("Fl") == "fL"


def test_unknown_unit_passes_through_unchanged() -> None:
    assert normalize_unit("mg/dL") == "mg/dL"


def test_none_unit_is_preserved() -> None:
    assert normalize_unit(None) is None


def test_normalize_unit_is_case_and_whitespace_insensitive() -> None:
    assert normalize_unit("  G/DL  ") == "g/dL"
