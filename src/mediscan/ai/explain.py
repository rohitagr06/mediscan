"""Assembly: turn a verdict into four grounded, safe, provenance-tagged outputs.

WHY THIS FILE EXISTS
    This is where the sprint clicks together. For EACH of the four outputs:
        verdict facts -> prompt (5.3) -> resilient chain (5.7)
        -> validated schema (5.4) -> guardrail (5.9)
        -> on ANY failure, the deterministic template (5.8)
    Every output gets an ExplanationProvenance (ai vs deterministic + which
    model/prompt). Every output ALWAYS has a value — the report is never blank.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import NamedTuple

from mediscan.ai import templates
from mediscan.ai.base import LLMClient
from mediscan.ai.chain import generate_with_fallback
from mediscan.ai.exceptions import LLMError
from mediscan.ai.prompts import (
    DietPrompt,
    DoctorSummaryPrompt,
    PatientSummaryPrompt,
    PromptTemplate,
    SpecialistPrompt,
)
from mediscan.config import settings
from mediscan.rag.retriever import RetrievedSnippet, retrieve
from mediscan.safety.guardrail import check
from mediscan.schemas import ExplanationProvenance, ExplanationSource, UrgencyAssessment
from mediscan.schemas.base import MediScanModel
from mediscan.schemas.medical import SeverityAssessment


class Explanation(NamedTuple):
    """One produced output paired with how it was produced.

    Attributes:
        content: The validated schema object (or list of them) — the actual
            summary/notes/suggestions.
        provenance: Where it came from (ai vs deterministic, prompt, model...).
    """

    content: MediScanModel | list[MediScanModel]
    provenance: ExplanationProvenance


class ReportExplanations(NamedTuple):
    """The four grounded outputs for one report, each with its provenance."""

    patient: Explanation
    doctor: Explanation
    dietary: Explanation
    specialist: Explanation


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _facts_from_verdict(
    assessments: list[SeverityAssessment], urgency: UrgencyAssessment
) -> str:
    """Format the deterministic verdict as the grounding FACTS text."""
    lines = []
    for a in assessments:
        rng = a.range_resolution.reference_range
        rng_txt = f"{rng.low}-{rng.high}" if rng else "unknown"
        sev = a.severity.value if a.severity else "un-assessable"
        direction = a.abnormal_direction.value if a.abnormal_direction else "n/a"
        lines.append(
            f"{a.test_name}: value {a.value}, severity {sev}, "
            f"direction {direction}, normal range {rng_txt}"
        )
    lines.append(f"Overall urgency: {urgency.level.value}.")
    return "\n".join(lines)


def _grounding_snippets(
    assessments: list[SeverityAssessment],
    retrieve_fn: Callable[[str], list[RetrievedSnippet]],
) -> list[RetrievedSnippet]:
    """Retrieve curated KB background for each ABNORMAL finding, de-duplicated.

    For every abnormal finding we build a short query from its test name and
    direction (e.g. "Hemoglobin low: what does it mean?") and ask the KB for
    the closest snippets. Normal findings are skipped — they need no
    explanation. Retrieval is wrapped in try/except so a RAG failure can NEVER
    break the explanation (graceful degradation, #006 spirit): worst case we
    fall back to the verdict facts alone.

    Args:
        assessments: The deterministic per-test judgments.
        retrieve_fn: query -> snippets. The real retriever in production; a
            fake one injected in tests (so no model/network is needed).

    Returns:
        Retrieved snippets across all abnormal findings, first-seen order,
        with duplicates (same text + source) removed.
    """
    seen: set[tuple[str, str]] = set()
    collected: list[RetrievedSnippet] = []
    for a in assessments:
        if a.abnormal_direction is None:
            continue  # normal value -> nothing to explain, skip it
        query = f"{a.test_name} {a.abnormal_direction.value}: what does it mean?"
        try:
            snippets = retrieve_fn(query)
        except Exception:  # noqa: BLE001 - RAG must never break the explanation
            snippets = []
        for snip in snippets:
            key = (snip.text, snip.source)
            if key not in seen:
                seen.add(key)
                collected.append(snip)
    return collected


def _augment_facts(verdict_facts: str, snippets: list[RetrievedSnippet]) -> str:
    """Append retrieved KB background (each with its source) under the verdict.

    The deterministic numbers stay on top exactly as before; RAG only ADDS a
    sourced "BACKGROUND KNOWLEDGE" section beneath them. If nothing was
    retrieved, the facts are unchanged — the AI still explains from the verdict.

    Args:
        verdict_facts: The deterministic FACTS text from ``_facts_from_verdict``.
        snippets: Retrieved KB snippets to fold in (may be empty).

    Returns:
        The combined FACTS string that goes into the prompt.
    """
    if not snippets:
        return verdict_facts
    lines = [
        verdict_facts,
        "",
        "BACKGROUND KNOWLEDGE (from our curated knowledge base — use ONLY these "
        "facts, do not add outside knowledge):",
    ]
    lines.extend(f"- {snip.text} [source: {snip.source}]" for snip in snippets)
    return "\n".join(lines)


def _all_strings(obj: object) -> list[str]:
    """Recursively collect every string in a dumped model (for guardrailing).

    Args:
        obj: A value from ``model_dump()`` — a str, dict, list, or scalar.

    Returns:
        Every string found anywhere inside ``obj`` (nested dicts/lists included).
    """
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in _all_strings(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in _all_strings(v)]
    return []


def _guardrail_ok(value: MediScanModel | list[MediScanModel]) -> bool:
    items = value if isinstance(value, list) else [value]
    for item in items:
        for text in _all_strings(item.model_dump()):
            if not check(text).passed:
                return False
    return True


def _explain(
    prompt: PromptTemplate,
    facts: str,
    providers: list[LLMClient],
    *,
    as_list: bool,
    deterministic: Callable[[], MediScanModel | list[MediScanModel]],
    now: Callable[[], datetime],
    grounding_sources: list[str],
) -> Explanation:
    """Try AI (chain + validate + guardrail); on ANY failure, use the template."""
    try:
        result = generate_with_fallback(
            providers, prompt.build(facts), prompt.output_schema, as_list=as_list
        )
        if _guardrail_ok(result.value):
            return Explanation(
                content=result.value,
                provenance=ExplanationProvenance(
                    source=ExplanationSource.AI,
                    prompt_name=prompt.name,
                    prompt_version=prompt.version,
                    provider=result.provider_name,
                    model=result.model,
                    temperature=settings.llm_temperature,
                    timestamp=now(),
                    grounding_sources=grounding_sources,
                ),
            )
    except LLMError:
        pass  # AllProvidersFailed included

    return Explanation(
        content=deterministic(),
        provenance=ExplanationProvenance(
            source=ExplanationSource.DETERMINISTIC,
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            timestamp=now(),
        ),
    )


def explain_report(
    assessments: list[SeverityAssessment],
    urgency: UrgencyAssessment,
    providers: list[LLMClient],
    *,
    now: Callable[[], datetime] = _utcnow,
    retrieve_fn: Callable[[str], list[RetrievedSnippet]] = retrieve,
) -> ReportExplanations:
    """Produce all four grounded, guardrailed, provenance-tagged outputs."""
    verdict_facts = _facts_from_verdict(assessments, urgency)
    snippets = _grounding_snippets(assessments, retrieve_fn)
    facts = _augment_facts(verdict_facts, snippets)

    # Unique sources, first-seen order. dict.fromkeys() drops duplicates while
    # preserving order (a set would scramble it); list() gives back a plain list.
    sources = list(dict.fromkeys(snip.source for snip in snippets))

    return ReportExplanations(
        patient=_explain(
            PatientSummaryPrompt(),
            facts,
            providers,
            as_list=False,
            deterministic=lambda: templates.patient_summary(assessments, urgency),
            now=now,
            grounding_sources=sources,
        ),
        doctor=_explain(
            DoctorSummaryPrompt(),
            facts,
            providers,
            as_list=False,
            deterministic=lambda: templates.doctor_summary(assessments, urgency),
            now=now,
            grounding_sources=sources,
        ),
        dietary=_explain(
            DietPrompt(),
            facts,
            providers,
            as_list=True,
            deterministic=lambda: templates.dietary(assessments, urgency),
            now=now,
            grounding_sources=sources,
        ),
        specialist=_explain(
            SpecialistPrompt(),
            facts,
            providers,
            as_list=True,
            deterministic=lambda: templates.specialist(assessments, urgency),
            now=now,
            grounding_sources=sources,
        ),
    )
