"""Reconstruct visual table rows from PyMuPDF word boxes (Sprint 8 fix).

WHY THIS IS ITS OWN MODULE
    `page.get_text()` returns characters in the PDF's internal stream order.
    For a real tabular lab report (e.g. Tata 1mg) that order is COLUMN-major:
    every test name, THEN every value, THEN every unit — so a value lands on
    a different line from its test name and the row-based parser recognises
    nothing. Zero results parse.

    This module rebuilds the visual ROWS from geometry: words sharing a
    vertical position are the same printed row. Kept SEPARATE from
    pymupdf_engine (which imports the heavy `pymupdf` library) so the logic
    is pure stdlib — testable anywhere, no PyMuPDF needed, just like the
    project's other pure functions.
"""

# Two words belong to the same printed row when their vertical centres are
# within this many PDF points. Lab-table rows are ~10-14 pt apart and body
# text is ~11 pt, so ~3 pt comfortably groups one row without merging two.
# A module constant (not config): an internal extraction detail, not a
# clinical knob a reviewer would ever retune.
ROW_Y_TOLERANCE_PT = 3.0


def reconstruct_lines(words: list, *, y_tolerance: float = ROW_Y_TOLERANCE_PT) -> str:
    """Rebuild visual rows from PyMuPDF word boxes. PURE — hence testable.

    Args:
        words: the list PyMuPDF's ``page.get_text("words")`` returns — each
            item an ``(x0, y0, x1, y1, text, block, line, word_no)`` tuple.
            Only the first five fields are used (box + text).
        y_tolerance: max vertical-centre gap (in points) for two words to be
            treated as the same row.

    Returns:
        One string, rows separated by newlines, words within a row ordered
        left-to-right — the horizontal layout the parser expects.
    """
    if not words:
        return ""

    # (centre_y, left_x, text): centre_y clusters rows, left_x orders columns.
    tokens = [((w[1] + w[3]) / 2.0, w[0], w[4]) for w in words]
    tokens.sort(key=lambda t: (t[0], t[1]))  # top-to-bottom, then left-to-right

    rows: list[list[tuple[float, str]]] = []
    current: list[tuple[float, str]] = []
    row_anchor_y: float | None = None
    for centre_y, left_x, text in tokens:
        # Anchor each row on its FIRST word's centre; a later word joins the
        # row while it stays within tolerance of that anchor. A bigger jump
        # starts a new row. (Anchoring on the first word, not a running mean,
        # stops a tall row from slowly drifting into the next one.)
        if row_anchor_y is None or abs(centre_y - row_anchor_y) <= y_tolerance:
            current.append((left_x, text))
            if row_anchor_y is None:
                row_anchor_y = centre_y
        else:
            rows.append(current)
            current = [(left_x, text)]
            row_anchor_y = centre_y
    if current:
        rows.append(current)

    return "\n".join(
        " ".join(text for _, text in sorted(row, key=lambda p: p[0])) for row in rows
    )
