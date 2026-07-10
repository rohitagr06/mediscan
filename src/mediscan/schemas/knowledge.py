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


class RangeBounds(MediScanModel):
    """A normal range plus optional critical thresholds.

    Used both as a test's shared/default bounds and as a per-sex block.
    Supports ONE-SIDED ranges: `low` OR `high` may be absent (e.g. LDL is
    only "< 100", so low=None, high=100), but at least one must be present.
    A critical threshold is only meaningful on a side that HAS a normal
    bound, and must sit OUTSIDE it.
    """

    # allow_inf_nan=False rejects NaN/Infinity — a NaN bound would slip past
    # the comparisons below (every comparison with NaN is False), silently
    # disabling a bound: an "unknown masquerades as fine" hole (#011).
    low: float | None = Field(
        default=None, allow_inf_nan=False, description="Lower bound, or None."
    )
    high: float | None = Field(
        default=None, allow_inf_nan=False, description="Upper bound, or None."
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

    @model_validator(mode="after")
    def check_bounds(self):
        if self.low is None and self.high is None:
            raise ValueError("a range needs at least one of low / high")
        if self.low is not None and self.high is not None and self.low >= self.high:
            raise ValueError(f"low ({self.low}) must be < high ({self.high})")
        if self.critical_low is not None:
            if self.low is None:
                raise ValueError("critical_low set but there is no normal low")
            if self.critical_low >= self.low:
                raise ValueError(
                    f"critical_low ({self.critical_low}) must be below the "
                    f"normal low ({self.low})"
                )
        if self.critical_high is not None:
            if self.high is None:
                raise ValueError("critical_high set but there is no normal high")
            if self.critical_high <= self.high:
                raise ValueError(
                    f"critical_high ({self.critical_high}) must be above the "
                    f"normal high ({self.high})"
                )
        return self


class ReferenceRangeEntry(MediScanModel):
    """One curated reference-range fact for a single lab test.

    test_name MUST match the canonical output of normalize_test_name so the
    engine's lookup succeeds. The default bounds (low/high/critical_*) are
    the sex-independent range; sex-dependent tests instead provide `male`
    and `female` blocks. An entry must be resolvable for any sex: it needs
    EITHER default bounds OR both a male and a female block.
    """

    test_name: str = Field(
        min_length=1, description="Canonical test name (matches normalization output)."
    )
    unit: str | None = Field(
        default=None, description="Canonical unit for this test, if any."
    )
    # Default (sex-independent) bounds — optional so one-sided ranges work and
    # so a purely sex-specific test can omit them in favour of male/female.
    low: float | None = Field(default=None, allow_inf_nan=False)
    high: float | None = Field(default=None, allow_inf_nan=False)
    critical_low: float | None = Field(default=None, allow_inf_nan=False)
    critical_high: float | None = Field(default=None, allow_inf_nan=False)
    # Optional per-sex overrides for sex-dependent tests (Hemoglobin,
    # Creatinine, Ferritin, ...). Report-printed ranges are already sex-correct
    # (#023), so these only affect the KB FALLBACK.
    male: RangeBounds | None = Field(default=None)
    female: RangeBounds | None = Field(default=None)
    source: str = Field(
        min_length=1,
        description="Citation for these numbers — mandatory (no anonymous facts).",
    )

    @model_validator(mode="after")
    def check_bounds(self):
        has_default = self.low is not None or self.high is not None
        has_both_sexes = self.male is not None and self.female is not None
        if not has_default and not has_both_sexes:
            raise ValueError(
                f"{self.test_name}: provide default low/high, or BOTH a male and "
                f"a female block, so the entry resolves for any sex"
            )
        if has_default:
            # reuse RangeBounds validation for the default bounds (raises on a
            # bad low/high or a critical on the wrong side)
            self.default_bounds()
        return self

    def default_bounds(self) -> "RangeBounds | None":
        """The sex-independent bounds as a RangeBounds, or None if not given."""
        if self.low is None and self.high is None:
            return None
        return RangeBounds(
            low=self.low,
            high=self.high,
            critical_low=self.critical_low,
            critical_high=self.critical_high,
        )


class KnowledgeSnippet(MediScanModel):
    """One self-contained, sourced fact, ready to be embedded and retrieved."""

    text: str = Field(min_length=1, description="The fact, as a short sentence.")
    source: str = Field(min_length=1, description="Citation for this fact.")
    test_name: str = Field(min_length=1, description="Test this fact is about.")


class TestKnowledge(MediScanModel):
    """Curated, sourced explanation content for one lab test."""

    test_name: str = Field(min_length=1, description="Canonical test name.")
    what_it_measures: str = Field(min_length=1)
    low_meaning: str = Field(min_length=1, description="What a low value can indicate.")
    high_meaning: str = Field(
        min_length=1, description="What a high value can indicate."
    )
    dietary_note: str | None = Field(default=None)
    specialist: str | None = Field(default=None)
    source: str = Field(min_length=1, description="Citation - mandatory (#019).")

    def to_snippets(self) -> list[KnowledgeSnippet]:
        """Split this entry into one sourced snippet per idea (chunking)."""

        def snip(text: str) -> KnowledgeSnippet:
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
