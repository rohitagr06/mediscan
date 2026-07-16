"""The resilient fallback chain: try providers in order, then give up cleanly.

WHY THIS FILE EXISTS
    Free tiers rate-limit and go down (we saw a real 429 from Gemini). This
    chain isolates each failure: it retries a provider a few times with
    EXPONENTIAL BACKOFF (polite to rate limits), then moves to the next
    provider, and only raises AllProvidersFailed when every rung is spent —
    at which point the caller (5.10) uses the deterministic templates (5.8).
"""

import time
from collections.abc import Callable
from typing import NamedTuple

from mediscan.ai.base import LLMClient
from mediscan.ai.exceptions import AllProvidersFailed, LLMError
from mediscan.ai.structured import generate_structured
from mediscan.config import settings
from mediscan.observability import get_logger
from mediscan.schemas import LLMRequest
from mediscan.schemas.base import MediScanModel

log = get_logger(__name__)


class ChainResult(NamedTuple):
    """The winning output plus which provider/model produced it (provenance)."""

    value: MediScanModel | list[MediScanModel]
    provider_name: str
    model: str


def generate_with_fallback(
    providers: list[LLMClient],
    request: LLMRequest,
    schema: type[MediScanModel],
    *,
    as_list: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> ChainResult:
    """Try each provider in order; per-provider exponential-backoff retries.

    `sleep` is injectable so tests run instantly (pass a no-op).
    Raises AllProvidersFailed only when every provider is exhausted.
    """
    if not providers:
        # Demo/deterministic mode passes no providers ON PURPOSE: this is
        # the intended no-AI path, not a failure. Signal it quietly and let
        # the caller drop to the deterministic template.
        log.debug("no AI providers configured; using deterministic templates")
        raise AllProvidersFailed("no AI providers configured")

    last_error: LLMError | None = None
    for provider in providers:
        for attempt in range(settings.llm_max_retries + 1):
            try:
                value = generate_structured(provider, request, schema, as_list=as_list)
                return ChainResult(
                    value=value,
                    provider_name=provider.provider_name,
                    model=getattr(provider, "model", ""),
                )
            except LLMError as err:
                # Transient (429 / timeout) or a bad-output failure. Keep the
                # most recent error so the final AllProvidersFailed can chain
                # it for debugging. Back off and retry the SAME provider; if
                # it's the last attempt, fall through to the next provider.
                last_error = err
                # Observability: record the provider + attempt + error TYPE
                # (never the request or any response text — no PHI in logs).
                log.warning(
                    "provider attempt failed: provider=%s attempt=%d error=%s",
                    provider.provider_name,
                    attempt,
                    type(err).__name__,
                )
                if attempt < settings.llm_max_retries:
                    sleep(2**attempt)  # 1s, 2s, 4s, ...

    # Chain the last underlying failure (429/timeout/validation) as the cause.
    log.error("all AI providers failed after %d provider(s)", len(providers))
    raise AllProvidersFailed("all AI providers failed") from last_error
