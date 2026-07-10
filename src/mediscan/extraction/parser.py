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

SCOPE (decisions #018, #027)
    A row is recognized only when it has a POSITIVE reference range,
    either:
      - two-sided  ("13.0 - 17.0"), or
      - one-sided  ("< 100", "> 40", "<= 5.7 %")  [added in Sprint 6.5]
    Rows without a range, or with negative reference values, are treated
    as unparsed. One-sided ranges cover lipids, HbA1c, and thyroid-style
    tests where the report prints only an upper or a lower limit.
"""

import re

from pydantic import ValidationError

from mediscan.schemas import LabResult, ParseOutcome, ReferenceRange

# --- Reference-range grammar (shared building blocks) ----------------------
# A number is an unsigned integer or decimal (17 or 13.0). No leading sign:
# negative reference values are out of scope (#018) and stay unparsed.
_NUMBER = r"\d+(?:\.\d+)?"

# One-sided: an operator then a number, with an OPTIONAL trailing "%".
# "(?:\s*%)?" only consumes a space when a "%" actually follows it, so it can
# never swallow the space that separates a trailing flag (e.g. "< 100 H").
_ONE_SIDED_SRC = rf"(?:<=|>=|<|>)\s*{_NUMBER}(?:\s*%)?"

# Two-sided: LOW - HIGH.
_TWO_SIDED_SRC = rf"{_NUMBER}\s*-\s*{_NUMBER}"

# The whole range token, optionally wrapped in parentheses. "(?:\s*\))?" uses
# the same trick as the "%" above — it only eats a space when a ")" follows.
_RANGE_SRC = rf"\(?\s*(?:{_ONE_SIDED_SRC}|{_TWO_SIDED_SRC})(?:\s*\))?"

# Tight patterns used by parse_reference_range() to READ a matched token and
# pull out the actual numbers.
_ONE_SIDED_RE = re.compile(rf"^(?P<op><=|>=|<|>)\s*(?P<num>{_NUMBER})(?:\s*%)?$")
_TWO_SIDED_RE = re.compile(rf"^(?P<low>{_NUMBER})\s*-\s*(?P<high>{_NUMBER})$")

# --- One compiled pattern for a full lab-report row ------------------------
#   NAME   VALUE   UNIT   RANGE   [FLAG]
# Compiled once at module load (not per call) — a safety-critical parser
# earns its speed by being simple and fast.
_LAB_LINE = re.compile(
    r"^\s*"  # start, optional leading spaces
    r"(?P<name>[A-Za-z][A-Za-z ]+?)"  # NAME: starts with a letter, letters+spaces, lazy
    r"\s+"  # gap
    rf"(?P<value>{_NUMBER})"  # VALUE: integer or decimal
    r"\s+"
    r"(?P<unit>\S+)"  # UNIT: one non-space token
    r"\s+"
    rf"(?P<range>{_RANGE_SRC})"  # RANGE: two-sided OR one-sided
    r"(?:\s+(?P<flag>[A-Za-z*]{1,3}))?"  # FLAG: any short trailing marker (h, L, HH, *)
    r"\s*$"  # optional trailing spaces, end
)

# A real lab row is well under this. Lines longer than this are skipped
# before the regex to avoid pathological backtracking (ReDoS hardening).
_MAX_LINE_LENGTH = 300


def _safe_reference_range(low: str | None, high: str | None) -> ReferenceRange | None:
    """Build a ReferenceRange, or None if it fails validation (e.g. low >= high)."""
    try:
        return ReferenceRange(low=low, high=high)
    except ValidationError:
        return None


def parse_reference_range(token: str) -> ReferenceRange | None:
    """Turn a reference-range token into a ReferenceRange, or None if unrecognized.

    Handles two-sided ("13.0 - 17.0") and one-sided ("< 100", ">= 40",
    "< 5.7 %") ranges. Kept as its own small function so the range logic is
    isolated and directly testable — the seed of a future recognizer split
    (Sprint 7), without adding that framework now.

    One-sided meaning:
      "< N" / "<= N"  -> normal is BELOW N, so N is the UPPER limit (high = N).
      "> N" / ">= N"  -> normal is ABOVE N, so N is the LOWER limit (low  = N).
    """
    text = token.strip().strip("()").strip()

    one = _ONE_SIDED_RE.match(text)
    if one is not None:
        number = one.group("num")
        if one.group("op") in ("<", "<="):
            return _safe_reference_range(low=None, high=number)
        return _safe_reference_range(low=number, high=None)

    two = _TWO_SIDED_RE.match(text)
    if two is not None:
        return _safe_reference_range(low=two.group("low"), high=two.group("high"))

    return None


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

        reference_range = parse_reference_range(match.group("range"))
        if reference_range is None:
            # The row matched the row SHAPE but the range token didn't resolve
            # to a valid range (e.g. an inverted two-sided range). Treat as
            # unparsed rather than terminating the whole parser.
            unparsed_lines.append(line)
            continue

        try:
            result = LabResult(
                test_name=match.group("name").strip(),
                value=match.group("value"),
                unit=match.group("unit"),
                reference_range=reference_range,
                flag_in_report=match.group("flag"),
            )
        except ValidationError:
            # The row matched the expected structure but failed schema
            # validation. Treat it as unparsed instead of crashing.
            unparsed_lines.append(line)
            continue

        results.append(result)

    return ParseOutcome(results=results, unparsed_lines=unparsed_lines)
