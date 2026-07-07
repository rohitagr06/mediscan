"""Unit tests for ParseOutcome."""

import pytest
from pydantic import ValidationError

from mediscan.schemas import (
    LabResult,
    ParseOutcome,
    Severity,
)


def test_parse_outcome_accepts_empty_lists() -> None:
    """An empty ParseOutcome is a valid parser result."""
    outcome = ParseOutcome()

    assert outcome.results == []
    assert outcome.unparsed_lines == []


def test_parse_outcome_preserves_results_and_unparsed_lines() -> None:
    """Parsed results and unparsed lines should be stored unchanged."""
    lab_result = LabResult(
        test_name="Hemoglobin",
        value=9.8,
        unit="g/dL",
        severity=Severity.NORMAL,
    )

    outcome = ParseOutcome(
        results=[lab_result],
        unparsed_lines=[
            "Random OCR noise",
            "Unreadable footer",
        ],
    )

    assert len(outcome.results) == 1
    assert outcome.results[0] == lab_result

    assert outcome.unparsed_lines == [
        "Random OCR noise",
        "Unreadable footer",
    ]


def test_parse_outcome_rejects_unknown_fields() -> None:
    """Unexpected fields should be rejected by MediScanModel."""
    with pytest.raises(ValidationError):
        ParseOutcome(
            unexpected_field=True,
        )


def test_parse_outcome_uses_independent_default_lists() -> None:
    """Default list fields should not be shared between instances."""
    first = ParseOutcome()
    second = ParseOutcome()

    first.unparsed_lines.append("OCR noise")

    assert first.unparsed_lines == ["OCR noise"]
    assert second.unparsed_lines == []

    first.results.append(
        LabResult(
            test_name="Hemoglobin",
            value=9.8,
            unit="g/dL",
            severity=Severity.NORMAL,
        )
    )

    assert len(first.results) == 1
    assert second.results == []
