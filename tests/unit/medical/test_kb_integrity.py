"""Cross-layer KB integrity checks (Sprint 6.5.10).

Per-entry validity is already enforced by the Pydantic schemas at LOAD time
(a low >= high, or a critical threshold on the wrong side of a normal bound,
fails loudly on startup). These tests guard something the schemas cannot
see: the CONTRACTS *between* the three data layers that must move in
lockstep —

  * the assessment POLICY            (medical/coverage.py, `_POLICY_DATA`)
  * the reference-range KB           (knowledge_base/reference_ranges/*.json)
  * the test-knowledge KB            (knowledge_base/test_knowledge/*.json)

Drift between them is silent and dangerous. A Tier-A test that loses its
reference-range entry doesn't error — it quietly falls through to
"acknowledged" and is never graded. A KB entry whose name stops normalizing
to itself is simply never found. These tests turn that silent drift into a
loud, specific failure.

Everything here is chromadb-free, so it runs in the fast suite.
"""

import pytest
from pydantic import ValidationError

from mediscan.extraction.normalization import normalize_test_name, normalize_unit
from mediscan.medical.coverage import assessable_test_names, policy_test_names
from mediscan.medical.reference_data import load_reference_ranges
from mediscan.rag.index import load_test_knowledge
from mediscan.schemas import ReferenceRangeEntry


def _knowledge_names() -> list[str]:
    """Canonical test_name of every test-knowledge entry (with duplicates)."""
    return [tk.test_name for tk in load_test_knowledge()]


# --- no duplicates within a layer ------------------------------------------


def test_no_duplicate_knowledge_names() -> None:
    """Two knowledge entries for one test would double-count in retrieval.

    (The reference-range loader already RAISES on a duplicate name; the
    test-knowledge loader doesn't, so we assert it here.)
    """
    names = _knowledge_names()
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, f"duplicate test-knowledge entries for: {dupes}"


# --- every KB name is reachable via normalization --------------------------


def test_reference_range_names_normalize_to_themselves() -> None:
    # A KB key that isn't its own canonical form can never be looked up.
    for name in load_reference_ranges():
        assert normalize_test_name(name) == name, (
            f"reference-range key {name!r} is not canonical "
            f"(normalizes to {normalize_test_name(name)!r})"
        )


def test_knowledge_names_normalize_to_themselves() -> None:
    for name in _knowledge_names():
        assert normalize_test_name(name) == name, (
            f"test-knowledge key {name!r} is not canonical "
            f"(normalizes to {normalize_test_name(name)!r})"
        )


# --- units are stored in canonical form ------------------------------------


def test_reference_range_units_are_canonical() -> None:
    # A non-canonical unit (e.g. "gm/dl" instead of "g/dL") would drift from
    # what the parser normalizes report units to, and display inconsistently.
    for name, entry in load_reference_ranges().items():
        if entry.unit is not None:
            assert normalize_unit(entry.unit) == entry.unit, (
                f"{name}: unit {entry.unit!r} is not canonical "
                f"(should be {normalize_unit(entry.unit)!r})"
            )


# --- the orphan checks: policy <-> KB coupling -----------------------------
#
# Every Tier-A (graded) test needs BOTH a reference range (to band the value)
# and a knowledge entry (to explain it). And every KB entry needs a policy
# row that makes it Tier-A — otherwise it is dead data nothing can reach.


def test_every_assessable_test_has_a_reference_range() -> None:
    assessable = assessable_test_names()
    ranges = set(load_reference_ranges())
    missing = sorted(assessable - ranges)
    assert not missing, (
        f"Tier-A tests with no reference range (would silently NOT be graded): "
        f"{missing}"
    )


def test_every_assessable_test_has_a_knowledge_entry() -> None:
    assessable = assessable_test_names()
    knowledge = set(_knowledge_names())
    missing = sorted(assessable - knowledge)
    assert not missing, (
        f"Tier-A tests with no knowledge entry (would grade but not explain): "
        f"{missing}"
    )


def test_no_orphan_reference_range() -> None:
    # A reference-range entry for a test the policy never grades is dead data.
    ranges = set(load_reference_ranges())
    orphans = sorted(ranges - assessable_test_names())
    assert not orphans, (
        f"reference-range entries with no Tier-A policy row (unreachable): "
        f"{orphans}"
    )


def test_no_orphan_knowledge_entry() -> None:
    knowledge = set(_knowledge_names())
    orphans = sorted(knowledge - assessable_test_names())
    assert not orphans, (
        f"test-knowledge entries with no Tier-A policy row (unreachable): " f"{orphans}"
    )


def test_every_policy_name_is_recognized_by_normalization() -> None:
    # The policy keys are canonical names too; if one drifts, coverage
    # classification would look it up under a name normalization never emits.
    for name in policy_test_names():
        assert normalize_test_name(name) == name, (
            f"policy test name {name!r} is not canonical "
            f"(normalizes to {normalize_test_name(name)!r})"
        )


# --- proof the schema-level guard still fails loudly -----------------------


def test_impossible_critical_threshold_is_rejected() -> None:
    """A deliberately-broken entry must fail with a clear message (6.5.10).

    critical_low is supposed to sit BELOW the normal low. Here it sits inside
    the normal range — a contradiction the loader must refuse rather than
    silently mis-band values around it.
    """
    with pytest.raises(ValidationError, match="critical_low"):
        ReferenceRangeEntry(
            test_name="Hemoglobin",
            low=13.0,
            high=17.0,
            critical_low=14.0,  # inside the normal range — impossible
            source="Deliberately broken (test)",
        )
