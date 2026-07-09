"""Embedding functions: text -> vector, for the RAG index.

WHY THIS FILE EXISTS
    ChromaDB needs an "embedding function" — a callable that takes a list of
    texts and returns a list of vectors — to turn our knowledge snippets into
    numbers it can search by similarity. This module provides two:

      - the REAL one (BGE-small via sentence-transformers), for production;
      - a tiny deterministic FAKE, for tests — so the fast test suite needs
        no model download and no network.

    Both satisfy ChromaDB's embedding-function shape: __call__(input) where
    `input` is a list[str] and the return is a list of float-vectors.
"""

import zlib

from chromadb import Documents, EmbeddingFunction, Embeddings


def bge_embedding_function():
    """Return ChromaDB's BGE-small embedding function (real, production).

    The heavy libraries are imported LAZILY (inside the function) so this
    module loads even where chromadb/sentence-transformers aren't installed.

    Returns:
        A ChromaDB SentenceTransformerEmbeddingFunction backed by
        BAAI/bge-small-en-v1.5 (downloads ~130 MB on first use, then cached).
    """
    from chromadb.utils import embedding_functions

    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="BAAI/bge-small-en-v1.5"
    )


class FakeEmbeddingFunction(EmbeddingFunction):
    """Deterministic bag-of-words embedder for tests — no model, no network.

    Subclasses ChromaDB's EmbeddingFunction so it works for BOTH add() and
    query(): the base class provides embed_documents/embed_query, which both
    route to our __call__. Similar text (shared words) -> similar vectors;
    it captures word overlap, NOT real meaning — never use in production.
    """

    _DIM = 64  # vector length; small is fine for tests

    def __init__(self) -> None:
        # ChromaDB now expects every embedding function to define __init__
        # (a future version will require it). There's nothing to configure for
        # the fake, so this simply satisfies that contract and silences the
        # DeprecationWarning.
        super().__init__()

    def __call__(self, input: Documents) -> Embeddings:
        vectors: list[list[float]] = []
        for text in input:
            vec = [0.0] * self._DIM
            for word in text.lower().split():
                # zlib.crc32 is a STABLE hash (same result every run, unlike
                # Python's built-in hash() which is randomized per process).
                bucket = zlib.crc32(word.encode()) % self._DIM
                vec[bucket] += 1.0
            vectors.append(vec)
        return vectors

    @staticmethod
    def name() -> str:
        return "fake"

    def get_config(self) -> dict:
        return {}

    @staticmethod
    def build_from_config(config: dict) -> "EmbeddingFunction":
        return FakeEmbeddingFunction()
