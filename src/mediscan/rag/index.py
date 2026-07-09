"""Build the in-memory vector index from the knowledge-base files.

WHY THIS FILE EXISTS
    RAG needs a searchable store of our curated snippets. This module reads
    every TestKnowledge JSON, chunks each entry into snippets, and loads them
    into an in-memory ChromaDB collection. Rebuilding from the files each run
    keeps the JSON as the single source of truth (no stale index).

    ChromaDB is imported LAZILY so this module — and the snippet-loading half
    — works without it (tests that only check loading need no vector DB).
"""

import json
from functools import cache
from pathlib import Path

from mediscan.schemas import KnowledgeSnippet, TestKnowledge

_KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "test_knowledge"


def load_snippets() -> list[KnowledgeSnippet]:
    """Read every TestKnowledge JSON file and chunk it into snippets.

    Returns:
        All KnowledgeSnippets across every KB file, validated at load.

    Raises:
        ValidationError: If any entry is malformed (Pydantic validates it).
    """
    snippets: list[KnowledgeSnippet] = []
    for path in sorted(_KB_DIR.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        for item in raw:
            snippets.extend(TestKnowledge(**item).to_snippets())
    return snippets


def build_index(embedding_function):
    """Build a fresh in-memory ChromaDB collection of all KB snippets.

    Args:
        embedding_function: A callable text->vectors (the real BGE one in
            production, the fake one in tests). Injected so tests need no model.

    Returns:
        A ChromaDB collection ready to be queried.
    """
    import chromadb

    client = chromadb.EphemeralClient()  # in-memory, nothing written to disk
    collection = client.create_collection(
        name="mediscan_kb",
        embedding_function=embedding_function,
    )

    snippets = load_snippets()
    if snippets:  # ChromaDB rejects an empty add()
        collection.add(
            documents=[s.text for s in snippets],
            metadatas=[{"source": s.source, "test": s.test_name} for s in snippets],
            ids=[f"snippet-{i}" for i in range(len(snippets))],
        )
    return collection


@cache
def get_index():
    """Return the shared production index, built once with the real BGE model."""
    from mediscan.rag.embedding import bge_embedding_function

    return build_index(bge_embedding_function())
