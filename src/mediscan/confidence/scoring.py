"""The confidence scoring engine (Sprint 7).

WHY THIS FILE EXISTS
    "How much should you trust this report?" is not one number — it's a blend
    of how well each stage did: did we read the pixels cleanly (ocr)? did rules
    or a fallback LLM extract the fields (extraction)? did the structured output
    validate first try (validation)? were the AI explanations grounded in our
    sourced KB (grounding)? This module turns those signals into a populated
    ConfidenceBreakdown, deterministically (no AI decides trust — #011/#006).

    Everything here is a PURE function: same inputs -> same output, no state,
    no I/O. That makes it trivial to test and safe to call anywhere.

HOW THE OVERALL SCORE IS BUILT
    overall = (w_ocr·ocr + w_ext·extraction + w_val·validation + w_gnd·grounding)
              × max(floor, 1 − k · fallback_depth)
    The weights (summing to 1.0), the penalty rate k, and the floor all live in
    config, so a clinician can retune trust without touching code.
"""

from mediscan.config import settings
from mediscan.schemas import ConfidenceBreakdown

# How much to trust each extraction METHOD. Deterministic rules are more
# trustworthy than an LLM guess, so rules score higher. Data, not logic —
# extend when an LLM-extraction fallback is actually added.
_EXTRACTION_METHOD_SCORES: dict[str, float] = {
    "rules": 1.0,  # regex/table parsing — auditable, deterministic
    "llm": 0.7,  # a language model had to read the fields — less certain
}


def extraction_confidence(method: str) -> float:
    """Confidence from HOW the fields were extracted (rules beat an LLM).

    An unknown method is treated as the cautious LLM score rather than a
    confident 1.0 — we never assume trust we can't justify.
    """
    return _EXTRACTION_METHOD_SCORES.get(method, 0.7)


def validation_confidence(repair_retries: int) -> float:
    """1.0 when structured output validated on the first try; less if it needed
    repair.

    Each repair-retry (the AI layer re-asking the model for valid JSON) shaves
    0.25 off, floored at 0.0. Zero retries -> full marks.
    """
    return max(0.0, 1.0 - 0.25 * repair_retries)


def grounding_confidence(grounded_outputs: int, total_outputs: int) -> float:
    """Fraction of AI outputs that were backed by RAG sources.

    When there are NO AI outputs (the fully deterministic path), there is
    nothing ungrounded to worry about, so this is 1.0 — the verdict stands on
    auditable rules, not model memory.
    """
    if total_outputs == 0:
        return 1.0
    return grounded_outputs / total_outputs


def score_confidence(
    *,
    ocr: float,
    extraction: float,
    validation: float,
    grounding: float,
    fallback_depth: int = 0,
    parsed_count: int | None = None,
) -> ConfidenceBreakdown:
    """Blend the four per-stage scores into a ConfidenceBreakdown.

    Args:
        ocr / extraction / validation / grounding: per-stage confidences, each
            already in [0.0, 1.0]. (Use the helpers above to derive
            extraction/validation/grounding from raw pipeline facts.)
        fallback_depth: how deep the AI fallback chain went (0 = the primary
            model answered, 1 = second rung, ...). Higher -> more penalty.
        parsed_count: how many lab rows were actually parsed from the
            document. When this is 0, the analysis has NO content — the stages
            each "succeeded" on nothing — so ``overall`` collapses to 0.0
            rather than reporting a misleading high number. ``None`` (the
            default) means "not supplied", and the blend behaves as before.

    Returns:
        A ConfidenceBreakdown carrying the four inputs unchanged plus a
        weighted `overall` in [0.0, 1.0]. Keyword-only args (the `*`) so a call
        can never silently swap two scores by position.

    The sub-scores are validated to [0, 1] by ConfidenceBreakdown itself, so an
    out-of-range input fails loudly rather than skewing the blend.
    """
    weighted = (
        settings.confidence_weight_ocr * ocr
        + settings.confidence_weight_extraction * extraction
        + settings.confidence_weight_validation * validation
        + settings.confidence_weight_grounding * grounding
    )
    # Deeper fallback -> lower trust, but never below the floor.
    penalty = max(
        settings.confidence_fallback_floor,
        1.0 - settings.confidence_fallback_k * fallback_depth,
    )
    overall = weighted * penalty

    # Nothing parsed => nothing to trust. A report that read ZERO values must
    # never present as confident, however cleanly each empty stage "passed".
    if parsed_count == 0:
        overall = 0.0

    return ConfidenceBreakdown(
        ocr=ocr,
        extraction=extraction,
        validation=validation,
        grounding=grounding,
        # round to kill float noise (0.7999999) before the [0,1] validator.
        overall=round(overall, 4),
    )
