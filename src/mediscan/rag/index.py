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
import uuid
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
    # Unique name per build. EphemeralClient shares ONE in-process backend, so
    # a fixed name would collide ("already exists") the moment a second index
    # is built in the same process — which tests do. Production builds exactly
    # one (get_index is @cache'd), and callers use the collection OBJECT, never
    # its name, so a random name is invisible everywhere but safe everywhere.
    collection = client.create_collection(
        name=f"mediscan_kb_{uuid.uuid4().hex}",
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
