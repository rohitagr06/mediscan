"""Knowledge-base schemas: validated reference-range facts.

WHY THIS FILE EXISTS
    The medical engine falls back to curated generalized adult reference
    ranges when a report omits its own. Those ranges are medical facts,
    so they are stored as reviewable JSON and VALIDATED at load time:
    a malformed entry (low >= high, a critical threshold on the wrong
    side of the normal bound) fails loudly on startup, never silently
    mis-ranging a value.
"""

from pydantic import Field, model_validator

from mediscan.schemas.base import MediScanModel


class ReferenceRangeEntry(MediScanModel):
    """One curated reference-range fact for a single lab test.

    test_name MUST match the canonical output of normalize_test_name so
    the engine's lookup succeeds. Critical thresholds are optional and,
    when present, must sit OUTSIDE the normal range (a critical-low is
    below the normal low; a critical-high is above the normal high).
    """

    test_name: str = Field(
        min_length=1, description="Canonical test name (matches normalization output)."
    )
    unit: str | None = Field(
        default=None, description="Canonical unit for this test, if any."
    )
    # allow_inf_nan=False rejects NaN/Infinity. Without it a NaN bound
    # would slip through the check_bounds comparison below (every
    # comparison with NaN is False), silently disabling that bound — an
    # "unknown masquerades as fine" hole (#011) hiding inside the KB.
    low: float = Field(
        allow_inf_nan=False, description="Lower bound of the normal adult range."
    )
    high: float = Field(
        allow_inf_nan=False, description="Upper bound of the normal adult range."
    )
    critical_low: float | None = Field(
        default=None,
        allow_inf_nan=False,
        description="Value at/below which the result is critical.",
    )
    critical_high: float | None = Field(
        default=None,
        allow_inf_nan=False,
        description="Value at/above which the result is critical.",
    )
    source: str = Field(
        min_length=1,
        description="Citation for these numbers — mandatory (no anonymous facts).",
    )

    @model_validator(mode="after")
    def check_bounds(self):
        if self.low >= self.high:
            raise ValueError(
                f"{self.test_name}: low ({self.low}) must be < high ({self.high})"
            )
        if self.critical_low is not None and self.critical_low >= self.low:
            raise ValueError(
                f"{self.test_name}: critical_low ({self.critical_low}) must be "
                f"below the normal low ({self.low})"
            )
        if self.critical_high is not None and self.critical_high <= self.high:
            raise ValueError(
                f"{self.test_name}: critical_high ({self.critical_high}) must be "
                f"above the normal high ({self.high})"
            )
        return self


class KnowledgeSnippet(MediScanModel):
    """One self-contained, sourced fact, ready to be embedded and retrieved."""

    text: str = Field(min_length=1, description="The fact, as a short sentence.")
    source: str = Field(min_length=1, description="Citation for this fact.")
    test_name: str = Field(min_length=1, description="Test this fact is about.")


class TestKnowledge(MediScanModel):
    """Curated, sourced explanation content for one lab test.

    Turned into individually-retrievable KnowledgeSnippets by to_snippets().
    Every statement is informational, never a diagnosis or treatment.
    """

    test_name: str = Field(min_length=1, description="Canonical test name.")
    what_it_measures: str = Field(min_length=1)
    low_meaning: str = Field(min_length=1, description="What a low value can indicate.")
    high_meaning: str = Field(
        min_length=1, description="What a high value can indicate."
    )
    dietary_note: str | None = Field(default=None)
    specialist: str | None = Field(default=None)
    source: str = Field(min_length=1, description="Citation — mandatory (#019).")

    def to_snippets(self) -> list[KnowledgeSnippet]:
        """Split this entry into one sourced snippet per idea (chunking)."""

        def snip(text: str) -> KnowledgeSnippet:
            # every snippet carries the SAME source + test_name as this entry
            return KnowledgeSnippet(
                text=text, source=self.source, test_name=self.test_name
            )

        snippets = [
            snip(f"{self.test_name}: {self.what_it_measures}"),
            snip(f"A low {self.test_name} can be associated with: {self.low_meaning}"),
            snip(
                f"A high {self.test_name} can be associated with: {self.high_meaning}"
            ),
        ]
        if self.dietary_note:
            snippets.append(
                snip(f"Dietary note for {self.test_name}: {self.dietary_note}")
            )
        if self.specialist:
            snippets.append(
                snip(
                    f"For an abnormal {self.test_name}, a relevant specialist "
                    f"is a {self.specialist}."
                )
            )
        return snippets
