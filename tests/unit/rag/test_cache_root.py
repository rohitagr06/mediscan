"""Tests for the writable-cache fallback (Sprint 8.7 deploy hardening).

_resolve_cache_root must return a usable directory even when the configured
path is read-only (e.g. a Hugging Face Spaces filesystem) — falling back to
a temp dir rather than crashing the app on startup. Pure/offline (no chromadb).
"""

from mediscan.rag.index import _resolve_cache_root


def test_uses_configured_writable_dir(tmp_path):
    target = tmp_path / "idx"
    root = _resolve_cache_root(str(target))
    assert root == target
    assert root.is_dir()


def test_falls_back_when_unwritable(tmp_path):
    # Put a FILE where the parent dir would need to be: mkdir under it fails.
    blocker = tmp_path / "afile"
    blocker.write_text("x")
    unwritable = blocker / "idx"
    root = _resolve_cache_root(str(unwritable))
    assert root != unwritable
    assert root.is_dir()  # a real, writable temp dir instead
