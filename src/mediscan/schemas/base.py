from pydantic import BaseModel, ConfigDict


class MediScanModel(BaseModel):
    """Base class for every MediScan schema (security hardening, decision #012).

    - extra="forbid": unknown fields are validation errors, never silently
      ignored. Catches malformed extraction output and hallucinated LLM fields
      at the boundary instead of letting them vanish unnoticed.
    - validate_assignment=True: mutating a field AFTER construction re-runs
      all validators — post-construction mutation cannot bypass the guards
      (hole found by Rohit while evaluating frozen=True, decision #013).
    - str_strip_whitespace=True: leading/trailing whitespace is stripped before
      validation, so whitespace-only strings cannot sneak past min_length.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )
