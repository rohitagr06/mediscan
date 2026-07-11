"""The orchestrator: one call, whole pipeline, one AnalysisReport (Sprint 7.4).

WHY THIS FILE EXISTS
    Every stage already works alone. This is the CONDUCTOR that calls them in
    order and hands each the typed object the next expects, assembling the
    single master `AnalysisReport`. It owns NO medical logic — it only wires.

TWO ENTRY POINTS
    * analyze_text(full_text, ...)  — the testable CORE: text in, report out.
      Every dependency (AI providers, the RAG retriever, the clock) is
      injectable, so it runs fully offline with zero AI and zero network.
    * analyze_document(path, ...)   — the thin FRONT: it validates + reads the
      file (PyMuPDF / PaddleOCR) into text, then calls analyze_text. The heavy
      OCR libraries are imported LAZILY inside it, so importing THIS module (to
      test the core) never needs them.

THE SAFETY INVARIANT (#006)
    The deterministic verdict (parse -> coverage -> urgency) is computed BEFORE
    any AI runs. Only `coverage.assessed` feeds urgency, so an acknowledged /
    out-of-scope test can never move the verdict. If every AI provider is down,
    the explanations degrade to deterministic templates but the report is still
    complete.
"""

import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from mediscan.ai.explain import assemble_report_explanations
from mediscan.confidence import (
    extraction_confidence,
    grounding_confidence,
    score_confidence,
)
from mediscan.extraction.metadata import extract_patient_context
from mediscan.extraction.parser import parse_lab_text
from mediscan.medical.coverage import classify_coverage
from mediscan.medical.urgency import assess_urgency
from mediscan.observability import get_logger
from mediscan.rag.retriever import RetrievedSnippet, retrieve
from mediscan.schemas import (
    AnalysisReport,
    ExplanationSource,
    ProcessingMetadata,
)

log = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _explanation_signals(explanations) -> tuple[float, int, list[str]]:
    """Derive (grounding, fallback_depth, models_used) from the explanations.

    - grounding: fraction of AI outputs that carried KB sources. No AI outputs
      (all-deterministic, or none produced) -> 1.0: nothing ungrounded was
      asserted, the verdict stands on rules.
    - fallback_depth: how many of the four outputs fell back to the
      deterministic template (0 = AI answered all, 4 = full AI outage). Feeds
      both the confidence penalty and metadata.fallback_count.
    - models_used: the distinct AI models that actually answered, in order.
    """
    if explanations is None:
        return 1.0, 0, []

    outputs = [
        explanations.patient,
        explanations.doctor,
        explanations.dietary,
        explanations.specialist,
    ]
    ai_outputs = [o for o in outputs if o.provenance.source is ExplanationSource.AI]
    grounded = sum(1 for o in ai_outputs if o.provenance.grounding_sources)
    grounding = grounding_confidence(grounded, len(ai_outputs))
    fallback_depth = sum(
        1 for o in outputs if o.provenance.source is ExplanationSource.DETERMINISTIC
    )
    # dict.fromkeys keeps first-seen order while dropping duplicates.
    models_used = list(
        dict.fromkeys(o.provenance.model for o in ai_outputs if o.provenance.model)
    )
    return grounding, fallback_depth, models_used


def analyze_text(
    full_text: str,
    *,
    providers: list | None = None,
    retrieve_fn: Callable[[str], list[RetrievedSnippet]] = retrieve,
    now: Callable[[], datetime] = _utcnow,
    ocr_confidence: float = 1.0,
    ocr_engine: str | None = None,
    extraction_method: str = "rules",
) -> AnalysisReport:
    """Run the medical + AI + confidence pipeline on already-extracted text.

    This is the fully-testable core. Pass ``providers=[]`` (or omit) to run the
    deterministic-only path — every explanation degrades to a template, no AI
    call is made. ``retrieve_fn`` is injectable so tests need no vector DB.

    Returns a complete, validated AnalysisReport.
    """
    started = time.perf_counter()
    providers = providers if providers is not None else []

    # --- deterministic core (no AI) ---------------------------------------
    outcome = parse_lab_text(full_text)
    context = extract_patient_context(full_text)
    coverage = classify_coverage(outcome, context.sex)
    urgency = assess_urgency(coverage.assessed)

    # --- AI explanations (only when there is something graded to explain) --
    explanations = None
    if coverage.assessed:
        explanations = assemble_report_explanations(
            coverage.assessed, urgency, providers, now=now, retrieve_fn=retrieve_fn
        )

    # --- confidence -------------------------------------------------------
    grounding, fallback_depth, models_used = _explanation_signals(explanations)
    confidence = score_confidence(
        ocr=ocr_confidence,
        extraction=extraction_confidence(extraction_method),
        # every parsed result was validated by Pydantic at construction; the
        # AI-structured-repair count isn't surfaced yet, so RC1 uses full marks.
        validation=1.0,
        grounding=grounding,
        fallback_depth=fallback_depth,
    )

    duration_ms = (time.perf_counter() - started) * 1000.0
    metadata = ProcessingMetadata(
        duration_ms=duration_ms,
        models_used=models_used,
        fallback_count=fallback_depth,
        ocr_engine=ocr_engine,
    )

    report = AnalysisReport(
        lab_results=list(outcome.results),
        coverage=coverage,
        urgency=urgency,
        patient_summary=explanations.patient.content if explanations else None,
        doctor_summary=explanations.doctor.content if explanations else None,
        dietary_considerations=(explanations.dietary.content if explanations else []),
        specialist_suggestions=(
            explanations.specialist.content if explanations else []
        ),
        confidence=confidence,
        metadata=metadata,
    )

    # Observability: metrics only, never report text / values (#010).
    log.info(
        "analysis complete: urgency=%s overall_confidence=%.3f fallback=%d "
        "assessed=%d acknowledged=%d",
        urgency.level.value,
        confidence.overall,
        fallback_depth,
        len(coverage.assessed),
        len(coverage.acknowledged),
    )
    return report


def analyze_document(
    path: str | Path,
    *,
    providers: list | None = None,
    retrieve_fn: Callable[[str], list[RetrievedSnippet]] = retrieve,
    now: Callable[[], datetime] = _utcnow,
) -> AnalysisReport:
    """Full pipeline from a FILE on disk to an AnalysisReport.

    Validates the upload (magic bytes), routes text-PDF vs scan, extracts text
    with the right engine (PyMuPDF / PaddleOCR), then hands the text to
    ``analyze_text``. The OCR stack is imported lazily so this module stays
    importable (and the core stays testable) where those libraries aren't
    installed.
    """
    # Lazy imports: keep PyMuPDF/PaddleOCR out of module import so analyze_text
    # is testable without them.
    from mediscan.ingestion.storage import SecureUploadDir
    from mediscan.ingestion.validators import validate_upload
    from mediscan.ocr.factory import get_engine_for
    from mediscan.ocr.router import detect_document_type
    from mediscan.schemas import DocumentType

    path = Path(path)
    doc_type = validate_upload(path)  # coarse: PDF -> PDF_TEXT, image -> IMAGE

    with SecureUploadDir() as upload_dir:
        stored = upload_dir.store(path)
        # refine PDFs into born-digital text vs a scan needing OCR
        if doc_type is DocumentType.PDF_TEXT:
            doc_type = detect_document_type(stored)
        extracted = get_engine_for(doc_type).extract(stored)

    # text PDFs have no OCR step -> full confidence in the read.
    ocr_conf = 1.0 if extracted.ocr_confidence is None else extracted.ocr_confidence
    return analyze_text(
        extracted.full_text,
        providers=providers,
        retrieve_fn=retrieve_fn,
        now=now,
        ocr_confidence=ocr_conf,
        ocr_engine=extracted.extraction_method,
    )
