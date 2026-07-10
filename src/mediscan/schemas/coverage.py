"""Coverage: which tests MediScan assessed, acknowledged, or couldn't read.

WHY THIS FILE EXISTS
    A real report contains tests outside RC1's assessable scope. MediScan
    must never silently drop them (#011) nor grade the unsafe ones (#006).
    So every parsed test lands in one of two buckets — ASSESSED (a full
    deterministic verdict) or ACKNOWLEDGED (read and shown, not graded) —
    and unreadable lines are surfaced separately. CoverageResult is that
    complete, honest accounting.

    Whether a test is assessable is PRODUCT POLICY, kept separate from the
    medical KB (decision #030): the KB holds facts; the policy holds
    behaviour. AssessmentPolicy is that per-test behaviour record.
"""

from enum import StrEnum

from pydantic import Field

from mediscan.schemas.base import MediScanModel
from mediscan.schemas.labs import ReferenceRange
from mediscan.schemas.medical import SeverityAssessment


class AssessmentTier(StrEnum):
    """How MediScan treats a test (the docs/14 tiers)."""

    ASSESSED = "A"  # numeric, safe, in scope -> full deterministic verdict
    DEFERRED = "B"  # numeric but needs care -> acknowledged, not graded (RC2)
    EXCLUDED = "C"  # sensitive -> acknowledged, refer to a doctor, no verdict


class AcknowledgeClass(StrEnum):
    """How to PRESENT a test that was read but not assessed."""

    NUMERIC = "numeric"  # show the report's own range, "not graded by MediScan"
    SENSITIVE = "sensitive"  # "present, needs a doctor"; NO range, NO verdict


class AssessmentPolicy(MediScanModel):
    """Per-test product behaviour: which tier, and how to acknowledge it.

    Kept SEPARATE from the medical KB (#030) — the KB says what a value
    means; this says whether MediScan is allowed to grade it.
    """

    test_name: str = Field(min_length=1, description="Canonical test name.")
    tier: AssessmentTier = Field(
        description="A (assessed) / B (deferred) / C (excluded)."
    )
    classification: AcknowledgeClass = Field(
        default=AcknowledgeClass.NUMERIC,
        description="How to present it when NOT assessed (numeric vs sensitive).",
    )

    @property
    def assessable(self) -> bool:
        """True only for Tier A — the deterministic engine may grade it."""
        return self.tier is AssessmentTier.ASSESSED


class AcknowledgedTest(MediScanModel):
    """A test MediScan read but did NOT grade (it still gets surfaced)."""

    test_name: str = Field(min_length=1)
    value: float = Field(allow_inf_nan=False)
    unit: str | None = Field(default=None)
    reference_range: ReferenceRange | None = Field(
        default=None,
        description="The report's own range — kept only for NUMERIC tests.",
    )
    classification: AcknowledgeClass = Field(
        description="Numeric (show range) vs sensitive (name only, see a doctor)."
    )


class CoverageResult(MediScanModel):
    """The complete accounting of one report's tests — nothing dropped.

    Only `assessed` findings feed the urgency roll-up; `acknowledged` tests
    never influence the verdict, and `unparsed` lines are surfaced so a line
    MediScan couldn't read is never mistaken for a clean result.
    """

    assessed: list[SeverityAssessment] = Field(default_factory=list)
    acknowledged: list[AcknowledgedTest] = Field(default_factory=list)
    unparsed: list[str] = Field(default_factory=list)
