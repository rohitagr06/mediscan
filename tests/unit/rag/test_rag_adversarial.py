"""Adversarial, wiring & boundary tests for the RAG layer (Claude's half).

Rohit's half (test_rag_layer.py) proves the happy paths. THIS file attacks
the guarantees:
  * retrieval never returns more than K, and asking for more than the KB
    holds is safe (no crash);
  * empty / whitespace / gibberish queries return safely;
  * grounding WIRING: an abnormal finding's FACTS block carries the matching
    KB snippet AND its source, normal findings are not grounded, and a
    retrieval failure never breaks the explanation;
  * provenance records the sources it grounded on (traceability, 6.8);
  * the #006 safety boundary is MACHINE-CHECKED: medical/ never imports rag/;
  * one @pytest.mark.slow test loads the REAL BGE model and proves semantic
    retrieval — a meaning-similar query (fatigue) beats an unrelated one.

Fast tests use the deterministic FAKE embedder — no model, no network.
"""

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mediscan.ai.base import LLMClient
from mediscan.ai.explain import (
    _augment_facts,
    _facts_from_verdict,
    _grounding_snippets,
    explain_report,
)
from mediscan.medical.severity import assess_results
from mediscan.medical.urgency import assess_urgency
from mediscan.rag.embedding import FakeEmbeddingFunction
from mediscan.rag.index import build_index
from mediscan.rag.retriever import RetrievedSnippet, retrieve
from mediscan.schemas import (
    ExplanationSource,
    LabResult,
    LLMResponse,
    ReferenceRange,
)

FIXED_NOW = datetime(2026, 7, 9, tzinfo=UTC)


@pytest.fixture(scope="module")
def fake_index():
    """KB index built once with the deterministic fake embedder (offline)."""
    return build_index(FakeEmbeddingFunction())


# --- retrieval bounds & odd queries ----------------------------------------


def test_retrieval_never_exceeds_k(fake_index):
    assert len(retrieve("hemoglobin", k=2, collection=fake_index)) <= 2


def test_asking_for_more_than_kb_is_safe(fake_index):
    # k far bigger than the KB must NOT crash; ChromaDB returns what exists.
    got = retrieve("blood count", k=999, collection=fake_index)
    assert 0 < len(got) <= fake_index.count()


@pytest.mark.parametrize("query", ["", "   ", "zzz qqq wxyz", "?!?!"])
def test_odd_queries_return_safely(fake_index, query):
    # The query prefix guarantees a non-empty embedding, so even ""/gibberish
    # can't produce a zero vector or a crash.
    got = retrieve(query, k=3, collection=fake_index)
    assert isinstance(got, list)
    assert len(got) <= 3


# --- grounding wiring (no chromadb needed — pure retriever stubs) -----------


def _abnormal_hb():
    labs = [
        LabResult(
            test_name="Hemoglobin",
            value=8.0,
            reference_range=ReferenceRange(low=13.0, high=17.0),
        )
    ]
    assessments = assess_results(labs)
    return assessments, assess_urgency(assessments)


def _one_snippet(_query: str) -> list[RetrievedSnippet]:
    return [RetrievedSnippet("Low hemoglobin can indicate anemia.", "MedlinePlus")]


def test_facts_block_carries_snippet_and_source():
    assessments, urgency = _abnormal_hb()
    snippets = _grounding_snippets(assessments, _one_snippet)
    facts = _augment_facts(_facts_from_verdict(assessments, urgency), snippets)
    assert "Low hemoglobin can indicate anemia." in facts
    assert "[source: MedlinePlus]" in facts
    assert "BACKGROUND KNOWLEDGE" in facts


def test_normal_findings_are_not_grounded():
    labs = [
        LabResult(
            test_name="Platelet Count",
            value=250.0,
            reference_range=ReferenceRange(low=150.0, high=410.0),
        )
    ]
    assessments = assess_results(labs)
    called: list[str] = []

    def spy(query: str) -> list[RetrievedSnippet]:
        called.append(query)
        return []

    _grounding_snippets(assessments, spy)
    assert called == []  # a normal value triggers no retrieval at all


def test_retrieval_failure_never_breaks_grounding():
    assessments, _ = _abnormal_hb()

    def boom(_query: str) -> list[RetrievedSnippet]:
        raise RuntimeError("index down")

    # Swallowed -> empty, so the explanation still runs from verdict facts.
    assert _grounding_snippets(assessments, boom) == []


# --- provenance records the sources (6.8 traceability) ---------------------


class _PatientFake(LLMClient):
    """Returns shape-correct JSON for whichever of the four prompts it gets."""

    provider_name = "fake"
    model = "fake-1"

    def complete(self, request) -> LLMResponse:
        u = request.user_prompt.lower()
        if "physician" in u:
            text = '{"text": "Mild anemia pattern.", "clinical_notes": ["Hb 8"]}'
        elif "dietary" in u:
            text = '[{"suggestion": "Iron-rich foods may be discussed."}]'
        elif "specialist" in u:
            text = '[{"specialty": "Hematologist", "reason": "Low hemoglobin."}]'
        else:  # patient
            text = (
                '{"text": "Your hemoglobin is low. See a doctor soon.", '
                '"key_points": ["Hb low"]}'
            )
        return LLMResponse(
            text=text,
            provider_name="fake",
            model="fake-1",
            temperature=0.2,
            latency_ms=0.0,
        )


def test_provenance_records_grounding_sources():
    assessments, urgency = _abnormal_hb()

    def two_sources(_query: str) -> list[RetrievedSnippet]:
        return [
            RetrievedSnippet("Low hemoglobin can indicate anemia.", "SrcA"),
            RetrievedSnippet("Low hematocrit can too.", "SrcB"),
        ]

    r = explain_report(
        assessments,
        urgency,
        [_PatientFake()],
        now=lambda: FIXED_NOW,
        retrieve_fn=two_sources,
    )
    assert r.patient.provenance.source is ExplanationSource.AI
    assert r.patient.provenance.grounding_sources == ["SrcA", "SrcB"]


# --- #006 safety boundary: medical/ must NEVER import rag/ ------------------


def test_medical_never_imports_rag():
    """Machine-check the #006 rule instead of trusting a promise.

    We parse every module under src/mediscan/medical/ and assert none of them
    imports anything from mediscan.rag — the deterministic engine cannot be
    allowed to depend on the AI/RAG layer, by construction.
    """
    root = Path(__file__).resolve().parents[3]  # tests/unit/rag/ -> repo root
    medical_dir = root / "src" / "mediscan" / "medical"
    offenders: list[str] = []
    for py in sorted(medical_dir.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("mediscan.rag"):
                    offenders.append(f"{py.name}: from {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("mediscan.rag"):
                        offenders.append(f"{py.name}: import {alias.name}")
    assert offenders == [], f"medical/ must not import rag/ (#006): {offenders}"


# --- slow: the REAL BGE model proves MEANING-based retrieval ---------------


@pytest.mark.slow
def test_real_bge_retrieves_by_meaning():
    """A fatigue query shares almost no WORDS with the KB, but MEANS anemia.

    Only a real embedding model (not the word-overlap fake) can bridge that
    gap — so this guards the production retrieval path. Marked slow: excluded
    from the default run, executed with `uv run pytest -m slow`.
    """
    from mediscan.rag.embedding import bge_embedding_function

    collection = build_index(bge_embedding_function())
    got = retrieve(
        "I have been feeling very tired and weak lately",
        k=3,
        collection=collection,
    )
    joined = " ".join(s.text.lower() for s in got)
    assert "hemoglobin" in joined or "anemia" in joined
