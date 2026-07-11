"""Offline tests for the persisted-index cache key + pruning (Sprint 7.10).

The persist/load itself needs ChromaDB (covered by the gated 7.11 test). But
the INVALIDATION logic — the content hash and the stale-directory pruning —
is pure Python and fully testable here, which is the whole point of factoring
it out.
"""

from mediscan.rag.index import _hash_kb, _prune_stale_indexes


def _write(directory, name, content):
    (directory / name).write_text(content, encoding="utf-8")


# --- the content hash (the cache key) --------------------------------------


def test_hash_is_deterministic(tmp_path):
    _write(tmp_path, "a.json", '[{"x": 1}]')
    assert _hash_kb(tmp_path) == _hash_kb(tmp_path)


def test_hash_changes_when_content_changes(tmp_path):
    _write(tmp_path, "a.json", '[{"x": 1}]')
    before = _hash_kb(tmp_path)
    _write(tmp_path, "a.json", '[{"x": 2}]')  # edit
    assert _hash_kb(tmp_path) != before


def test_hash_changes_when_a_file_is_added(tmp_path):
    _write(tmp_path, "a.json", '[{"x": 1}]')
    before = _hash_kb(tmp_path)
    _write(tmp_path, "b.json", '[{"y": 2}]')  # new panel
    assert _hash_kb(tmp_path) != before


def test_hash_ignores_non_json_files(tmp_path):
    _write(tmp_path, "a.json", '[{"x": 1}]')
    before = _hash_kb(tmp_path)
    _write(tmp_path, "notes.txt", "irrelevant")
    assert _hash_kb(tmp_path) == before  # only *.json feeds the index


def test_real_kb_hash_is_a_hex_digest():
    digest = _hash_kb()  # the real KB dir
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


# --- pruning old index directories -----------------------------------------


def test_prune_keeps_only_the_current_hash(tmp_path):
    for name in ("oldhash1", "oldhash2", "keepme"):
        (tmp_path / name).mkdir()
    _prune_stale_indexes(tmp_path, keep="keepme")
    assert {p.name for p in tmp_path.iterdir()} == {"keepme"}


def test_prune_missing_root_is_a_noop(tmp_path):
    # never crash if the cache root doesn't exist yet
    _prune_stale_indexes(tmp_path / "nope", keep="x")
