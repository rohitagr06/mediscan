"""Tests for PyMuPDF row reconstruction (Sprint 8 real-PDF fix).

The real Tata 1mg PDF text-extracts COLUMN-major: names, then values, then
units — so the row parser found zero results. `reconstruct_lines` rebuilds
the visual rows from word bounding boxes. It's a pure function over the word
tuples PyMuPDF returns, so we can test it WITHOUT PyMuPDF by feeding it
synthetic word boxes that mimic a real page.
"""

from mediscan.ocr._rows import reconstruct_lines


def _word(x0: float, y0: float, text: str, *, height: float = 10.0) -> tuple:
    """Build one PyMuPDF-style word tuple: (x0, y0, x1, y1, text, b, l, n)."""
    return (x0, y0, x0 + 20.0, y0 + height, text, 0, 0, 0)


def test_empty_words_gives_empty_string():
    assert reconstruct_lines([]) == ""


def test_words_on_same_row_join_left_to_right():
    # Same y, different x -> one row, ordered by x even if given out of order.
    words = [
        _word(300, 100, "13.0-17.0"),
        _word(50, 100, "Hemoglobin"),
        _word(200, 100, "g/dL"),
        _word(150, 100, "15.3"),
    ]
    assert reconstruct_lines(words) == "Hemoglobin 15.3 g/dL 13.0-17.0"


def test_column_major_stream_is_regrouped_into_rows():
    # Simulate the Tata failure mode: the PDF emits every NAME first (one y
    # each), then every VALUE, then every RANGE — column-major. Reconstruction
    # must stitch them back into per-row lines by vertical position.
    words = [
        # names column (x~50)
        _word(50, 100, "Hemoglobin"),
        _word(50, 120, "Creatinine"),
        # values column (x~150) — emitted later in the stream
        _word(150, 100, "15.3"),
        _word(150, 120, "1.33"),
        # range column (x~300)
        _word(300, 100, "13.0-17.0"),
        _word(300, 120, "0.7-1.3"),
    ]
    out = reconstruct_lines(words)
    lines = out.split("\n")
    assert lines[0] == "Hemoglobin 15.3 13.0-17.0"
    assert lines[1] == "Creatinine 1.33 0.7-1.3"


def test_small_vertical_jitter_stays_one_row():
    # Sub-pixel/point differences in y (sub-scripts, font mix) must NOT split
    # a row: 100.0 vs 101.5 are within the ~3pt tolerance.
    words = [
        _word(50, 100.0, "Platelet"),
        _word(150, 101.5, "152"),
        _word(300, 100.4, "150-410"),
    ]
    assert reconstruct_lines(words) == "Platelet 152 150-410"


def test_rows_far_apart_stay_separate():
    words = [
        _word(50, 100, "RowOne"),
        _word(50, 140, "RowTwo"),  # 40pt below -> clearly a new row
    ]
    assert reconstruct_lines(words).split("\n") == ["RowOne", "RowTwo"]
