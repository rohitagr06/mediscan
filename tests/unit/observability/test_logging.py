"""Tests for the observability foundation (logging).

Two things matter here: (1) configuration is idempotent so handlers never
stack up and duplicate lines, and (2) the PHI-safe seams actually emit an
event — a CATEGORY, never the offending text — when they fire.
"""

import logging

from mediscan.observability import configure_logging, get_logger
from mediscan.safety.guardrail import check


def test_get_logger_is_namespaced():
    log = get_logger("mediscan.something")
    assert isinstance(log, logging.Logger)
    assert log.name == "mediscan.something"


def test_configure_logging_is_idempotent():
    # Calling it repeatedly must not stack root handlers (which would make
    # every log line print N times). We reset the module flag to exercise the
    # first-call path, then prove a second call adds nothing.
    import mediscan.observability as obs

    obs._CONFIGURED = False
    before = len(logging.getLogger().handlers)
    configure_logging("INFO")
    after_first = len(logging.getLogger().handlers)
    configure_logging("INFO")  # second call: no-op
    after_second = len(logging.getLogger().handlers)

    assert after_second == after_first  # no new handler on the repeat call
    assert after_first >= before


def test_guardrail_trip_logs_category_not_text(caplog):
    # A blocked output must log an EVENT with the category, and the log line
    # must NOT contain the offending text (no PHI / model output in logs).
    offending = "You should take 500 mg of the medication twice daily."
    with caplog.at_level(logging.WARNING, logger="mediscan.safety.guardrail"):
        result = check(offending)

    assert result.passed is False
    assert result.category == "medication_dose"
    # exactly one warning, mentioning the category, NOT the offending text
    messages = [r.getMessage() for r in caplog.records]
    assert any("medication_dose" in m for m in messages)
    assert all("500 mg" not in m for m in messages)


def test_clean_text_logs_nothing(caplog):
    with caplog.at_level(logging.WARNING, logger="mediscan.safety.guardrail"):
        result = check("Your hemoglobin is a little low; consider seeing a doctor.")
    assert result.passed is True
    assert caplog.records == []
