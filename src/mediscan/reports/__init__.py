"""Report rendering: AnalysisReport -> HTML -> PDF (Sprint 8.3).

Two-step split (#035): render_html is a pure, dependency-free string
builder (unit-testable everywhere); render_pdf is the WeasyPrint step,
lazily imported so environments without pango/cairo still work.
"""

from mediscan.reports.pdf import render_pdf, render_report_pdf
from mediscan.reports.render import render_html

__all__ = ["render_html", "render_pdf", "render_report_pdf"]
