"""Tests for SecureUploadDir: the self-destructing upload directory.

The key promise under test: the directory is ALWAYS removed after the
`with` block — clean exit or exception — and the patient's original
filename never survives into storage (PHI).
"""

import pytest

from mediscan.ingestion.storage import SecureUploadDir


def test_stores_copy_with_anonymous_name(tmp_path):
    source = tmp_path / "ramesh_hiv_report.pdf"
    source.write_bytes(b"%PDF-1.6 contents")

    with SecureUploadDir() as upload_dir:
        stored = upload_dir.store(source)
        assert stored.exists()
        assert stored.read_bytes() == source.read_bytes()
        # PHI rule: original name gone, extension kept
        assert "ramesh" not in stored.name.lower()
        assert stored.suffix == ".pdf"
        assert stored.parent == upload_dir.path


def test_directory_removed_after_clean_exit(tmp_path):
    source = tmp_path / "a.pdf"
    source.write_bytes(b"%PDF-")
    with SecureUploadDir() as upload_dir:
        kept_path = upload_dir.path
        upload_dir.store(source)
    assert not kept_path.exists()  # gone, with everything in it


def test_directory_removed_even_when_exception_flies(tmp_path):
    source = tmp_path / "a.pdf"
    source.write_bytes(b"%PDF-")
    kept_path = None
    with pytest.raises(RuntimeError):
        with SecureUploadDir() as upload_dir:
            kept_path = upload_dir.path
            upload_dir.store(source)
            raise RuntimeError("simulated mid-pipeline crash")
    # __exit__ ran anyway: that's the context-manager guarantee
    assert kept_path is not None
    assert not kept_path.exists()


def test_using_path_outside_with_block_is_an_error():
    upload_dir = SecureUploadDir()
    with pytest.raises(RuntimeError):
        _ = upload_dir.path  # never entered — refuse loudly, not None-crash


def test_two_sessions_are_isolated(tmp_path):
    with SecureUploadDir() as a, SecureUploadDir() as b:
        assert a.path != b.path
