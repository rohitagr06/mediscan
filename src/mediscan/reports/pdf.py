"""Render the report HTML to PDF bytes via WeasyPrint (Sprint 8.3).

WHY THIS FILE IS SEPARATE FROM render.py
    WeasyPrint needs system C libraries (pango, cairo) that may be absent —
    in the cloud sandbox, and on a misconfigured deploy. Keeping the import
    LAZY and in its own module means:
      - render_html stays importable and testable everywhere, always;
      - the app can detect "PDF unavailable" and degrade to offering the
        print-friendly HTML instead of crashing at import time.

SAFETY NOTE (#010)
    The PDF is produced IN MEMORY and returned as bytes. It is never
    written to a server-side path by this module — the caller hands it
    straight to the user (download button / HTTP response), so no uploaded
    document's analysis ever persists on disk.
"""

from mediscan.schemas.report import AnalysisReport


def render_pdf(html: str) -> bytes:
    """Turn a rendered HTML document into PDF bytes.

    Raises:
        ImportError: If WeasyPrint (or its system libraries) is missing.
            Callers that want to degrade gracefully catch this and fall
            back to serving the HTML itself.
    """
    # Lazy import: the cost (and the system-library requirement) is paid
    # only when a PDF is actually requested.
    from weasyprint import HTML

    # string= tells WeasyPrint the argument IS the document, not a path.
    # write_pdf() with no target returns the bytes instead of writing a file.
    return HTML(string=html).write_pdf()


def render_report_pdf(report: AnalysisReport) -> bytes:
    """Convenience one-call: AnalysisReport -> PDF bytes."""
    from mediscan.reports.render import render_html

    return render_pdf(render_html(report))
