"""Normalization helpers for laboratory test names and units.

WHY THIS FILE EXISTS
    Medical laboratories use different names and unit spellings for the
    same laboratory test. This module maps those variations to a single
    canonical form so downstream components (range resolution, the
    assessment allowlist, and KB lookup) can key on ONE name.

    Normalization is intentionally tolerant. Unknown names and units are
    returned unchanged rather than guessed or discarded.

CANONICAL NAMES ARE A CONTRACT
    The RIGHT-hand values below are the canonical test names. The KB files
    (reference_ranges/*.json, test_knowledge/*.json) and the assessment
    policy MUST use these exact strings as their keys, or a real test won't
    resolve. When you add a test, decide its canonical name HERE first.
"""

import re


def _canonical_key(name: str) -> str:
    """Normalise a name into the lookup-key form used by the synonym map.

    Lowercases, collapses runs of whitespace to a single space, and
    standardises comma spacing to ", " so that "VLDL Cholesterol,Calculated"
    and "VLDL Cholesterol, Calculated" both match one stored key. This keeps
    the map small without needing an entry for every spacing quirk.
    """
    key = " ".join(name.strip().lower().split())  # lowercase + collapse spaces
    return re.sub(r"\s*,\s*", ", ", key)  # standardise comma spacing


# Alias (already in _canonical_key form) -> canonical laboratory test name.
#
# Data, not logic. Extend this mapping as support for more tests is added.
# Real-report variants (British spellings, "(TLC)" abbreviations, ", Calculated"
# suffixes, "Cholesterol - LDL" ordering) are included where observed.
_TEST_NAME_SYNONYMS: dict[str, str] = {
    # --- CBC (existing + real-report spellings) ---
    "hb": "Hemoglobin",
    "hgb": "Hemoglobin",
    "haemoglobin": "Hemoglobin",
    "hemoglobin": "Hemoglobin",
    "tlc": "Total Leukocyte Count",
    "total leukocyte count": "Total Leukocyte Count",
    "total leucocyte count": "Total Leukocyte Count",  # British spelling
    "total leukocyte count (tlc)": "Total Leukocyte Count",
    "total leucocyte count (tlc)": "Total Leukocyte Count",
    "wbc": "Total Leukocyte Count",
    "white blood cell count": "Total Leukocyte Count",
    "platelet count": "Platelet Count",
    "platelets": "Platelet Count",
    "plt": "Platelet Count",
    "hematocrit": "Hematocrit",
    "haematocrit": "Hematocrit",
    "hct": "Hematocrit",
    "pcv": "Hematocrit",
    "packed cell volume": "Hematocrit",
    "packed cell volume (pcv)": "Hematocrit",
    "hematocrit value, hct": "Hematocrit",
    "mcv": "MCV",
    "mean corpuscular volume": "MCV",
    "mean corpuscular volume, mcv": "MCV",
    # --- Lipids ---
    "cholesterol": "Total Cholesterol",
    "total cholesterol": "Total Cholesterol",
    "cholesterol - total": "Total Cholesterol",
    "cholesterol, total": "Total Cholesterol",
    "serum cholesterol": "Total Cholesterol",
    "triglycerides": "Triglycerides",
    "triglyceride": "Triglycerides",
    "tg": "Triglycerides",
    "hdl": "HDL Cholesterol",
    "hdl cholesterol": "HDL Cholesterol",
    "cholesterol - hdl": "HDL Cholesterol",
    "ldl": "LDL Cholesterol",
    "ldl cholesterol": "LDL Cholesterol",
    "cholesterol - ldl": "LDL Cholesterol",
    "ldl cholesterol, calculated": "LDL Cholesterol",
    "vldl": "VLDL Cholesterol",
    "vldl cholesterol": "VLDL Cholesterol",
    "cholesterol- vldl": "VLDL Cholesterol",
    "cholesterol - vldl": "VLDL Cholesterol",
    "vldl cholesterol, calculated": "VLDL Cholesterol",
    "non hdl cholesterol": "Non-HDL Cholesterol",
    "non-hdl cholesterol": "Non-HDL Cholesterol",
    # --- Glucose / HbA1c ---
    "fasting glucose": "Fasting Glucose",
    "glucose fasting": "Fasting Glucose",
    "glucose - fasting": "Fasting Glucose",
    "fasting blood glucose": "Fasting Glucose",
    "fbg": "Fasting Glucose",
    "postprandial glucose": "Postprandial Glucose",
    "post prandial glucose": "Postprandial Glucose",
    "glucose pp": "Postprandial Glucose",
    "glucose - pp": "Postprandial Glucose",
    "ppbg": "Postprandial Glucose",
    "hba1c": "HbA1c",
    "hba1c (glycosylated hemoglobin)": "HbA1c",
    "glycosylated hemoglobin": "HbA1c",
    "glycosylated hemoglobin (hba1c)": "HbA1c",
    "glycated hemoglobin": "HbA1c",
    "glycohemoglobin": "HbA1c",
    # --- Thyroid ---
    "tsh": "TSH",
    "thyroid stimulating hormone": "TSH",
    "thyroid stimulating hormone - ultra": "TSH",
    "free t3": "Free T3",
    "ft3": "Free T3",
    "free triiodothyronine": "Free T3",
    "free t4": "Free T4",
    "ft4": "Free T4",
    "free thyroxine": "Free T4",
    # --- Kidney (KFT) ---
    "creatinine": "Creatinine",
    "serum creatinine": "Creatinine",
    "urea": "Urea",
    "blood urea": "Urea",
    "bun": "Blood Urea Nitrogen",
    "blood urea nitrogen": "Blood Urea Nitrogen",
    "urea nitrogen blood": "Blood Urea Nitrogen",
    "uric acid": "Uric Acid",
    "serum uric acid": "Uric Acid",
}


# Alias (lowercase) -> canonical unit. Data, not logic. Unknown units pass
# through unchanged.
_UNIT_SYNONYMS: dict[str, str] = {
    "g/dl": "g/dL",
    "gm/dl": "g/dL",
    "10^3/ul": "10^3/uL",
    "10*3/ul": "10^3/uL",
    "%": "%",
    "fl": "fL",
    "mg/dl": "mg/dL",
    "u/l": "U/L",
    "iu/l": "IU/L",
    "meq/l": "mEq/L",
    "mmol/l": "mmol/L",
    "uiu/ml": "uIU/mL",
    "pg/ml": "pg/mL",
    "ng/ml": "ng/mL",
    "ng/dl": "ng/dL",
    "iu/ml": "IU/mL",
}


def normalize_test_name(name: str) -> str:
    """Return the canonical name for a lab test, or the input unchanged.

    Lookup is case-, whitespace-, and comma-spacing-insensitive. Unknown
    names pass through untouched — we never drop or guess a test we don't
    know (it becomes an 'acknowledged, not assessed' test downstream).
    """
    return _TEST_NAME_SYNONYMS.get(_canonical_key(name), name)


def normalize_unit(unit: str | None) -> str | None:
    """Canonicalize a unit string. None passes through as None.

    Lookup is case-insensitive and ignores surrounding whitespace.
    Unknown units are returned unchanged. None is preserved.
    """
    if unit is None:
        return None

    lookup_key = unit.strip().lower()

    return _UNIT_SYNONYMS.get(lookup_key, unit)
