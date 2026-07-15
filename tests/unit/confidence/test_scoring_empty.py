"""Confidence-on-empty tests (Sprint 8 fix).

A report that parsed ZERO lab rows must not present as confident, however
cleanly each (empty) stage scored. These lock the `parsed_count` collapse.
"""

from mediscan.confidence.scoring import score_confidence


def test_zero_parsed_collapses_overall_to_zero():
    # All stages perfect, but nothing was parsed -> overall must be 0.
    breakdown = score_confidence(
        ocr=1.0,
        extraction=1.0,
        validation=1.0,
        grounding=1.0,
        parsed_count=0,
    )
    assert breakdown.overall == 0.0
    # Sub-scores are still reported honestly (each stage's own signal).
    assert breakdown.ocr == 1.0
    assert breakdown.extraction == 1.0


def test_some_parsed_scores_normally():
    breakdown = score_confidence(
        ocr=1.0,
        extraction=1.0,
        validation=1.0,
        grounding=1.0,
        parsed_count=5,
    )
    assert breakdown.overall == 1.0


def test_parsed_count_omitted_is_backward_compatible():
    # No parsed_count -> behaves exactly as before (existing callers/tests).
    breakdown = score_confidence(ocr=1.0, extraction=1.0, validation=1.0, grounding=1.0)
    assert breakdown.overall == 1.0
