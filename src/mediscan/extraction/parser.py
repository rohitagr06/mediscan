"""Deterministic laboratory report parser.

WHY THIS FILE EXISTS
    The parser converts raw document text into structured laboratory
    observations without making any medical judgments. Its only
    responsibility is to recognize laboratory report rows and extract
    their raw fields.

    Parsing is intentionally tolerant: every line either becomes a
    LabResult or is preserved in ParseOutcome.unparsed_lines. Invalid,
    noisy, or partially recognized OCR output never crashes the parser
    and is never silently discarded.

SCOPE (decision #018)
    A row is recognized only when it has a two-sided POSITIVE reference
    range (e.g. "13.0 - 17.0"). Rows without a range, or with negative
    reference values, are treated as unparsed. This fits the RC1 CBC-panel
    scope (decision #005) and is revisited when scope expands.
"""

import re

from pydantic import ValidationError

from mediscan.schemas import LabResult, ParseOutcome, ReferenceRange

# One compiled pattern for a full lab-report row:
#   NAME   VALUE   UNIT   (LOW - HIGH)   [FLAG]
# Compiled once at module load (not per call) — a safety-critical parser
# earns its speed by being simple and fast.
_LAB_LINE = re.compile(
    r"^\s*"  # start, optional leading spaces
    r"(?P<name>[A-Za-z][A-Za-z ]+?)"  # NAME: starts with a letter, letters+spaces, lazy
    r"\s+"  # gap
    r"(?P<value>\d+(?:\.\d+)?)"  # VALUE: integer or decimal
    r"\s+"
    r"(?P<unit>\S+)"  # UNIT: one non-space token
    r"\s+\(?\s*"  # gap, optional "(", optional spaces
    r"(?P<low>\d+(?:\.\d+)?)"  # RANGE LOW
    r"\s*-\s*"  # dash, spaces allowed around it
    r"(?P<high>\d+(?:\.\d+)?)"  # RANGE HIGH
    r"\s*\)?"  # optional spaces, optional ")"
    r"(?:\s+(?P<flag>[A-Za-z*]{1,3}))?"  # FLAG: any short trailing marker (h, L, HH, *)
    r"\s*$"  # optional trailing spaces, end
)

# A real lab row is well under this. Lines longer than this are skipped
# before the regex to avoid pathological backtracking (ReDoS hardening).
_MAX_LINE_LENGTH = 300


def parse_lab_text(text: str) -> ParseOutcome:
    """Parse document text into lab results, tolerantly.

    Every line either matches the lab-row shape (-> a LabResult with
    severity STILL None, because parsing never judges) or is recorded
    in unparsed_lines. Never raises on bad input — a line that doesn't
    match is data, not an error.
    """
    results: list[LabResult] = []
    unparsed_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        # A real lab row is short. Skipping absurdly long lines before the
        # regex is a cheap guard against pathological backtracking on a
        # hostile all-letters/spaces line (ReDoS hardening); such a line is
        # never a lab row anyway, so it is recorded as unparsed.
        if len(line) > _MAX_LINE_LENGTH:
            unparsed_lines.append(line)
            continue

        match = _LAB_LINE.match(line)

        if match is None:
            unparsed_lines.append(line)
            continue

        try:
            result = LabResult(
                test_name=match.group("name").strip(),
                value=match.group("value"),
                unit=match.group("unit"),
                reference_range=ReferenceRange(
                    low=match.group("low"),
                    high=match.group("high"),
                ),
                flag_in_report=match.group("flag"),
            )
        except ValidationError:
            # The row matched the expected structure but failed schema
            # validation (e.g. an invalid reference range). Treat it as
            # unparsed instead of terminating the whole parser.
            unparsed_lines.append(line)
            continue

        results.append(result)

    return ParseOutcome(results=results, unparsed_lines=unparsed_lines)
