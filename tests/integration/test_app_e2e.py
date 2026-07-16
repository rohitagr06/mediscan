"""Application-level E2E (Sprint 8.8): the whole stranger-facing path.

Drives the UI's ``analyze()`` seam on the real synthetic ``cbc_report.pdf``
fixture, end to end: validate -> secure temp store -> extract (PyMuPDF) ->
analyze -> render HTML -> generate PDF. Deterministic (``demo_mode=True``:
no AI, no keys). RAG grounding is stubbed with a no-op retriever (the RAG
suite covers grounding on its own), so this test stays OFFLINE — no vector
DB, no BGE download, no network. Skipped where PyMuPDF or WeasyPrint (system
libs) are absent, exactly like the other end-to-end tests.

This is the proof of the RC1 milestone in one test: "a stranger uploads a
lab report and gets back an analysis plus a downloadable PDF."
"""

from pathlib import Path

import pytest

pytest.importorskip("pymupdf")
try:
    import weasyprint  # noqa: F401 - probe only; used via the seam
except (ImportError, OSError) as exc:  # pragma: no cover - env-dependent
    pytest.skip(f"WeasyPrint unavailable: {exc}", allow_module_level=True)

from mediscan.ui import app as ui_app

FIXTURES = Path("tests/fixtures/files")


def _no_retrieve(_query):
    return []


def test_stranger_path_pdf_to_report_and_pdf(monkeypatch):
    # Inject a no-op retriever so the real engine runs OFFLINE (no vector DB,
    # no BGE download). Everything else — validation, secure storage,
    # extraction, parsing, coverage, urgency, rendering, PDF — is the exact
    # code path the deployed app uses.
    real_analyze = ui_app.analyze_document
    monkeypatch.setattr(
        ui_app,
        "analyze_document",
        lambda path, **kw: real_analyze(path, retrieve_fn=_no_retrieve, **kw),
    )

    source = FIXTURES / "cbc_report.pdf"
    display, pdf_path = ui_app.analyze(str(source), demo_mode=True)

    # The rendered report shows the analysis + the mandatory disclaimer.
    assert "<iframe" in display  # report shown in a sandboxed frame
    assert "informational tool" in display  # disclaimer, present by construction
    assert "Assessed results" in display
    assert "Hemoglobin" in display  # a real assessed finding from the fixture

    # A downloadable PDF was actually produced on disk.
    assert pdf_path is not None
    assert pdf_path.endswith(".pdf")
    out = Path(pdf_path)
    try:
        assert out.exists()
        assert out.read_bytes().startswith(b"%PDF-")
    finally:
        out.unlink(missing_ok=True)  # clean up the temp file the seam created
