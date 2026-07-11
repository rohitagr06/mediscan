"""Tests for the confidence scoring engine (Sprint 7.2).

Each dimension has a tested rule, the blend obeys the config weights, and the
fallback penalty makes a degraded run score visibly lower than a clean one.
"""

import pytest
from pydantic import ValidationError

from mediscan.confidence import (
    extraction_confidence,
    grounding_confidence,
    score_confidence,
    validation_confidence,
)
from mediscan.config import Settings, settings
from mediscan.schemas import ConfidenceBreakdown

# --- per-dimension rules ---------------------------------------------------


def test_extraction_confidence_rules_beat_llm():
    assert extraction_confidence("rules") == 1.0
    assert extraction_confidence("llm") == 0.7
    # an unknown method is treated cautiously, never a confident 1.0
    assert extraction_confidence("mystery") == 0.7


@pytest.mark.parametrize(
    "retries, expected",
    [(0, 1.0), (1, 0.75), (2, 0.5), (10, 0.0)],  # floored at 0
)
def test_validation_confidence_drops_per_repair(retries, expected):
    assert validation_confidence(retries) == expected


def test_grounding_confidence_is_a_fraction():
    assert grounding_confidence(3, 4) == 0.75
    assert grounding_confidence(0, 2) == 0.0


def test_grounding_confidence_no_ai_outputs_is_full():
    # the deterministic path asserts nothing ungrounded -> full grounding
    assert grounding_confidence(0, 0) == 1.0


# --- the blend -------------------------------------------------------------


def test_perfect_run_scores_one():
    c = score_confidence(ocr=1.0, extraction=1.0, validation=1.0, grounding=1.0)
    assert isinstance(c, ConfidenceBreakdown)
    assert c.overall == 1.0  # weights sum to 1, no fallback penalty


def test_sub_scores_pass_through_unchanged():
    c = score_confidence(ocr=0.8, extraction=0.9, validation=1.0, grounding=0.5)
    assert (c.ocr, c.extraction, c.validation, c.grounding) == (0.8, 0.9, 1.0, 0.5)


def test_overall_is_the_configured_weighted_blend():
    c = score_confidence(ocr=0.8, extraction=0.9, validation=1.0, grounding=0.5)
    expected = (
        settings.confidence_weight_ocr * 0.8
        + settings.confidence_weight_extraction * 0.9
        + settings.confidence_weight_validation * 1.0
        + settings.confidence_weight_grounding * 0.5
    )
    assert c.overall == round(expected, 4)


def test_fallback_depth_lowers_a_clean_run():
    clean = score_confidence(
        ocr=1.0, extraction=1.0, validation=1.0, grounding=1.0, fallback_depth=0
    )
    fell_back = score_confidence(
        ocr=1.0, extraction=1.0, validation=1.0, grounding=1.0, fallback_depth=3
    )
    assert fell_back.overall < clean.overall


def test_fallback_penalty_never_below_the_floor():
    # a huge fallback depth must not drive overall below floor * weighted
    c = score_confidence(
        ocr=1.0, extraction=1.0, validation=1.0, grounding=1.0, fallback_depth=99
    )
    assert c.overall == pytest.approx(settings.confidence_fallback_floor, abs=1e-4)


def test_degraded_run_scores_visibly_lower_than_clean():
    clean = score_confidence(ocr=1.0, extraction=1.0, validation=1.0, grounding=1.0)
    degraded = score_confidence(
        ocr=0.4, extraction=0.7, validation=0.5, grounding=0.0, fallback_depth=2
    )
    assert degraded.overall < clean.overall - 0.3  # a wide, obvious gap


def test_out_of_range_subscore_is_rejected():
    # ConfidenceBreakdown enforces [0, 1]; a bad input fails loudly, not silently
    with pytest.raises(ValidationError):
        score_confidence(ocr=1.5, extraction=1.0, validation=1.0, grounding=1.0)


# --- config guard ----------------------------------------------------------


def test_weights_must_sum_to_one():
    # a misconfigured weight set must crash at startup, not skew trust silently
    with pytest.raises(ValidationError, match="sum to 1.0"):
        Settings(
            confidence_weight_ocr=0.5,
            confidence_weight_extraction=0.5,
            confidence_weight_validation=0.5,
            confidence_weight_grounding=0.5,
        )
