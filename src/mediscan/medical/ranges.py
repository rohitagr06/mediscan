"""Reference-range resolution (report-first range + merged KB criticals, #023).

Sex-aware (Sprint 6.5): when the report omits its own range for a sex-dependent
test, the KB fallback uses the block for the patient's sex. When the sex is
UNKNOWN, it uses the UNION of both sexes' ranges — the widest normal band, so
we don't raise a false alarm (decision #029). Report-printed ranges are already
sex-correct, so sex only ever affects the KB fallback.
"""

from mediscan.extraction.normalization import normalize_test_name
from mediscan.medical.reference_data import load_reference_ranges
from mediscan.schemas import LabResult, ReferenceRange
from mediscan.schemas.knowledge import RangeBounds, ReferenceRangeEntry
from mediscan.schemas.medical import CriticalThresholds, RangeResolution, RangeSource
from mediscan.schemas.patient import Sex


def _union(a: RangeBounds, b: RangeBounds) -> RangeBounds:
    """Widest normal band across two sex blocks (#029): min low, max high.

    A bound is kept only when BOTH sides provide it — if one sex block has no
    critical_low, the union has none either (we don't invent a threshold).
    """

    def lo(x: float | None, y: float | None) -> float | None:
        return None if x is None or y is None else min(x, y)

    def hi(x: float | None, y: float | None) -> float | None:
        return None if x is None or y is None else max(x, y)

    return RangeBounds(
        low=lo(a.low, b.low),
        high=hi(a.high, b.high),
        critical_low=lo(a.critical_low, b.critical_low),
        critical_high=hi(a.critical_high, b.critical_high),
    )


def _bounds_for_sex(entry: ReferenceRangeEntry, sex: Sex) -> RangeBounds | None:
    """Pick the KB bounds that apply to this patient's sex.

    A matching sex block wins; UNKNOWN with both blocks present unions them
    (#029); otherwise the sex-independent default bounds are used.
    """
    if sex is Sex.MALE and entry.male is not None:
        return entry.male
    if sex is Sex.FEMALE and entry.female is not None:
        return entry.female
    if sex is Sex.UNKNOWN and entry.male is not None and entry.female is not None:
        return _union(entry.male, entry.female)
    return entry.default_bounds()


def _merge_kb_criticals(
    report_range: ReferenceRange, bounds: RangeBounds | None
) -> CriticalThresholds:
    """KB criticals that sit STRICTLY OUTSIDE the report's normal range (#023).

    The report owns the normal range. A KB critical is only trustworthy here
    if it lies beyond the matching report bound; a threshold inside the report
    range would contradict it, so we drop it (report wins) and that side falls
    back to percentage banding.
    """
    if bounds is None:
        return CriticalThresholds()

    low = bounds.critical_low
    if low is not None and (report_range.low is None or low >= report_range.low):
        low = None  # inside/at the report range -> ignore

    high = bounds.critical_high
    if high is not None and (report_range.high is None or high <= report_range.high):
        high = None

    return CriticalThresholds(low=low, high=high)


def resolve_reference_range(
    result: LabResult, sex: Sex = Sex.UNKNOWN
) -> RangeResolution:
    """Report-first normal range; merge KB criticals; else KB fallback; else unknown.

    Args:
        result: The parsed lab result (may carry the report's printed range).
        sex: The patient's sex, used to pick sex-specific KB bounds on the
            fallback path. Defaults to UNKNOWN so existing callers are
            unaffected until the pipeline threads the real sex through.
    """
    entry = load_reference_ranges().get(normalize_test_name(result.test_name))
    bounds = _bounds_for_sex(entry, sex) if entry is not None else None

    if result.reference_range is not None:
        # Report owns the normal range; augment with safe KB criticals.
        return RangeResolution(
            reference_range=result.reference_range,
            reference_range_source=RangeSource.REPORT,
            critical_thresholds=_merge_kb_criticals(result.reference_range, bounds),
        )

    if bounds is None:
        return RangeResolution(reference_range_source=RangeSource.UNKNOWN)

    # KB fallback: range AND criticals from the KB (already validated consistent).
    return RangeResolution(
        reference_range=ReferenceRange(low=bounds.low, high=bounds.high),
        reference_range_source=RangeSource.KNOWLEDGE_BASE,
        critical_thresholds=CriticalThresholds(
            low=bounds.critical_low, high=bounds.critical_high
        ),
    )
