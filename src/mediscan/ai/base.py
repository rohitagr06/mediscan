"""The LLMClient contract: one interface, many providers.

WHY THIS FILE EXISTS
    The same lesson as ocr/base.py's OcrEngine. Callers depend on this
    contract, never on Gemini or GitHub directly, so providers are swappable
    and the whole layer is testable with a fake — no network, no keys.
"""

from abc import ABC, abstractmethod

from mediscan.schemas import LLMRequest, LLMResponse


class LLMClient(ABC):
    """Abstract base every AI provider implements.

    The contract's promises:
      - complete() returns a valid LLMResponse, or raises LLMError.
      - it never returns partial/empty junk.
      - it honors the configured timeout (never hangs forever).
      - provider_name identifies it for the audit trail (like OcrEngine's
        method_name attribute).
    """

    provider_name: str

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Send the prompts to the model and return its raw response."""
