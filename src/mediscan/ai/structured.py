"""Turn a model's raw text into a validated schema object (with one repair).

WHY THIS FILE EXISTS
    Models sometimes return almost-right JSON — a trailing comma, a missing
    field, a code-fence wrapper. Rather than crash or accept garbage, we
    validate strictly against the target schema and, on failure, send ONE
    corrective retry. One repair, then we give up and let the caller fall
    back (chain in 5.7, deterministic template in 5.8). Bounded, never a loop.
"""

import json

from pydantic import ValidationError

from mediscan.ai.base import LLMClient
from mediscan.ai.exceptions import LLMError
from mediscan.schemas import LLMRequest
from mediscan.schemas.base import MediScanModel


def _strip_code_fence(text: str) -> str:
    """Drop a leading/trailing ```json ... ``` wrapper some models add."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t[3:]
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def _parse_and_validate(
    text: str, schema: type[MediScanModel], as_list: bool
) -> MediScanModel | list[MediScanModel]:
    """Parse JSON and validate against schema. Raises on any problem."""
    data = json.loads(_strip_code_fence(text))
    if as_list:
        if not isinstance(data, list):
            raise ValueError("expected a JSON list")
        return [schema.model_validate(item) for item in data]
    return schema.model_validate(data)


def generate_structured(
    client: LLMClient,
    request: LLMRequest,
    schema: type[MediScanModel],
    *,
    as_list: bool = False,
) -> MediScanModel | list[MediScanModel]:
    """Call the model; parse+validate its JSON; retry ONCE on failure.

    Returns a validated schema instance (or a list of them when as_list).
    Raises LLMError if even the single repair attempt fails.
    """
    attempt_request = request
    last_error: Exception | None = None

    for _ in range(2):  # initial attempt + exactly one repair
        response = client.complete(attempt_request)
        try:
            return _parse_and_validate(response.text, schema, as_list)
        except (json.JSONDecodeError, ValidationError, ValueError) as err:
            last_error = err
            # Feed the error back so the model can fix its own mistake. This
            # goes to the provider, never to a log.
            attempt_request = LLMRequest(
                system_prompt=request.system_prompt,
                user_prompt=(
                    f"{request.user_prompt}\n\nYour previous reply was invalid "
                    f"({type(err).__name__}). Return ONLY valid JSON matching "
                    "the requested shape."
                ),
            )

    # Clean message (no AI/report content); original chained for debugging.
    raise LLMError(
        "structured output failed validation after one repair"
    ) from last_error
