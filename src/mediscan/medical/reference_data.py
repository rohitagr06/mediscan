"""Loader for curated reference-range knowledge.

Reads every JSON file under knowledge_base/reference_ranges/, validates
each entry against ReferenceRangeEntry, and returns them keyed by
canonical test name. Validation happens HERE, at load time: a bad KB
file fails on startup, not mid-analysis.
"""

import json
from functools import cache
from pathlib import Path

from mediscan.schemas.knowledge import ReferenceRangeEntry

_KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "reference_ranges"


@cache
def load_reference_ranges() -> dict[str, ReferenceRangeEntry]:
    """Load and validate all reference-range entries, keyed by test_name.

    Cached: the KB is read and validated once per process. Raises on a
    malformed entry or a duplicate test_name across files.
    """
    entries: dict[str, ReferenceRangeEntry] = {}
    for path in sorted(_KB_DIR.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        for item in raw:
            entry = ReferenceRangeEntry(**item)  # validates here
            if entry.test_name in entries:
                raise ValueError(
                    f"duplicate reference-range entry for '{entry.test_name}' "
                    f"(in {path.name})"
                )
            entries[entry.test_name] = entry
    return entries
