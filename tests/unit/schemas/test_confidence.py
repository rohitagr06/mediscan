"""Tests for mediscan.schemas.confidence.

The key rule under guard (decision #011): confidence scores have NO
defaults — a bare ConfidenceBreakdown() must fail with exactly five
missing-field errors, one per score.
"""

import pytest
from pydantic import ValidationError

from mediscan.schemas import ConfidenceBreakdown, ProcessingMetadata


def test_explicit_scores_accepted():
    cb = ConfidenceBreakdown(
        ocr=0.9, extraction=0.85, validation=1.0, grounding=0.8, overall=0.86
    )
    assert cb.overall == 0.86


def test_bare_breakdown_rejected_all_five_missing():
    # Decision #011: no optimistic defaults — every score explicit
    with pytest.raises(ValidationError) as exc_info:
        ConfidenceBreakdown()
    assert exc_info.value.error_count() == 5


def test_each_score_bounded():
    good = dict(ocr=1.0, extraction=1.0, validation=1.0, grounding=1.0, overall=1.0)
    for field in good:
        for bad_value in (1.2, -0.1):
            with pytest.raises(ValidationError):
                ConfidenceBreakdown(**{**good, field: bad_value})


def test_nan_score_rejected():
    with pytest.raises(ValidationError):
        ConfidenceBreakdown(
            ocr=float("nan"), extraction=1, validation=1, grounding=1, overall=1
        )


def test_metadata_defaults():
    md = ProcessingMetadata()
    assert md.duration_ms is None
    assert md.models_used == []
    assert md.fallback_count == 0
    assert md.ocr_engine is None


def test_negative_fallback_count_rejected():
    with pytest.raises(ValidationError):
        ProcessingMetadata(fallback_count=-1)


def test_models_used_lists_are_independent():
    a, b = ProcessingMetadata(), ProcessingMetadata()
    a.models_used.append("gemini-flash")
    assert b.models_used == []
