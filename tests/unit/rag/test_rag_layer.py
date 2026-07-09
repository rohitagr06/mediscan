"""Happy-path tests for the RAG layer (Rohit's half).

The everyday "it works" cases:
  * the KB schema validates a good entry and REJECTS an unsourced one;
  * chunking turns one entry into the expected sourced snippets;
  * the index builds with the fake embedder (no model, no network);
  * a matching query retrieves the right test's snippet, with its source.

Adversarial, boundary, and slow real-model cases live in
test_rag_adversarial.py (Claude's half). Everything here uses the
deterministic FAKE embedder, so the suite stays fast and offline.
"""

import pytest
from pydantic import ValidationError

from mediscan.rag.embedding import FakeEmbeddingFunction
from mediscan.rag.index import build_index
from mediscan.rag.retriever import retrieve

# Aliased on import: the class is named TestKnowledge, and pytest tries to
# COLLECT any module-level name starting with "Test" as a test class (warning
# noise). Binding it to a non-"Test" name here avoids that.
from mediscan.schemas import TestKnowledge as KnowledgeEntry


def _knowledge(**overrides) -> dict:
    """A valid TestKnowledge payload; pass overrides to change one field."""
    data = {
        "test_name": "Hemoglobin",
        "what_it_measures": "the oxygen-carrying protein in red blood cells",
        "low_meaning": "low hemoglobin can be associated with anemia",
        "high_meaning": "high hemoglobin can be associated with dehydration",
        "dietary_note": "iron-rich foods are often discussed",
        "specialist": "Hematologist",
        "source": "MedlinePlus: Hemoglobin Test",
    }
    data.update(overrides)
    return data


# --- schema: validation + the mandatory source (#019) ----------------------


def test_valid_knowledge_builds():
    tk = KnowledgeEntry(**_knowledge())
    assert tk.test_name == "Hemoglobin"
    assert tk.source  # present and non-empty


def test_missing_source_is_rejected():
    payload = _knowledge()
    del payload["source"]  # no citation at all
    with pytest.raises(ValidationError):
        KnowledgeEntry(**payload)


def test_blank_source_is_rejected():
    # str_strip_whitespace turns "   " into "", which fails min_length=1.
    with pytest.raises(ValidationError):
        KnowledgeEntry(**_knowledge(source="   "))


# --- chunking: one entry -> individually-retrievable snippets ---------------


def test_full_entry_chunks_into_five_sourced_snippets():
    snippets = KnowledgeEntry(**_knowledge()).to_snippets()
    # measures / low / high / dietary / specialist = 5
    assert len(snippets) == 5
    # every snippet carries the SAME source + test_name as its parent entry
    assert all(s.source == "MedlinePlus: Hemoglobin Test" for s in snippets)
    assert all(s.test_name == "Hemoglobin" for s in snippets)


def test_optional_fields_drop_their_snippets():
    lean = KnowledgeEntry(**_knowledge(dietary_note=None, specialist=None))
    # only measures / low / high remain
    assert len(lean.to_snippets()) == 3


def test_low_snippet_mentions_test_and_meaning():
    snippets = KnowledgeEntry(**_knowledge()).to_snippets()
    low = next(s for s in snippets if s.text.startswith("A low Hemoglobin"))
    assert "anemia" in low.text


# --- index + retrieval with the fake embedder (offline) --------------------


@pytest.fixture(scope="module")
def fake_index():
    """The KB index built once with the deterministic fake embedder.

    scope="module" builds it a single time for every test in this file
    instead of rebuilding per test — the KB doesn't change between them.
    """
    return build_index(FakeEmbeddingFunction())


def test_index_builds_with_expected_snippet_count(fake_index):
    # today's KB: 5 CBC tests x 5 snippets each = 25.
    assert fake_index.count() == 25


def test_matching_query_retrieves_that_test(fake_index):
    got = retrieve("Hemoglobin low what does it mean", k=3, collection=fake_index)
    assert got  # non-empty
    joined = " ".join(s.text.lower() for s in got)
    assert "hemoglobin" in joined
    assert all(s.source for s in got)  # every hit is citable
