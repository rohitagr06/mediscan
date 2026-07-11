"""Structured, PHI-safe logging for MediScan.

WHY THIS FILE EXISTS
    A medical tool must be observable in production: we need to see how long
    things take, which fallback rung fired, when a guardrail blocked AI text,
    and when validation failed. But it must NEVER log Protected Health
    Information (decision #010) or secrets. The rule is simple and absolute:
    log EVENTS and METRICS (a category, a provider name, a latency, a count),
    never report text, patient values, raw model output, or API keys.

    This is the ONE place logging is configured, so every module gets a
    consistent, namespaced logger without repeating boilerplate. It is the
    foundation the Sprint-7 orchestration + confidence work builds on.

USAGE
    from mediscan.observability import get_logger
    log = get_logger(__name__)
    log.warning("guardrail blocked AI output: category=%s", category)

    Call configure_logging() ONCE at application startup (an entry point or
    the future orchestrator). Library modules only call get_logger(); they
    never configure handlers themselves.
"""

import logging

from mediscan.config import settings

# Module-level flag so configure_logging() is idempotent (see below).
_CONFIGURED = False


def configure_logging(level: str | None = None) -> None:
    """Set up root logging once, honouring settings.log_level.

    Idempotent on purpose: calling it more than once (repeated entry points,
    or every test) is a no-op after the first call, so handlers never stack up
    and print every line two, three, or ten times.

    Args:
        level: Optional level override (e.g. "DEBUG"). Defaults to
            settings.log_level, which comes from the environment
            (MEDISCAN_LOG_LEVEL) — so verbosity is configured, not hardcoded.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=level or settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger for a module.

    Pass ``__name__`` from the calling module so each log line is attributed to
    the right place (e.g. "mediscan.ai.chain"). Getting a logger has no side
    effects and needs no configuration — it is safe to call at import time.

    SAFETY: never pass PHI or secrets through the returned logger. Log
    categories, counts, provider names, and latencies — never report text,
    patient values, or model output.
    """
    return logging.getLogger(name)
