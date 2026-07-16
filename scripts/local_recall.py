"""Local real-report recall helper (Sprint 8.9c) — COUNTS ONLY, never PHI.

    uv run python scripts/local_recall.py samples/*.pdf

Runs the deterministic pipeline (no AI, no network) over each PDF and prints
ONLY integer counts per file:

    parsed         — lab rows the parser recovered (assessed + acknowledged)
    assessed       — of those, graded by the medical engine
    acknowledged   — of those, shown-but-not-graded (out of scope / sensitive)
    unparsed_lines — lines NOT recognised as results (headers, footers, noise)

WHY THIS IS SAFE (#010)
    Real lab reports are PHI. This tool prints NO test names, NO values, NO
    line text — only counts and the filename you passed, so its output is safe
    to paste back for the record. To compute recall you also need the EXPECTED
    number of tests, which you read off the PDF yourself:

        recall = parsed / expected

    Keep your PDFs in the gitignored samples/ folder; never commit them.
"""

from __future__ import annotations

import sys
from pathlib import Path

from mediscan.orchestration.pipeline import analyze_document


def _counts(path: Path) -> tuple[int, int, int, int]:
    """Return (parsed, assessed, acknowledged, unparsed_lines) — counts only."""
    report = analyze_document(path, providers=[], retrieve_fn=lambda _q: [])
    cov = report.coverage
    return (
        len(report.lab_results),
        len(cov.assessed),
        len(cov.acknowledged),
        len(cov.unparsed),
    )


def _row_for(path: Path) -> str:
    """One counts-only output row for a single file (never raises)."""
    if not path.exists():
        return f"{path.name:<28} MISSING (file not found)"
    try:
        parsed, assessed, ack, unparsed = _counts(path)
    except Exception as err:  # a bad/corrupt PDF must not kill the batch
        return f"{path.name:<28} ERROR: {type(err).__name__}"
    return f"{path.name:<28} {parsed:>7} {assessed:>9} {ack:>5} {unparsed:>9}"


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    header = f"{'file':<28} {'parsed':>7} {'assessed':>9} {'ack':>5} {'unparsed':>9}"
    print(header)
    print("-" * len(header))
    for arg in argv:
        print(_row_for(Path(arg)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
