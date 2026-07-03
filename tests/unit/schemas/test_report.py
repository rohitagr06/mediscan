import pytest
from pydantic import ValidationError

from mediscan.schemas import DEFAULT_DISCLAIMER, AnalysisReport


def test_empty_report_is_valid_with_disclaimer():
    report = AnalysisReport()
    assert report.lab_results == []
    assert report.urgency is None
    assert report.confidence is None  # None = not yet scored (decision #011)
    assert report.disclaimer == DEFAULT_DISCLAIMER
    assert "informational" in report.disclaimer.lower()


def test_disclaimer_cannot_be_emptied():
    with pytest.raises(ValidationError):
        AnalysisReport(disclaimer="")


def test_full_report_from_fixture(sample_cbc_report):
    assert len(sample_cbc_report.lab_results) == 3
    assert sample_cbc_report.urgency.level.value == "consult_soon"
    assert sample_cbc_report.confidence.overall == 0.93
    # every dietary consideration carries the constitutional flag
    assert all(d.informational_only for d in sample_cbc_report.dietary_considerations)


def test_json_round_trip_identity(sample_cbc_report):
    # Task 1.9: serialize -> parse -> must be EXACTLY equal
    json_text = sample_cbc_report.model_dump_json()
    restored = AnalysisReport.model_validate_json(json_text)
    assert restored == sample_cbc_report


def test_round_trip_preserves_enums_as_strings(sample_cbc_report):
    data = sample_cbc_report.model_dump(mode="json")
    assert data["urgency"]["level"] == "consult_soon"
    assert data["lab_results"][0]["severity"] == "moderate"


def test_report_from_plain_dicts():
    # The shape an LLM's JSON output arrives in — nested dicts all the way down
    report = AnalysisReport.model_validate(
        {
            "lab_results": [
                {
                    "test_name": "Hemoglobin",
                    "value": "9.8",
                    "reference_range": {"low": 13.0, "high": 17.0},
                }
            ]
        }
    )
    assert report.lab_results[0].value == 9.8


def test_extra_top_level_field_rejected():
    with pytest.raises(ValidationError):
        AnalysisReport(diagnosis="anemia")
