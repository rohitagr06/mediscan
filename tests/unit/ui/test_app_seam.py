"""Unit tests for the UI seam `analyze()` (Sprint 8.5/8.8 groundwork).

These test the SEAM's wiring — validation gating, error handling, provider
selection, and that a report becomes display HTML + a PDF path — WITHOUT a
browser and WITHOUT the heavy engine. The engine (`analyze_document`) and
the PDF renderer are monkeypatched, so these run offline in any environment;
the real end-to-end run is exercised on the Mac (8.8).
"""

import os
from pathlib import Path

import pytest

from mediscan.schemas.report import AnalysisReport

# gradio itself is only needed to BUILD the app, not to test the seam, so we
# never import it here. The seam is a plain function.
from mediscan.ui import app as ui_app


@pytest.fixture
def valid_pdf(tmp_path: Path) -> Path:
    """A minimal file that passes validate_upload as a text PDF."""
    p = tmp_path / "report.pdf"
    # "%PDF-1.4" magic bytes make validate_upload accept it as a PDF.
    p.write_bytes(b"%PDF-1.4\n% minimal\n")
    return p


def test_no_file_returns_prompt_and_no_pdf():
    display, pdf = ui_app.analyze(None, demo_mode=True)
    assert "upload" in display.lower()
    assert pdf is None


def test_invalid_file_is_rejected_gracefully(tmp_path: Path):
    bad = tmp_path / "notes.txt"
    bad.write_text("hello")
    display, pdf = ui_app.analyze(str(bad), demo_mode=True)
    assert "couldn" in display.lower() or "accepted" in display.lower()
    assert pdf is None


def test_happy_path_returns_iframe_and_pdf(monkeypatch, valid_pdf: Path):
    # Stub the engine: no OCR, no AI — just hand back a fixed report.
    fake_report = AnalysisReport()
    monkeypatch.setattr(ui_app, "analyze_document", lambda *a, **k: fake_report)
    # Stub the PDF renderer to avoid needing WeasyPrint's system libs here.
    monkeypatch.setattr(ui_app, "render_pdf", lambda html: b"%PDF-1.4 fake")

    display, pdf = ui_app.analyze(str(valid_pdf), demo_mode=True)

    assert "<iframe" in display  # report shown in a sandboxed frame
    assert "informational tool" in display  # disclaimer rendered inside it
    assert pdf is not None
    assert pdf.endswith(".pdf")
    assert os.path.exists(pdf)
    os.remove(pdf)  # clean up the temp file the seam created


def test_engine_failure_becomes_friendly_message(monkeypatch, valid_pdf: Path):
    def boom(*a, **k):
        raise RuntimeError("internal detail that must not leak")

    monkeypatch.setattr(ui_app, "analyze_document", boom)
    display, pdf = ui_app.analyze(str(valid_pdf), demo_mode=True)
    assert "went wrong" in display.lower()
    assert "internal detail" not in display  # no leak of the exception text
    assert pdf is None


def test_missing_pdf_engine_still_shows_analysis(monkeypatch, valid_pdf: Path):
    monkeypatch.setattr(ui_app, "analyze_document", lambda *a, **k: AnalysisReport())

    def no_pdf(html):
        raise OSError("no pango")

    monkeypatch.setattr(ui_app, "render_pdf", no_pdf)
    display, pdf = ui_app.analyze(str(valid_pdf), demo_mode=True)
    assert "<iframe" in display  # analysis still rendered
    assert pdf is None  # but no PDF offered


# ---------------------------------------------------------------------------
# Provider selection (demo mode is the safe default, #036)
# ---------------------------------------------------------------------------


def test_demo_mode_uses_no_providers():
    assert ui_app._providers_for(demo_mode=True) == []


def test_keyed_mode_skips_providers_without_keys(monkeypatch):
    # No keys configured -> no providers (graceful, not a crash).
    monkeypatch.setattr(ui_app.settings, "gemini_api_key", None)
    monkeypatch.setattr(ui_app.settings, "github_models_token", None)
    assert ui_app._providers_for(demo_mode=False) == []
