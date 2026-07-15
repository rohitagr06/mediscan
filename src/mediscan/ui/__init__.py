"""User interface: the Gradio web app (Sprint 8.5).

`analyze` is the testable seam (file path -> rendered HTML + PDF path);
`build_app`/`main` construct and launch the Gradio front end. See ui/app.py.
"""

from mediscan.ui.app import analyze, build_app, main

__all__ = ["analyze", "build_app", "main"]
