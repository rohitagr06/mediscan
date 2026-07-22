"""The Gradio web app: upload a lab report, get an analysis + PDF (Sprint 8.5).

WHY THIS FILE EXISTS
    This is the stranger-facing face of MediScan. Everything below is a THIN
    wrapper over the engine — `analyze_document()` does the real work; this
    module only moves a file in and renders the result out. It adds NO
    medical logic (#006): severity, urgency and coverage are already decided
    inside the report by the time we render it.

THE SEAM
    `analyze(file_path, demo_mode) -> (display_html, pdf_path)` is the single
    function the UI calls and the E2E test (8.8) drives. Keeping it a plain
    function — not tangled into Gradio callbacks — is what makes the whole
    stranger-path testable without a browser.

SAFETY
    - Uploads go through the existing front door: `validate_upload` (size +
      extension + magic-bytes + anti-spoof) then `SecureUploadDir` (a private
      mode-700 temp dir that self-destructs). The uploaded file never
      outlives the `with` block (#010).
    - Demo mode (the default) runs `providers=[]`: no API keys, no network,
      a fully deterministic report. The safe public default (#036).
    - Errors are shown as friendly text; internal details/PHI are never
      surfaced to the user.
"""

import html as _html
import os
import tempfile
from pathlib import Path

from mediscan.ai.providers.openai_compatible import (
    gemini_provider,
    github_fallback_provider,
    github_primary_provider,
)
from mediscan.config import settings
from mediscan.ingestion.exceptions import UploadValidationError
from mediscan.ingestion.storage import SecureUploadDir
from mediscan.ingestion.validators import validate_upload
from mediscan.observability import get_logger
from mediscan.orchestration.pipeline import analyze_document
from mediscan.reports.pdf import render_pdf
from mediscan.reports.render import render_html
from mediscan.schemas.report import AnalysisReport

_logger = get_logger(__name__)

_ACCEPTED_TYPES = [".pdf", ".png", ".jpg", ".jpeg"]


def _providers_for(demo_mode: bool) -> list:
    """Build the AI provider chain, or an empty list for demo mode.

    demo_mode -> []  (deterministic: template explanations, no keys, no net).
    Otherwise, add each provider whose API key is actually configured — a
    missing key simply drops that rung, so a half-configured environment
    degrades instead of crashing (#004 chain order preserved).
    """
    # settings.demo_mode is a HARD override for public deployments: when
    # set, no providers are built whatever the UI toggle says.
    if demo_mode or settings.demo_mode:
        return []
    providers: list = []
    if settings.gemini_api_key is not None:
        providers.append(gemini_provider())
    if settings.github_models_token is not None:
        providers.append(github_primary_provider())
        providers.append(github_fallback_provider())
    return providers


def _no_retrieval(_query: str) -> list:
    """No-op retriever for the demo path.

    With no AI providers there is nothing to ground, so we skip RAG
    entirely. This is what keeps the slim deploy from importing ChromaDB
    and the embedding model at runtime (Sprint 8.10).
    """
    return []


def _display_html(report: AnalysisReport) -> str:
    """Wrap the full report document in a sandboxed iframe for on-page display.

    render_html returns a COMPLETE <html> document with its own <style>
    (page margins, body font, etc.). Dropping that straight into the Gradio
    page would let those rules restyle Gradio itself. An <iframe srcdoc>
    isolates the document's CSS completely — the report renders exactly as
    it will in the PDF, in its own little sealed frame.
    """
    full = render_html(report)
    escaped = _html.escape(full, quote=True)  # srcdoc holds an HTML string
    return (
        f'<iframe title="MediScan report" '
        f'style="width:100%;height:820px;border:1px solid #ccd;'
        f'border-radius:6px;background:#fff" srcdoc="{escaped}"></iframe>'
    )


def _pdf_to_tempfile(report: AnalysisReport) -> str:
    """Render the report to PDF and write it to a temp path for download.

    The PDF is generated IN MEMORY (bytes); we write it to an ephemeral
    temp file only because a download widget needs a path to serve. It is
    never written into the repo or a persistent app directory (#010).
    """
    pdf_bytes = render_pdf(render_html(report))
    fd, path = tempfile.mkstemp(prefix="mediscan_report_", suffix=".pdf")
    try:
        os.write(fd, pdf_bytes)
    finally:
        os.close(fd)  # always close the OS handle, even if write fails
    return path


def _error_box(message: str) -> str:
    """A small red-bordered notice for the display panel."""
    return (
        '<div style="padding:12px;border:1px solid #d84315;border-radius:6px;'
        f'background:#fff3e0;color:#8a2f13">{_html.escape(message)}</div>'
    )


def analyze(file_path: str | None, demo_mode: bool = True) -> tuple[str, str | None]:
    """THE SEAM: a file path in -> (display HTML, PDF path or None).

    Never raises: every failure becomes a friendly HTML notice and a None
    PDF path, so the UI can always render something.
    """
    if not file_path:
        return _error_box("Please upload a lab report (PDF or photo) first."), None

    source = Path(file_path)

    # 1) Validate BEFORE touching the engine (cheap, and it's the safety gate).
    try:
        validate_upload(source)
    except UploadValidationError as exc:
        # UploadValidationError messages are safe to show (type/size only).
        return _error_box(f"That file couldn’t be accepted: {exc}"), None

    # 2) Store in a private temp dir + analyze; the upload dies with the block.
    try:
        with SecureUploadDir() as upload_dir:
            stored = upload_dir.store(source)
            providers = _providers_for(demo_mode)
            kwargs = {"providers": providers}
            if not providers:
                # No AI to ground -> skip RAG so the slim demo never
                # loads ChromaDB + the embedding model (Sprint 8.10).
                kwargs["retrieve_fn"] = _no_retrieval
            report = analyze_document(stored, **kwargs)
    except Exception:  # noqa: BLE001 - the UI must never crash on a bad report
        _logger.exception("analysis_failed")  # PHI-safe: event name only
        return (
            _error_box(
                "Sorry — something went wrong analysing that report. "
                "Please try a different file."
            ),
            None,
        )

    # 3) Render the result (in memory) + a downloadable PDF.
    display = _display_html(report)
    try:
        pdf_path = _pdf_to_tempfile(report)
    except Exception:  # noqa: BLE001 - no PDF engine? still show the analysis
        _logger.warning("pdf_render_unavailable")
        pdf_path = None
    return display, pdf_path


def build_app():
    """Construct (but do not launch) the Gradio Blocks app.

    Imported lazily so the whole module stays importable where Gradio is
    absent (the cloud sandbox) — only building/launching needs it.
    """
    import gradio as gr

    with gr.Blocks(title="MediScan by DipsAI") as app:
        gr.Markdown(
            "# MediScan by DipsAI\n"
            "Upload a lab report (PDF or photo) and get a clear, colour-coded "
            "analysis plus a downloadable PDF. **Not medical advice** — always "
            "consult a doctor."
        )
        with gr.Row():
            with gr.Column(scale=1):
                file_in = gr.File(
                    label="Lab report",
                    file_types=_ACCEPTED_TYPES,
                    type="filepath",
                )
                demo_toggle = gr.Checkbox(
                    label="Demo mode (deterministic, no AI keys needed)",
                    value=settings.demo_mode,
                    # Locked ON when the deployment forces demo mode (a
                    # public Space) so it cannot be toggled into a keyed run.
                    interactive=not settings.demo_mode,
                )
                run = gr.Button("Analyze", variant="primary")
                pdf_out = gr.File(label="Download PDF report")
            with gr.Column(scale=2):
                html_out = gr.HTML(label="Analysis")

        run.click(
            fn=analyze,
            inputs=[file_in, demo_toggle],
            outputs=[html_out, pdf_out],
        )
    return app


def main() -> None:
    """Entry point: `uv run python -m mediscan.ui` launches the app locally."""
    build_app().launch()


if __name__ == "__main__":
    main()
