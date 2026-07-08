"""Deterministic severity engine (decision #006, #020, #021).

Pure functions: given a lab value and its resolved range, decide a
severity band and direction. No AI, no mutation, no side effects.
"""

from mediscan.config import settings
from mediscan.medical.ranges import resolve_reference_range
from mediscan.schemas import (
    AbnormalDirection,
    LabResult,
    RangeResolution,
    Severity,
    SeverityAssessment,
)


def _band(
    value: float, resolution: RangeResolution
) -> tuple[Severity | None, AbnormalDirection | None]:
    """The pure banding decision: (value, range) -> (severity, direction).

    Separated from assembly so the decision logic can be tested on its
    own, with no schema-building around it.
    """
    rng = resolution.reference_range

    # 1. No range at all -> un-assessable. Unknown stays unknown.
    if rng is None:
        return None, None

    # Which side is the value out on? Guard for one-sided ranges where
    # low or high could be None.
    below = rng.low is not None and value < rng.low
    above = rng.high is not None and value > rng.high

    # 2. Inside the range -> NORMAL, no direction.
    if not below and not above:
        return Severity.NORMAL, None

    # 3. Pick the side's numbers.
    direction = AbnormalDirection.LOW if below else AbnormalDirection.HIGH
    boundary = rng.low if below else rng.high
    critical = resolution.critical_low if below else resolution.critical_high

    # 4. CRITICAL — only when a sourced threshold exists and we're past it.
    if critical is not None and (
        (below and value <= critical) or (above and value >= critical)
    ):
        return Severity.CRITICAL, direction

    # 5. Option B: a critical threshold exists -> band by fraction of the
    #    way from the boundary toward critical. The KB schema guarantees
    #    critical sits outside the range, so these denominators are > 0.
    if critical is not None:
        if below:
            frac = (boundary - value) / (boundary - critical)
        else:
            frac = (value - boundary) / (critical - boundary)
        if frac < settings.severity_frac_mild:
            return Severity.MILD, direction
        if frac < settings.severity_frac_moderate:
            return Severity.MODERATE, direction
        return Severity.HIGH, direction

    # 6. Option A: no critical threshold -> percentage from the boundary,
    #    CAPPED AT HIGH. We never invent a CRITICAL line (#020).
    # Float-safe zero check: floats carry tiny representation errors, so a
    # boundary that "should" be 0 might be stored as 2e-17. Exact `== 0`
    # would miss it and we'd divide by (almost) zero below, producing a
    # nonsense deviation. Anything this close to zero is zero for our purposes.
    if abs(boundary) < 1e-9:
        # can't take a percentage of zero; be conservative
        return Severity.HIGH, direction
    dev = abs(value - boundary) / abs(boundary)
    if dev < settings.severity_pct_mild:
        return Severity.MILD, direction
    if dev < settings.severity_pct_moderate:
        return Severity.MODERATE, direction
    return Severity.HIGH, direction


def assess_lab_result(result: LabResult) -> SeverityAssessment:
    """Judge one lab result. Pure: returns a NEW SeverityAssessment,
    never mutates the input (decision #021)."""
    resolution = resolve_reference_range(result)
    severity, direction = _band(result.value, resolution)
    return SeverityAssessment(
        test_name=result.test_name,
        value=result.value,
        severity=severity,
        abnormal_direction=direction,
        range_resolution=resolution,
    )


def assess_results(results: list[LabResult]) -> list[SeverityAssessment]:
    """Judge many results, in order (positionally aligned with input)."""
    return [assess_lab_result(r) for r in results]
