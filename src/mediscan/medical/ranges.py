"""Reference-range resolution (report-first range + merged KB criticals, #023)."""

from mediscan.extraction.normalization import normalize_test_name
from mediscan.medical.reference_data import load_reference_ranges
from mediscan.schemas import LabResult, ReferenceRange
from mediscan.schemas.knowledge import ReferenceRangeEntry
from mediscan.schemas.medical import CriticalThresholds, RangeResolution, RangeSource


def _merge_kb_criticals(
    report_range: ReferenceRange, entry: ReferenceRangeEntry | None
) -> CriticalThresholds:
    """KB criticals that sit STRICTLY OUTSIDE the report's normal range (#023).

    The report owns the normal range. A KB critical is only trustworthy here
    if it lies beyond the matching report bound; a threshold inside the report
    range would contradict it, so we drop it (report wins) and that side falls
    back to percentage banding.
    """
    if entry is None:
        return CriticalThresholds()

    low = entry.critical_low
    if low is not None and (report_range.low is None or low >= report_range.low):
        low = None  # inside/at the report range -> ignore

    high = entry.critical_high
    if high is not None and (report_range.high is None or high <= report_range.high):
        high = None

    return CriticalThresholds(low=low, high=high)


def resolve_reference_range(result: LabResult) -> RangeResolution:
    """Report-first normal range; merge KB criticals; else KB fallback; else unknown."""
    entry = load_reference_ranges().get(normalize_test_name(result.test_name))

    if result.reference_range is not None:
        # Report owns the normal range; augment with safe KB criticals.
        return RangeResolution(
            reference_range=result.reference_range,
            reference_range_source=RangeSource.REPORT,
            critical_thresholds=_merge_kb_criticals(result.reference_range, entry),
        )

    if entry is None:
        return RangeResolution(reference_range_source=RangeSource.UNKNOWN)

    # KB fallback: range AND criticals from the KB (already validated consistent).
    return RangeResolution(
        reference_range=ReferenceRange(low=entry.low, high=entry.high),
        reference_range_source=RangeSource.KNOWLEDGE_BASE,
        critical_thresholds=CriticalThresholds(
            low=entry.critical_low, high=entry.critical_high
        ),
    )
