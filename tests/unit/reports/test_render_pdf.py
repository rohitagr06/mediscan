"""Smoke test: WeasyPrint turns our HTML into real PDF bytes (Sprint 8.3).

Skipped automatically wherever WeasyPrint or its system libraries
(pango/cairo) are absent — the cloud sandbox, or a Mac where the Homebrew
libs aren't on the loader path — and runs for real once the libraries
resolve (CI, and a properly-configured Mac).
"""

import pytest

from mediscan.reports.render import render_html
from mediscan.schemas.report import AnalysisReport

# We cannot use pytest.importorskip alone: WeasyPrint imports fine as a
# Python package, then fails when it dlopen()s pango/cairo — which raises
# OSError, NOT ImportError. importorskip only catches ImportError, so the
# OSError would escape and abort the WHOLE test session at collection time.
# Catch BOTH and turn either into a clean skip of just this file.
try:
    import weasyprint  # noqa: F401 - imported only to probe availability
except (ImportError, OSError) as exc:  # pragma: no cover - env-dependent
    pytest.skip(
        f"WeasyPrint unavailable ({type(exc).__name__}): {exc}",
        allow_module_level=True,
    )


def test_pdf_bytes_are_produced_and_look_like_a_pdf():
    from mediscan.reports.pdf import render_report_pdf

    pdf = render_report_pdf(AnalysisReport())
    # Every real PDF file starts with the magic bytes "%PDF-".
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000  # a real multi-element document, not a stub


def test_full_report_renders_to_pdf(full_report):
    # `full_report` comes from conftest.py — shared with the HTML tests,
    # no cross-file import needed.
    from mediscan.reports.pdf import render_pdf

    pdf = render_pdf(render_html(full_report))
    assert pdf.startswith(b"%PDF-")
