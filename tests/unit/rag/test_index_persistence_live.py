"""ChromaDB-backed persistence tests (Sprint 7.11).

These exercise the REAL persist/load path with a temp cache directory and the
fast FAKE embedder (no model, no network). They run in CI and on the Mac (where
ChromaDB is installed) and are not collected in the cloud sandbox. The pure
hash/prune logic is covered separately in test_index_persistence.py.
"""

import mediscan.rag.index as index_module
from mediscan.rag.embedding import FakeEmbeddingFunction
from mediscan.rag.index import build_persistent_index


class _CountingEmbedder(FakeEmbeddingFunction):
    """A fake embedder that counts how many times it is invoked."""

    def __init__(self):
        self.calls = 0

    def __call__(self, input):
        self.calls += 1
        return super().__call__(input)


def test_cold_build_creates_and_populates(tmp_path):
    collection = build_persistent_index(FakeEmbeddingFunction(), cache_dir=tmp_path)
    assert collection.count() > 0
    # the on-disk index lives under the current KB hash
    assert (tmp_path / index_module._hash_kb()).is_dir()


def test_warm_load_does_not_re_embed(tmp_path):
    cold = _CountingEmbedder()
    build_persistent_index(cold, cache_dir=tmp_path)
    assert cold.calls > 0  # cold build embedded every snippet

    warm = _CountingEmbedder()
    collection = build_persistent_index(warm, cache_dir=tmp_path)
    assert warm.calls == 0  # warm load reused the on-disk vectors — no re-embed
    assert collection.count() > 0


def test_kb_change_rebuilds_and_prunes_the_old_index(tmp_path, monkeypatch):
    # pretend the KB has hash "A", build it
    monkeypatch.setattr(index_module, "_hash_kb", lambda kb_dir=None: "hashA")
    build_persistent_index(FakeEmbeddingFunction(), cache_dir=tmp_path)
    assert (tmp_path / "hashA").is_dir()

    # KB changes -> new hash "B" -> new dir built, old dir pruned
    monkeypatch.setattr(index_module, "_hash_kb", lambda kb_dir=None: "hashB")
    build_persistent_index(FakeEmbeddingFunction(), cache_dir=tmp_path)
    assert (tmp_path / "hashB").is_dir()
    assert not (tmp_path / "hashA").exists()  # stale index pruned


def test_corrupt_cache_recovers(tmp_path, monkeypatch):
    monkeypatch.setattr(index_module, "_hash_kb", lambda kb_dir=None: "h1")
    # plant a garbage file where ChromaDB expects its store
    corrupt = tmp_path / "h1"
    corrupt.mkdir(parents=True)
    (corrupt / "chroma.sqlite3").write_text("not a real database")

    # must not crash: a bad cache is nuked and rebuilt from the KB
    collection = build_persistent_index(FakeEmbeddingFunction(), cache_dir=tmp_path)
    assert collection.count() > 0
