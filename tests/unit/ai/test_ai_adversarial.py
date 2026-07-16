"""Adversarial + resilience tests for the AI explanation layer (Claude's half).

Rohit's half (test_ai_layer.py) covers happy paths. THIS file attacks the
platform's guarantees:
  * structured output repairs bad JSON once, then gives up cleanly;
  * the chain falls through providers and lands on the templates;
  * a prompt-injection "fact" cannot make the output unsafe;
  * secrets never leak into errors;
  * the report is ALWAYS complete (every output has a value);
  * provenance is honest (ai vs deterministic).

All mock-first: no network, no API keys. An autouse fixture zeroes retries so
the resilient chain never actually sleeps during tests.
"""

from datetime import UTC, datetime

import pytest

from mediscan.ai.base import LLMClient
from mediscan.ai.chain import generate_with_fallback
from mediscan.ai.exceptions import AllProvidersFailed, LLMError
from mediscan.ai.explain import explain_report
from mediscan.ai.prompts import PatientSummaryPrompt
from mediscan.ai.structured import generate_structured
from mediscan.config import settings
from mediscan.medical.severity import assess_results
from mediscan.medical.urgency import assess_urgency
from mediscan.safety.guardrail import check
from mediscan.schemas import (
    ExplanationSource,
    LabResult,
    LLMResponse,
    PatientSummary,
    ReferenceRange,
)

FIXED_NOW = datetime(2026, 7, 8, tzinfo=UTC)


def _no_grounding(_query):
    """Retriever stub: returns no KB snippets, so these tests stay offline.

    explain_report()'s default retriever builds the real BGE index (a model
    download). These Sprint-5 tests are about the AI/guardrail/provenance
    behaviour, not RAG, so we inject an empty retriever to keep them fast and
    offline. RAG grounding gets its own tests in Sprint 6.9.
    """
    return []


GOOD_PATIENT = (
    '{"text": "Your hemoglobin is a little low. See a doctor soon.", '
    '"key_points": ["Hb low"]}'
)


@pytest.fixture(autouse=True)
def _no_retry_delays(monkeypatch):
    """Zero retries so the chain never sleeps for real during tests."""
    monkeypatch.setattr(settings, "llm_max_retries", 0)


# --- test doubles ----------------------------------------------------------


class ScriptedLLM(LLMClient):
    """Returns queued texts in order; records how many times it was called."""

    provider_name = "scripted"
    model = "scripted-1"

    def __init__(self, texts: list[str]) -> None:
        self._texts = list(texts)
        self.calls = 0

    def complete(self, request) -> LLMResponse:
        self.calls += 1
        return LLMResponse(
            text=self._texts.pop(0),
            provider_name=self.provider_name,
            model=self.model,
            temperature=0.2,
            latency_ms=0.0,
        )


class DeadLLM(LLMClient):
    provider_name = "dead"
    model = "dead-1"

    def complete(self, request) -> LLMResponse:
        raise LLMError("provider down")


class FixedLLM(LLMClient):
    """Always returns one fixed text (used to inject forbidden output)."""

    provider_name = "fixed"
    model = "fixed-1"

    def __init__(self, text: str) -> None:
        self._text = text

    def complete(self, request) -> LLMResponse:
        return LLMResponse(
            text=self._text,
            provider_name="fixed",
            model="fixed-1",
            temperature=0.2,
            latency_ms=0.0,
        )


class SmartFake(LLMClient):
    """Returns shape-correct JSON for whichever prompt it receives."""

    provider_name = "smart"
    model = "smart-1"

    def complete(self, request) -> LLMResponse:
        u = request.user_prompt.lower()
        if "physician" in u:
            text = '{"text": "Mild anemia pattern.", "clinical_notes": ["Hb 9.8"]}'
        elif "diet" in u:
            text = '[{"suggestion": "Iron-rich foods may be discussed."}]'
        elif "lifestyle" in u:
            text = '[{"suggestion": "A brisk daily walk is often discussed."}]'
        elif "specialist" in u:
            text = '[{"specialty": "Hematologist", "reason": "Low hemoglobin."}]'
        else:  # patient
            text = GOOD_PATIENT
        return LLMResponse(
            text=text,
            provider_name="smart",
            model="smart-1",
            temperature=0.2,
            latency_ms=0.0,
        )


def _verdict():
    labs = [
        LabResult(
            test_name="Hemoglobin",
            value=9.8,
            reference_range=ReferenceRange(low=13.0, high=17.0),
        ),
    ]
    a = assess_results(labs)
    return a, assess_urgency(a)


def _no_sleep(_seconds: float) -> None:
    return None


# --- structured output: repair-retry ---------------------------------------


def test_structured_repairs_bad_then_good():
    req = PatientSummaryPrompt().build("Hb low")
    llm = ScriptedLLM(["{ not json", GOOD_PATIENT])
    out = generate_structured(llm, req, PatientSummary)
    assert out.key_points == ["Hb low"]
    assert llm.calls == 2  # one repair used


def test_structured_gives_up_after_one_repair():
    req = PatientSummaryPrompt().build("Hb low")
    llm = ScriptedLLM(["nope", "still nope"])
    with pytest.raises(LLMError):
        generate_structured(llm, req, PatientSummary)
    assert llm.calls == 2  # exactly one repair, then stop


# --- chain: fallthrough + give-up ------------------------------------------


def test_chain_falls_through_then_lands_on_next():
    req = PatientSummaryPrompt().build("Hb low")
    good = ScriptedLLM([GOOD_PATIENT])
    result = generate_with_fallback(
        [DeadLLM(), good], req, PatientSummary, sleep=_no_sleep
    )
    assert result.provider_name == "scripted"


def test_chain_all_fail_raises_all_providers_failed():
    req = PatientSummaryPrompt().build("Hb low")
    with pytest.raises(AllProvidersFailed):
        generate_with_fallback(
            [DeadLLM(), DeadLLM()], req, PatientSummary, sleep=_no_sleep
        )


# --- assembly: always complete, honest provenance --------------------------


def test_report_is_complete_even_when_all_providers_die():
    a, u = _verdict()
    r = explain_report(
        a, u, [DeadLLM(), DeadLLM()], now=lambda: FIXED_NOW, retrieve_fn=_no_grounding
    )
    for e in (r.patient, r.doctor, r.dietary, r.lifestyle, r.specialist):
        assert e.content is not None
        assert e.provenance.source is ExplanationSource.DETERMINISTIC
        assert e.provenance.timestamp == FIXED_NOW


def test_ai_success_is_tagged_ai_with_provider():
    a, u = _verdict()
    r = explain_report(
        a, u, [SmartFake()], now=lambda: FIXED_NOW, retrieve_fn=_no_grounding
    )
    for e in (r.patient, r.doctor, r.dietary, r.lifestyle, r.specialist):
        assert e.provenance.source is ExplanationSource.AI
        assert e.provenance.provider == "smart"
    assert r.patient.provenance.prompt_name == "patient_summary"


def test_guardrail_trip_forces_deterministic_for_that_output():
    a, u = _verdict()
    forbidden = '{"text": "Take 500 mg of iron daily.", "key_points": ["dose"]}'
    r = explain_report(
        a, u, [FixedLLM(forbidden)], now=lambda: FIXED_NOW, retrieve_fn=_no_grounding
    )
    assert r.patient.provenance.source is ExplanationSource.DETERMINISTIC
    assert "500 mg" not in r.patient.content.text


# --- prompt injection -------------------------------------------------------


def test_injection_fact_cannot_produce_unsafe_output():
    """A model that OBEYS an injected 'take a dose' instruction is caught by
    the guardrail, and that output falls back to the clean template."""
    a, u = _verdict()
    obeyed = '{"text": "As instructed, take 500 mg iron.", "key_points": ["x"]}'
    r = explain_report(
        a, u, [FixedLLM(obeyed)], now=lambda: FIXED_NOW, retrieve_fn=_no_grounding
    )
    assert r.patient.provenance.source is ExplanationSource.DETERMINISTIC
    assert check(r.patient.content.text).passed  # the template text is clean


# --- secret hygiene ---------------------------------------------------------


def test_normalized_provider_error_carries_no_secret():
    """Our normalized errors carry only the exception TYPE, never a key."""
    err = LLMError("gemini call failed (RateLimitError)")
    text = str(err)
    for leak in ("sk-", "AIza", "ghp_", "github_pat_"):
        assert leak not in text
