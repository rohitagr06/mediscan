"""Local real-report recall helper (Sprint 8.9c) — COUNTS ONLY, never PHI.

    uv run python scripts/local_recall.py samples/*.pdf

Runs the deterministic pipeline (no AI, no network) over each PDF and prints
ONLY integer counts per file:

    parsed     — lab rows the parser recovered (assessed + acknowledged)
    assessed   — of those, graded by the medical engine
    ack        — of those, shown-but-not-graded (out of scope / sensitive)
    miss_est   — unparsed lines that STILL look like a lab result (a number
                 next to a known unit): an ESTIMATE of tests we missed
    recall_est — parsed / (parsed + miss_est), as a percentage

WHY THIS IS SAFE (#010)
    Real lab reports are PHI. This tool prints NO test names, NO values, NO
    line text — only counts and the filename you passed, so its output is safe
    to paste back for the record.

WHY miss_est IS AN ESTIMATE (read this before trusting recall_est)
    `miss_est` counts unparsed lines that carry a number + a recognised unit.
    It OVER-counts when a report prints unit-bearing noise (a reference-range
    row, a pregnancy table) and UNDER-counts a missed test whose unit we don't
    list or whose value/units reconstructed onto separate lines (the multi-line
    gap, #033). So treat `recall_est` as a rough guide, not gospel — good
    enough to see which reports need parser work, not a certified metric.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from mediscan.orchestration.pipeline import analyze_document

# A digit immediately followed (allowing one space) by a recognised lab unit.
# Anchoring on the digit keeps boilerplate like "Page 1 of 15" or a bare "%"
# in prose from matching — a lab result is a NUMBER carrying a UNIT.
_RESULT_UNIT = re.compile(
    r"\d\s?"
    r"(?:mg/d[lL]|g/d[lL]|[µu]g/d[lL]|ng/m[lL]|ng/d[lL]|pg/m[lL]|"
    r"[µu]?IU/m[lL]|IU/[lL]|U/[lL]|mmol/[lL]|mEq/[lL]|mm/hr|"
    r"10\^[0-9]+/[^\s]+|/[µu][lL]|cu\.?mm|fL|pg|%)",
    re.IGNORECASE,
)


def _miss_estimate(unparsed_lines: list[str]) -> int:
    """Count unparsed lines that still look like a lab result (number + unit).

    Pure counting: the line text is inspected but NEVER printed or returned."""
    return sum(1 for line in unparsed_lines if _RESULT_UNIT.search(line))


def _counts(path: Path) -> tuple[int, int, int, int]:
    """Return (parsed, assessed, ack, miss_est) — counts only, no text."""
    report = analyze_document(path, providers=[], retrieve_fn=lambda _q: [])
    cov = report.coverage
    return (
        len(report.lab_results),
        len(cov.assessed),
        len(cov.acknowledged),
        _miss_estimate(list(cov.unparsed)),
    )


def _row_for(path: Path) -> str:
    """One counts-only output row for a single file (never raises)."""
    if not path.exists():
        return f"{path.name:<28} MISSING (file not found)"
    try:
        parsed, assessed, ack, miss = _counts(path)
    except Exception as err:  # a bad/corrupt PDF must not kill the batch
        return f"{path.name:<28} ERROR: {type(err).__name__}"
    denom = parsed + miss
    recall = f"{100 * parsed / denom:.0f}%" if denom else "—"
    return (
        f"{path.name:<28} {parsed:>7} {assessed:>9} {ack:>5} " f"{miss:>9} {recall:>11}"
    )


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    header = (
        f"{'file':<28} {'parsed':>7} {'assessed':>9} {'ack':>5} "
        f"{'miss_est':>9} {'recall_est':>11}"
    )
    print(header)
    print("-" * len(header))
    for arg in argv:
        print(_row_for(Path(arg)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
