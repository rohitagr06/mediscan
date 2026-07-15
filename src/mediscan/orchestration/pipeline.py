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

import asyncio
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from mediscan.ai.explain import assemble_report_explanations_async
from mediscan.confidence import (
    extraction_confidence,
    grounding_confidence,
    score_confidence,
)
from mediscan.extraction.metadata import extract_patient_context
from mediscan.extraction.parser import parse_lab_text
from mediscan.medical.coverage import classify_coverage
from mediscan.medical.urgency import assess_urgency
from mediscan.observability import configure_logging, get_logger
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


async def analyze_text_async(
    full_text: str,
    *,
    providers: list | None = None,
    retrieve_fn: Callable[[str], list[RetrievedSnippet]] = retrieve,
    now: Callable[[], datetime] = _utcnow,
    ocr_confidence: float = 1.0,
    ocr_engine: str | None = None,
    extraction_method: str = "rules",
    timeout: float | None = None,
) -> AnalysisReport:
    """Async core: run the whole pipeline on already-extracted text (Sprint 7.6).

    The deterministic stages (parse -> coverage -> urgency) are fast and stay
    synchronous; only the four AI explanation outputs are run CONCURRENTLY, each
    bounded by ``timeout``. Pass ``providers=[]`` (or omit) for the
    deterministic-only path — no AI call is made. ``retrieve_fn`` is injectable
    so tests need no vector DB. Returns a complete, validated AnalysisReport.
    """
    started = time.perf_counter()
    providers = providers if providers is not None else []

    # --- deterministic core (no AI) ---------------------------------------
    outcome = parse_lab_text(full_text)
    # Observability: COUNTS only — never the parsed rows, names, or values.
    log.debug(
        "parsed %d rows (%d unparsed)",
        len(outcome.results),
        len(outcome.unparsed_lines),
    )
    context = extract_patient_context(full_text)
    coverage = classify_coverage(outcome, context.sex)
    log.debug(
        "coverage: sex=%s assessed=%d acknowledged=%d",
        context.sex.value,
        len(coverage.assessed),
        len(coverage.acknowledged),
    )
    urgency = assess_urgency(coverage.assessed)

    # --- AI explanations (only when there is something graded to explain) --
    explanations = None
    if coverage.assessed:
        explanations = await assemble_report_explanations_async(
            coverage.assessed,
            urgency,
            providers,
            now=now,
            retrieve_fn=retrieve_fn,
            timeout=timeout,
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
        # 0 parsed rows => overall confidence collapses to 0 (a report that
        # read nothing must never look confident). See score_confidence.
        parsed_count=len(outcome.results),
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
        "assessed=%d acknowledged=%d duration_ms=%.1f",
        urgency.level.value,
        confidence.overall,
        fallback_depth,
        len(coverage.assessed),
        len(coverage.acknowledged),
        duration_ms,
    )
    return report


def analyze_text(
    full_text: str,
    *,
    providers: list | None = None,
    retrieve_fn: Callable[[str], list[RetrievedSnippet]] = retrieve,
    now: Callable[[], datetime] = _utcnow,
    ocr_confidence: float = 1.0,
    ocr_engine: str | None = None,
    extraction_method: str = "rules",
    timeout: float | None = None,
) -> AnalysisReport:
    """Synchronous wrapper over analyze_text_async (the #7.1 API decision).

    Callers in ordinary sync code get the same one-call convenience; async
    callers await analyze_text_async directly. asyncio.run spins up a private
    event loop for this call, so it must NOT be called from inside a running
    loop (use the async form there).
    """
    configure_logging()  # this sync call is an RC1 entry point (Sprint 8 UI later)
    return asyncio.run(
        analyze_text_async(
            full_text,
            providers=providers,
            retrieve_fn=retrieve_fn,
            now=now,
            ocr_confidence=ocr_confidence,
            ocr_engine=ocr_engine,
            extraction_method=extraction_method,
            timeout=timeout,
        )
    )


def _extract_text_from_document(path: Path) -> tuple[str, float, str]:
    """Validate, route, and read a file into (full_text, ocr_confidence, engine).

    The OCR stack is imported LAZILY so importing this module (to test the core)
    never needs PyMuPDF/PaddleOCR. Text PDFs have no OCR step, so their read
    confidence is a full 1.0.
    """
    from mediscan.ingestion.storage import SecureUploadDir
    from mediscan.ingestion.validators import validate_upload
    from mediscan.ocr.factory import get_engine_for
    from mediscan.ocr.router import detect_document_type
    from mediscan.schemas import DocumentType

    doc_type = validate_upload(path)  # coarse: PDF -> PDF_TEXT, image -> IMAGE
    with SecureUploadDir() as upload_dir:
        stored = upload_dir.store(path)
        # refine PDFs into born-digital text vs a scan needing OCR
        if doc_type is DocumentType.PDF_TEXT:
            doc_type = detect_document_type(stored)
        extracted = get_engine_for(doc_type).extract(stored)

    ocr_conf = 1.0 if extracted.ocr_confidence is None else extracted.ocr_confidence
    return extracted.full_text, ocr_conf, extracted.extraction_method


async def analyze_document_async(
    path: str | Path,
    *,
    providers: list | None = None,
    retrieve_fn: Callable[[str], list[RetrievedSnippet]] = retrieve,
    now: Callable[[], datetime] = _utcnow,
    timeout: float | None = None,
) -> AnalysisReport:
    """Async: a FILE on disk -> a full AnalysisReport (extract then analyze)."""
    full_text, ocr_conf, engine = _extract_text_from_document(Path(path))
    return await analyze_text_async(
        full_text,
        providers=providers,
        retrieve_fn=retrieve_fn,
        now=now,
        ocr_confidence=ocr_conf,
        ocr_engine=engine,
        timeout=timeout,
    )


def analyze_document(
    path: str | Path,
    *,
    providers: list | None = None,
    retrieve_fn: Callable[[str], list[RetrievedSnippet]] = retrieve,
    now: Callable[[], datetime] = _utcnow,
    timeout: float | None = None,
) -> AnalysisReport:
    """Synchronous wrapper over analyze_document_async — the file-in entry point."""
    configure_logging()  # RC1 entry point (Sprint 8 UI will own this later)
    return asyncio.run(
        analyze_document_async(
            path,
            providers=providers,
            retrieve_fn=retrieve_fn,
            now=now,
            timeout=timeout,
        )
    )
