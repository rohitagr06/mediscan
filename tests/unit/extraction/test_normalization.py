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


# --- first-wave synonyms, using the REAL report name variants (6.5.4) ---


def test_real_cbc_spelling_variants_normalize() -> None:
    # British spelling + parenthetical abbreviation seen in Tata / Lal reports
    assert normalize_test_name("Total Leucocyte Count") == "Total Leukocyte Count"
    assert normalize_test_name("Total Leukocyte Count (TLC)") == "Total Leukocyte Count"
    assert normalize_test_name("Packed Cell Volume (PCV)") == "Hematocrit"
    assert normalize_test_name("HEMATOCRIT VALUE, HCT") == "Hematocrit"


def test_lipid_name_variants_normalize() -> None:
    assert normalize_test_name("Cholesterol - Total") == "Total Cholesterol"
    assert normalize_test_name("Cholesterol - LDL") == "LDL Cholesterol"
    assert normalize_test_name("LDL Cholesterol, Calculated") == "LDL Cholesterol"
    # comma-spacing quirk ("VLDL Cholesterol,Calculated") must still match
    assert normalize_test_name("VLDL Cholesterol,Calculated") == "VLDL Cholesterol"
    assert normalize_test_name("Non HDL Cholesterol") == "Non-HDL Cholesterol"


def test_glucose_and_hba1c_variants_normalize() -> None:
    assert normalize_test_name("Glycosylated Hemoglobin (HbA1c)") == "HbA1c"
    assert normalize_test_name("HbA1c") == "HbA1c"
    assert normalize_test_name("Glucose Fasting") == "Fasting Glucose"


def test_thyroid_and_kft_variants_normalize() -> None:
    assert normalize_test_name("Thyroid Stimulating Hormone - Ultra") == "TSH"
    assert normalize_test_name("Free T3") == "Free T3"
    assert normalize_test_name("Urea Nitrogen Blood") == "Blood Urea Nitrogen"
    assert normalize_test_name("Serum Creatinine") == "Creatinine"


def test_first_wave_units_normalize() -> None:
    assert normalize_unit("mg/dl") == "mg/dL"
    assert normalize_unit("U/L") == "U/L"
    assert normalize_unit("uIU/ml") == "uIU/mL"
