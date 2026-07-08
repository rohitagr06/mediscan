"""AI-layer schemas: the generic request/response for any LLM provider.

WHY THIS FILE EXISTS
    Every AI provider (Gemini, GitHub Models, a fake test client) speaks the
    SAME two shapes: a request (two prompts) in, a response (text +
    provenance) out. Keeping these here — medicine-blind and provider-blind —
    is what lets ONE LLMClient contract stand in front of them all.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from mediscan.schemas.base import MediScanModel


class LLMRequest(MediScanModel):
    """One text-generation request. Medicine-blind on purpose.

    It carries ONLY the two prompts. It never mentions Hemoglobin, severity,
    or reports — a provider must stay reusable for any text task, so it can
    never learn what the words mean (the decision #006 boundary).
    """

    system_prompt: str = Field(
        min_length=1, description="The rules/instructions the model must follow."
    )
    user_prompt: str = Field(
        min_length=1, description="The task, with the fenced FACTS data block."
    )


class LLMResponse(MediScanModel):
    """The ONE uniform response that every provider returns.

    Raw text plus provenance metadata. The orchestration layer only ever
    sees this and never knows which provider produced it. The metadata is
    metrics/provenance (safe to log) — never report content.
    """

    text: str = Field(min_length=1, description="Raw model output (often JSON).")
    provider_name: str = Field(min_length=1, description="Which provider answered.")
    model: str = Field(min_length=1, description="Exact model id used.")
    temperature: float = Field(ge=0, le=1, description="Sampling temperature used.")
    latency_ms: float = Field(ge=0, description="How long the call took, in ms.")


class ExplanationSource(StrEnum):
    """Whether an output was written by AI or by the deterministic floor."""

    AI = "ai"
    DETERMINISTIC = "deterministic"


class ExplanationProvenance(MediScanModel):
    """How one output was produced — recorded on every explanation (#023 spirit).

    Invaluable for debugging ("why does this read oddly at prompt v6?") and for
    Sprint 7's confidence scoring, which weights AI vs rule-written outputs.
    """

    source: ExplanationSource = Field(description="ai or deterministic.")
    prompt_name: str = Field(min_length=1, description="Which prompt template.")
    prompt_version: int = Field(ge=1, description="That template's version.")
    provider: str | None = Field(default=None, description="Winning provider, if AI.")
    model: str | None = Field(default=None, description="Model id, if AI.")
    temperature: float | None = Field(default=None, description="Sampling temp, if AI.")
    timestamp: datetime = Field(description="When the output was produced (UTC).")
