"""Tests for the reference-range knowledge-base loader."""

from mediscan.extraction.normalization import normalize_test_name
from mediscan.medical.reference_data import load_reference_ranges
from mediscan.schemas import ReferenceRangeEntry


def test_loads_the_cbc_panel():
    kb = load_reference_ranges()
    assert len(kb) >= 5
    for name, entry in kb.items():
        assert isinstance(entry, ReferenceRangeEntry)
        assert entry.test_name == name  # keyed by its own canonical name


def test_hemoglobin_range_is_present_and_correct():
    kb = load_reference_ranges()
    hb = kb["Hemoglobin"]
    # Hemoglobin is now sex-aware: male/female blocks, not flat bounds.
    assert (hb.male.low, hb.male.high) == (13.0, 17.0)
    assert (hb.female.low, hb.female.high) == (12.0, 15.0)
    assert hb.male.critical_low == 7.0 and hb.male.critical_high == 20.0


def test_kb_keys_match_normalization_output():
    # THE COUPLING TEST: every KB key must be reachable via normalization,
    # or the engine's lookup would silently miss. This guards the contract
    # between the synonym map and the KB (Sprint 4.4 note).
    kb = load_reference_ranges()
    for canonical_name in kb:
        assert normalize_test_name(canonical_name) == canonical_name
