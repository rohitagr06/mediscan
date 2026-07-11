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

SHAPE OF THE CODE (Sprint 7.8 refactor)
    One anchored regex (`_LAB_LINE`) TOKENIZES a line into raw fields; small,
    independently-testable RECOGNIZERS then interpret each field:
      - parse_reference_range  — the range token -> ReferenceRange
      - _recognize_name        — the name cell   -> a clean name (or reject)
      - _recognize_flag        — pre/post flag    -> H/L/HH/LL/* (or None)
      - _recognize_number      — strip thousands commas
    `_recognize_row` composes them into a LabResult (or None), and
    parse_lab_text is then just a tolerant loop. Same behaviour as before the
    split — the regex and every rule are unchanged; only the one big function
    was decomposed so each recognizer can be tested in isolation (#033).

SCOPE (decisions #018, #027)
    A row is recognized only when it has a POSITIVE reference range,
    either:
      - two-sided  ("13.0 - 17.0"), or
      - one-sided  ("< 100", "> 40", "<= 5.7 %")  [added in Sprint 6.5]
    Rows without a range, or with negative reference values, are treated
    as unparsed. One-sided ranges cover lipids, HbA1c, and thyroid-style
    tests where the report prints only an upper or a lower limit.

    Real lab reports (e.g. Tata 1mg) print a trailing METHOD column after
    the range ("... 13.0-17.0 Cyanide Free SLS") and parenthesised names
    ("Glycosylated Hemoglobin (HbA1c)"). The parser tolerates both: any text
    after the range is captured as a trailing "tail" and IGNORED — except
    when the tail is exactly a short flag token (L / H / HH / *), which is
    kept as flag_in_report. The reference-range shape stays the anchor that
    tells a real lab row apart from a prose/comment line.
"""

import re

from pydantic import ValidationError

from mediscan.schemas import LabResult, ParseOutcome, ReferenceRange

# --- Reference-range grammar (shared building blocks) ----------------------
# Some reports use typographic dashes (en / em / minus) in ranges
# ("0.3 – 1.2", "5.7–8.2"). Normalise them to a plain hyphen so the range
# grammar only ever has to reason about one "-" character.
_DASH_NORMALIZE = str.maketrans({"–": "-", "—": "-", "−": "-"})

# A number is an unsigned integer or decimal (17 or 13.0), optionally with
# thousands separators ("5,100", "10,800"). No leading sign: negative
# reference values are out of scope (#018) and stay unparsed. The commas are
# stripped before the number is turned into a float.
_NUMBER = r"\d+(?:,\d{3})*(?:\.\d+)?"

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

# A trailing "flag" is a high/low marker (H, L, HH, LL, *) that some reports
# print after the range. We match ONLY these — not any short token — so a
# short method abbreviation (e.g. "GPO", "CLIA") is treated as an ignorable
# method column, never mistaken for a flag.
_FLAG_RE = re.compile(r"^(?:[HL]{1,2}|\*)$", re.IGNORECASE)

# --- One compiled pattern for a full lab-report row ------------------------
#   NAME   VALUE   UNIT   RANGE   [FLAG]
# Compiled once at module load (not per call) — a safety-critical parser
# earns its speed by being simple and fast.
_LAB_LINE = re.compile(
    r"^\s*"  # start, optional leading spaces
    # NAME: a letter first, then letters/digits/spaces/hyphens, matched LAZILY.
    # Digits + hyphens let real test names through (HbA1c, Free T3, Non-HDL).
    # This stays unambiguous because VALUE must be preceded by whitespace: a
    # name has no internal spaces before its number, so "HbA1c 5.4" splits at
    # the space, never inside "HbA1c". Lazy (+?) stops at the first split where
    # a full "value unit range" follows. Parentheses and commas let real names
    # through ("Glycosylated Hemoglobin (HbA1c)", "HEMATOCRIT VALUE, HCT").
    r"(?P<name>[A-Za-z][A-Za-z0-9 (),-]+?)"
    r"\s+"  # gap
    # Some labs print the H/L flag BEFORE the value ("LYMPHOCYTE  L  18"),
    # not after the range. Capture it optionally here so it is not absorbed
    # into the name; a normal row (value follows immediately) just skips it.
    r"(?:(?P<preflag>[HL]{1,2}|\*)\s+)?"
    rf"(?P<value>{_NUMBER})"  # VALUE: integer/decimal, thousands commas allowed
    r"\s+"
    r"(?P<unit>\S+)"  # UNIT: one non-space token
    r"\s+"
    # Optional interpretive descriptor that some reports print inside the
    # reference-interval cell BEFORE the number ("Desirable: <100",
    # "Normal:", "Low (desirable): < 200"). It must end in a colon — a strong
    # anchor that keeps ordinary prose from being mistaken for a lab row.
    r"(?:(?P<desc>[A-Za-z()/ ]+?:)\s*)?"
    rf"(?P<range>{_RANGE_SRC})"  # RANGE: two-sided OR one-sided
    # A comma can glue to the range ("<150, GPO"), so allow a comma/semicolon
    # OR space as the separator before the trailing text, and permit trailing
    # punctuation at the very end.
    r"(?:[\s,;]+(?P<tail>\S.*?))?"  # TAIL: method column or flag, classified below
    r"[\s,;.]*$"
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

    The RANGE recognizer. Handles two-sided ("13.0 - 17.0") and one-sided
    ("< 100", ">= 40", "< 5.7 %") ranges.

    One-sided meaning:
      "< N" / "<= N"  -> normal is BELOW N, so N is the UPPER limit (high = N).
      "> N" / ">= N"  -> normal is ABOVE N, so N is the LOWER limit (low  = N).
    """
    text = token.strip().strip("()").strip()

    one = _ONE_SIDED_RE.match(text)
    if one is not None:
        # strip thousands commas ("10,800" -> "10800") before float coercion
        number = one.group("num").replace(",", "")
        if one.group("op") in ("<", "<="):
            return _safe_reference_range(low=None, high=number)
        return _safe_reference_range(low=number, high=None)

    two = _TWO_SIDED_RE.match(text)
    if two is not None:
        return _safe_reference_range(
            low=two.group("low").replace(",", ""),
            high=two.group("high").replace(",", ""),
        )

    return None


# --- field recognizers (small + independently testable) --------------------


def _recognize_number(raw: str) -> str:
    """Strip thousands separators so a number coerces cleanly ("10,800"->"10800")."""
    return raw.replace(",", "")


def _recognize_name(raw_name: str) -> str | None:
    """The NAME recognizer: the clean test name, or None if it isn't one.

    Column-alignment padding in the source PDF can glue a stray token to the
    name across a big whitespace gap ("T3, Total          R"). A real name uses
    single spaces between words, so we keep only the part before the first
    multi-space gap. A lone leftover character (e.g. a stray "R" from a wrapped
    header) is never a real test name and is rejected.
    """
    name = re.split(r"\s{2,}", raw_name)[0].strip()
    return name if len(name) >= 2 else None


def _recognize_flag(preflag: str | None, tail: str | None) -> str | None:
    """The FLAG recognizer: a high/low marker, or None.

    A flag may sit BEFORE the value (preflag) or AFTER the range (tail). A
    trailing token is a flag ONLY when it is exactly H/L/HH/LL/*; anything
    longer is a Method column ("Cyanide Free SLS") and is ignored — so we never
    invent a flag from a method name. The pre-value flag takes precedence.
    """
    tail_flag = tail.strip() if tail and _FLAG_RE.match(tail.strip()) else None
    return preflag or tail_flag


def _recognize_row(line: str) -> LabResult | None:
    """Compose the recognizers over one normalized line -> a LabResult, or None.

    Returns None whenever the line isn't a well-formed lab row (too long, no
    match, a name/range that doesn't resolve, or a schema failure). The caller
    records those in unparsed_lines — nothing is ever silently dropped.
    """
    # A real lab row is short. Skipping absurdly long lines before the regex is
    # a cheap guard against pathological backtracking on a hostile
    # all-letters/spaces line (ReDoS hardening); such a line is never a lab row.
    if len(line) > _MAX_LINE_LENGTH:
        return None

    match = _LAB_LINE.match(line)
    if match is None:
        return None

    name = _recognize_name(match.group("name"))
    if name is None:
        return None

    reference_range = parse_reference_range(match.group("range"))
    if reference_range is None:
        # matched the row SHAPE but the range didn't resolve (e.g. inverted).
        return None

    flag = _recognize_flag(match.group("preflag"), match.group("tail"))

    try:
        return LabResult(
            test_name=name,
            value=_recognize_number(match.group("value")),
            unit=match.group("unit"),
            reference_range=reference_range,
            flag_in_report=flag,
        )
    except ValidationError:
        # matched the structure but failed schema validation -> unparsed.
        return None


def parse_lab_text(text: str) -> ParseOutcome:
    """Parse document text into lab results, tolerantly.

    Every non-blank line either becomes a LabResult (severity STILL None —
    parsing never judges) or is recorded in unparsed_lines. Never raises on
    bad input: a line that doesn't match is data, not an error.
    """
    results: list[LabResult] = []
    unparsed_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip().translate(_DASH_NORMALIZE)
        if not line:
            continue

        result = _recognize_row(line)
        if result is None:
            unparsed_lines.append(line)
        else:
            results.append(result)

    return ParseOutcome(results=results, unparsed_lines=unparsed_lines)
