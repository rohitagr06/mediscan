"""Truth-table tests for report urgency."""

from mediscan.medical.severity import assess_results
from mediscan.medical.urgency import assess_urgency
from mediscan.schemas import (
    LabResult,
    UrgencyLevel,
)


def test_all_normal_is_routine():
    urgency = assess_urgency(
        assess_results(
            [
                LabResult(
                    test_name="Hemoglobin",
                    value=15.0,
                ),
                LabResult(
                    test_name="Platelet Count",
                    value=250.0,
                ),
            ]
        )
    )

    assert urgency.level == UrgencyLevel.ROUTINE


def test_moderate_is_consult_soon():
    urgency = assess_urgency(
        assess_results(
            [
                LabResult(
                    test_name="Hemoglobin",
                    value=9.8,
                )
            ]
        )
    )

    assert urgency.level == UrgencyLevel.CONSULT_SOON


def test_high_is_urgent():
    urgency = assess_urgency(
        assess_results(
            [
                LabResult(
                    test_name="Hemoglobin",
                    value=7.5,
                )
            ]
        )
    )

    assert urgency.level == UrgencyLevel.URGENT


def test_critical_is_seek_immediate_care():
    urgency = assess_urgency(
        assess_results(
            [
                LabResult(
                    test_name="Hemoglobin",
                    value=6.0,
                )
            ]
        )
    )

    assert urgency.level == UrgencyLevel.IMMEDIATE


def test_unknown_result_floors_to_consult_soon():
    urgency = assess_urgency(
        assess_results(
            [
                LabResult(
                    test_name="Unknown Test",
                    value=100.0,
                )
            ]
        )
    )

    assert urgency.level == UrgencyLevel.CONSULT_SOON


def test_worst_result_wins():
    urgency = assess_urgency(
        assess_results(
            [
                LabResult(
                    test_name="Hemoglobin",
                    value=15.0,
                ),
                LabResult(
                    test_name="Platelet Count",
                    value=2500.0,
                ),
                LabResult(
                    test_name="MCV",
                    value=90.0,
                ),
            ]
        )
    )

    assert urgency.level == UrgencyLevel.IMMEDIATE


def test_empty_report_is_routine():
    urgency = assess_urgency([])

    assert urgency.level == UrgencyLevel.ROUTINE


def test_reasons_are_not_empty():
    urgency = assess_urgency(
        assess_results(
            [
                LabResult(
                    test_name="Hemoglobin",
                    value=15.0,
                )
            ]
        )
    )

    assert urgency.reasons


def test_contributing_tests_contains_abnormal_tests():
    urgency = assess_urgency(
        assess_results(
            [
                LabResult(
                    test_name="Hemoglobin",
                    value=9.8,
                ),
                LabResult(
                    test_name="Platelet Count",
                    value=250.0,
                ),
            ]
        )
    )

    assert urgency.contributing_tests == ["Hemoglobin"]
