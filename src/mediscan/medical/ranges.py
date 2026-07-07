"""Reference-range resolution.

WHY THIS FILE EXISTS
    Laboratory results may contain their own reference ranges. When they
    do not, MediScan falls back to curated generalized adult reference
    ranges from the knowledge base. This module performs that
    deterministic resolution and records where the range came from for
    explainability.
"""

from mediscan.extraction.normalization import normalize_test_name
from mediscan.medical.reference_data import load_reference_ranges
from mediscan.schemas import (
    LabResult,
    RangeResolution,
    RangeSource,
    ReferenceRange,
)


def resolve_reference_range(result: LabResult) -> RangeResolution:
    """Decide which reference range applies to a lab result.

    Report-first, KB-fallback, else un-assessable. Also surfaces the
    KB critical thresholds (which reports never carry) for the severity
    engine, and records the source for explainability.
    """

    if result.reference_range is not None:
        return RangeResolution(
            reference_range=result.reference_range,
            source=RangeSource.REPORT,
        )

    canonical = normalize_test_name(result.test_name)

    entry = load_reference_ranges().get(canonical)

    if entry is None:
        return RangeResolution(
            source=RangeSource.UNKNOWN,
        )

    return RangeResolution(
        reference_range=ReferenceRange(
            low=entry.low,
            high=entry.high,
        ),
        critical_low=entry.critical_low,
        critical_high=entry.critical_high,
        source=RangeSource.KNOWLEDGE_BASE,
    )
