"""Retrieve the most relevant KB snippets for a query (the 'R' in RAG).

WHY THIS FILE EXISTS
    Given a question (e.g. "Hemoglobin low — what does it mean?"), this asks
    the vector index for the closest curated snippets and returns them WITH
    their sources, so the explanation layer can ground on them and cite them.
"""

from typing import NamedTuple

from mediscan.config import settings
from mediscan.rag.index import get_index

# BGE retrieval works a little better when the QUERY (not the stored docs)
# carries this short instruction prefix. The stored snippets are embedded
# plain; only the query gets the prefix.
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class RetrievedSnippet(NamedTuple):
    """One retrieved fact and where it came from.

    Attributes:
        text: The snippet text to hand to the AI as a grounding fact.
        source: The citation for that fact (for traceability).
    """

    text: str
    source: str


def retrieve(
    query: str, k: int | None = None, *, collection=None
) -> list[RetrievedSnippet]:
    """Return the top-k KB snippets most relevant to `query`, with sources.

    Args:
        query: A natural-language question or finding description.
        k: How many snippets to return; defaults to settings.rag_top_k.
        collection: The vector collection to search; defaults to the shared
            production index. Tests inject a fake-embedder collection here.

    Returns:
        Up to k RetrievedSnippets, most relevant first. Empty if the index
        is empty.
    """
    coll = collection if collection is not None else get_index()
    n = k if k is not None else settings.rag_top_k

    results = coll.query(query_texts=[_QUERY_PREFIX + query], n_results=n)

    # ChromaDB returns lists-of-lists (one inner list per query); we sent one
    # query, so take index [0]. documents[0] and metadatas[0] line up.
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    return [
        RetrievedSnippet(text=doc, source=meta["source"])
        for doc, meta in zip(documents, metadatas, strict=True)
    ]
