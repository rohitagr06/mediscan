"""One provider for every OpenAI-compatible endpoint (Gemini + GitHub Models).

WHY ONE CLASS
    Gemini and GitHub Models both speak the OpenAI Chat Completions API, so a
    single class — configured with (base_url, api_key, model) — is every
    provider in the #004 chain. The three builders at the bottom produce the
    three rungs. Adding a fourth OpenAI-compatible provider later is one more
    builder, zero new code.

    The openai SDK is imported LAZILY so this module (and the test suite) load
    without it. Providers stay medicine-blind: they only send prompts and
    return text + metadata.
"""

import time

from pydantic import SecretStr

from mediscan.ai.base import LLMClient
from mediscan.ai.exceptions import LLMError
from mediscan.config import settings
from mediscan.schemas import LLMRequest, LLMResponse


class OpenAICompatibleProvider(LLMClient):
    """An LLMClient backed by any OpenAI-compatible endpoint."""

    def __init__(
        self,
        *,
        provider_name: str,
        base_url: str,
        api_key: SecretStr | None,
        model: str,
    ) -> None:
        self.provider_name = provider_name
        self._base_url = base_url
        self._api_key = api_key
        self.model = model
        self._client = None  # built on first use (lazy)

    def _get_client(self) -> "OpenAI":  # noqa: F821 (lazy import, string annotation)
        """Build (once) and return the underlying OpenAI SDK client.

        Lazy: the openai SDK is imported and the client constructed only on
        first use, so the module loads without the SDK (mock-first tests) and
        the secret key is unwrapped at the last possible moment.

        Returns:
            The cached ``openai.OpenAI`` client for this provider.

        Raises:
            LLMError: If this provider has no API key configured.
        """
        if self._client is None:
            if self._api_key is None:
                raise LLMError(f"{self.provider_name}: API key is not configured")
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self._base_url,
                api_key=self._api_key.get_secret_value(),  # unwrap at last moment
                timeout=settings.llm_timeout_seconds,  # plain seconds
            )
        return self._client

    def close(self) -> None:
        """Close the underlying HTTP connection pool, if one was opened.

        The OpenAI client holds an httpx connection pool. In a long-lived
        service, closing it on shutdown prevents pools from accumulating.
        Safe to call even if the client was never built. (Sprint 7's
        orchestration should own provider lifecycle.)
        """
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "OpenAICompatibleProvider":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Send the prompts to the model and return the raw response.

        Args:
            request: The system + user prompts to send (medicine-blind).

        Returns:
            An LLMResponse with the model's text plus provenance metadata
            (provider, model, temperature, latency).

        Raises:
            LLMError: On any SDK/network failure (normalized to the exception
                type only — no key or content leaked) or an empty response.
        """
        client = self._get_client()
        start = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=self.model,
                temperature=settings.llm_temperature,
                response_format={"type": "json_object"},  # generic "give me JSON"
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
            )
        except Exception as err:
            raise LLMError(
                f"{self.provider_name} call failed ({type(err).__name__})"
            ) from err

        latency_ms = (time.perf_counter() - start) * 1000
        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise LLMError(f"{self.provider_name} returned an empty response")

        return LLMResponse(
            text=text,
            provider_name=self.provider_name,
            model=self.model,
            temperature=settings.llm_temperature,
            latency_ms=latency_ms,
        )


# --- The three rungs of the #004 chain, as builders ---


def gemini_provider() -> OpenAICompatibleProvider:
    """Build the Gemini provider (rung 1 of the #004 chain) from config."""
    return OpenAICompatibleProvider(
        provider_name="gemini",
        base_url=settings.gemini_base_url,
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
    )


def github_primary_provider() -> OpenAICompatibleProvider:
    """Build the GitHub Models primary provider (rung 2, GPT-4.1-mini)."""
    return OpenAICompatibleProvider(
        provider_name="github-primary",
        base_url=settings.github_base_url,
        api_key=settings.github_models_token,
        model=settings.github_primary_model,
    )


def github_fallback_provider() -> OpenAICompatibleProvider:
    """Build the GitHub Models fallback provider (rung 3, Phi-4)."""
    return OpenAICompatibleProvider(
        provider_name="github-fallback",
        base_url=settings.github_base_url,
        api_key=settings.github_models_token,
        model=settings.github_fallback_model,
    )
