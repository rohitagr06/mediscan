"""Build the vector index from the knowledge-base files.

WHY THIS FILE EXISTS
    RAG needs a searchable store of our curated snippets. This module reads
    every TestKnowledge JSON, chunks each entry into snippets, and loads them
    into a ChromaDB collection.

    Two build modes:
      - build_index(...)             — in-memory (Ephemeral), used by tests.
      - build_persistent_index(...)  — persisted to disk, keyed by a HASH of the
        KB files (Sprint 7.10). A warm start LOADS the on-disk index without
        re-embedding; when any KB file changes the hash changes and the index
        is rebuilt + persisted (stale directories pruned). Keyed-by-content
        makes a stale index impossible by construction.

    ChromaDB is imported LAZILY so this module — and the snippet-loading half
    — works without it (tests that only check loading/hashing need no vector DB).
"""

import hashlib
import json
import shutil
import tempfile
import uuid
from functools import cache
from pathlib import Path

from mediscan.config import settings
from mediscan.schemas import KnowledgeSnippet, TestKnowledge

_KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "test_knowledge"

# One fixed collection name is safe for the PERSISTENT index because each KB
# hash gets its OWN directory — no cross-hash name collision is possible.
_COLLECTION_NAME = "mediscan_kb"


def load_test_knowledge() -> list[TestKnowledge]:
    """Read and validate every TestKnowledge JSON entry (whole, un-chunked).

    This is the SINGLE place that parses the test_knowledge KB files.
    load_snippets chunks these entries into retrievable snippets; the KB
    integrity checks inspect them whole. Sharing one loader guarantees both
    views see exactly the same set of entries.

    Returns:
        Every TestKnowledge across all KB files, validated at load.

    Raises:
        ValidationError: If any entry is malformed (Pydantic validates it).
    """
    entries: list[TestKnowledge] = []
    for path in sorted(_KB_DIR.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        for item in raw:
            entries.append(TestKnowledge(**item))  # validates here
    return entries


def load_snippets() -> list[KnowledgeSnippet]:
    """Chunk every TestKnowledge entry into individually-retrievable snippets.

    Returns:
        All KnowledgeSnippets across every KB file, validated at load.

    Raises:
        ValidationError: If any entry is malformed (Pydantic validates it).
    """
    snippets: list[KnowledgeSnippet] = []
    for entry in load_test_knowledge():
        snippets.extend(entry.to_snippets())
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


def _hash_kb(kb_dir: Path | None = None) -> str:
    """Return a SHA-256 fingerprint of the KB JSON files (name + contents).

    The fingerprint changes whenever any file is added, removed, renamed, or
    edited — so it's the perfect cache key: same KB -> same hash -> load the
    cached index; any change -> new hash -> rebuild. Pure and offline
    (no ChromaDB), so the invalidation logic is directly testable.
    """
    directory = kb_dir or _KB_DIR
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.json")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _prune_stale_indexes(cache_root: Path, *, keep: str) -> None:
    """Delete cached index directories for OLD KB hashes, keeping only `keep`.

    Without this, every KB edit would leave its old index dir behind forever.
    Best-effort: a directory that can't be removed is skipped, never fatal.
    """
    if not cache_root.is_dir():
        return
    for child in cache_root.iterdir():
        if child.is_dir() and child.name != keep:
            shutil.rmtree(child, ignore_errors=True)


def _populate(collection) -> None:
    """Add every KB snippet to a (fresh, empty) collection."""
    snippets = load_snippets()
    if snippets:  # ChromaDB rejects an empty add()
        collection.add(
            documents=[s.text for s in snippets],
            metadatas=[{"source": s.source, "test": s.test_name} for s in snippets],
            ids=[f"snippet-{i}" for i in range(len(snippets))],
        )


def _resolve_cache_root(cache_dir: str | Path | None) -> Path:
    """Return a WRITABLE directory for the persisted index.

    Uses the configured path (``cache_dir`` or settings), but if that path
    can't be created or written — e.g. a read-only Hugging Face Spaces
    filesystem — falls back to an ephemeral temp dir so the index still
    builds instead of crashing the app on startup.
    """
    root = Path(cache_dir or settings.rag_index_cache_dir).expanduser()
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return root
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "mediscan_rag_index"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def build_persistent_index(embedding_function, *, cache_dir: str | Path | None = None):
    """Build-or-load the persistent KB index, keyed by a hash of the KB files.

    Warm start (KB unchanged): the on-disk index is opened and returned WITHOUT
    re-embedding. Cold start / KB changed: a fresh per-hash directory is built,
    populated, persisted, and older hash directories are pruned.

    A corrupt or version-incompatible cache directory must never break startup:
    on any load error we clear ChromaDB's in-process cache, delete that
    directory, and rebuild from scratch.
    """
    import chromadb

    cache_root = _resolve_cache_root(cache_dir)
    kb_hash = _hash_kb()
    index_dir = cache_root / kb_hash

    def _open_and_maybe_build():
        client = chromadb.PersistentClient(path=str(index_dir))
        collection = client.get_or_create_collection(
            name=_COLLECTION_NAME, embedding_function=embedding_function
        )
        if collection.count() == 0:  # a freshly-created (cold) directory
            _populate(collection)
            _prune_stale_indexes(cache_root, keep=kb_hash)
        return collection

    try:
        return _open_and_maybe_build()
    except Exception:  # noqa: BLE001 - a bad cache must degrade to a rebuild
        # A failed open leaves a BROKEN system cached in-process keyed by this
        # path; a naive retry would reuse it ("no attribute 'bindings'"). Clear
        # that cache AND delete the dir so the rebuild starts truly clean.
        _reset_chroma_system_cache()
        shutil.rmtree(index_dir, ignore_errors=True)
        return _open_and_maybe_build()


def _reset_chroma_system_cache() -> None:
    """Clear ChromaDB's in-process per-path system cache (recovery helper).

    Best-effort and version-tolerant: if the internal API moves, we no-op
    rather than turn a recoverable cache problem into a crash.
    """
    try:
        from chromadb.api.shared_system_client import SharedSystemClient

        SharedSystemClient.clear_system_cache()
    except Exception:  # noqa: BLE001, S110 - internal API drift stays non-fatal
        pass


@cache
def get_index():
    """Return the shared production index, built or loaded once with real BGE.

    Uses the PERSISTENT index (Sprint 7.10): the first process to run with a
    given KB pays the embedding cost; later processes load it from disk.
    """
    from mediscan.rag.embedding import bge_embedding_function

    return build_persistent_index(bge_embedding_function())
