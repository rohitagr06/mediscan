"""Exceptions for the AI explanation layer."""


class LLMError(Exception):
    """A provider failed to produce a usable response.

    Every provider maps its own SDK/network errors to THIS type, so callers
    handle one exception instead of a dozen vendor-specific ones. Task 5.7
    will add AllProvidersFailed alongside it.
    """


class AllProvidersFailed(LLMError):
    """Every provider in the chain failed.

    The caller must now fall back to the deterministic templates (task 5.8).
    Subclasses LLMError so a caller catching LLMError catches this too.
    """
