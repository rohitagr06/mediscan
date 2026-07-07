"""Normalization helpers for laboratory test names and units.

WHY THIS FILE EXISTS
    Medical laboratories use different names and unit spellings for the
    same laboratory test. This module maps those variations to a single
    canonical form so downstream components can perform deterministic
    knowledge-base lookups.

    Normalization is intentionally tolerant. Unknown names and units are
    returned unchanged rather than guessed or discarded.
"""

# Alias (lowercase) -> canonical laboratory test name.
#
# Data, not logic. Extend this mapping as support for additional
# laboratory tests is added.
_TEST_NAME_SYNONYMS: dict[str, str] = {
    "hb": "Hemoglobin",
    "hgb": "Hemoglobin",
    "haemoglobin": "Hemoglobin",
    "hemoglobin": "Hemoglobin",
    "tlc": "Total Leukocyte Count",
    "total leukocyte count": "Total Leukocyte Count",
    "wbc": "Total Leukocyte Count",
    "white blood cell count": "Total Leukocyte Count",
    "platelet count": "Platelet Count",
    "platelets": "Platelet Count",
    "plt": "Platelet Count",
    "hematocrit": "Hematocrit",
    "haematocrit": "Hematocrit",
    "hct": "Hematocrit",
    "pcv": "Hematocrit",
    "mcv": "MCV",
    "mean corpuscular volume": "MCV",
}


# Alias (lowercase) -> canonical unit.
#
# Data, not logic. Unknown units pass through unchanged.
_UNIT_SYNONYMS: dict[str, str] = {
    "g/dl": "g/dL",
    "gm/dl": "g/dL",
    "10^3/ul": "10^3/uL",
    "10*3/ul": "10^3/uL",
    "%": "%",
    "fl": "fL",
}


def normalize_test_name(name: str) -> str:
    """Return the canonical name for a lab test, or the input unchanged.

    Lookup is case- and whitespace-insensitive. Unknown names pass
    through untouched — we never drop or guess a test we don't know.
    """
    lookup_key = name.strip().lower()

    return _TEST_NAME_SYNONYMS.get(lookup_key, name)


def normalize_unit(unit: str | None) -> str | None:
    """Canonicalize a unit string. None passes through as None.

    Lookup is case-insensitive and ignores surrounding whitespace.
    Unknown units are returned unchanged. None is preserved.
    """
    if unit is None:
        return None

    lookup_key = unit.strip().lower()

    return _UNIT_SYNONYMS.get(lookup_key, unit)
