"""The common base class every MediScan schema inherits from.

WHY THIS FILE EXISTS
    Rules that must apply to ALL our data models are defined once, here.
    Any class written as `class Something(MediScanModel)` automatically
    gains every protection below — including models we add in the future.
    That is the point of inheritance: write a rule once, apply it everywhere.

WHAT A "SCHEMA" IS
    A schema is a strict description of the shape data must have (which
    fields exist, their types, their allowed ranges). Pydantic enforces our
    schemas at runtime: creating an object with bad data raises an error
    instead of letting the bad data flow onward.
"""

from pydantic import BaseModel, ConfigDict


class MediScanModel(BaseModel):
    """Base class for every MediScan schema (security hardening, #012/#013).

    Protections applied to all subclasses:

    - extra="forbid": unknown fields are validation errors, never silently
      ignored. Catches malformed extraction output and hallucinated LLM
      fields at the boundary instead of letting them vanish unnoticed.
    - validate_assignment=True: changing a field AFTER the object was
      created re-runs all validators, so mutation cannot bypass the guards
      (hole found by Rohit while evaluating frozen=True, decision #013).
    - str_strip_whitespace=True: leading/trailing whitespace is stripped
      before validation, so a name like "   " cannot sneak past min_length.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )
