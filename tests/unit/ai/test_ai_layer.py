"""Happy-path tests for the AI explanation layer."""

from mediscan.ai.base import LLMClient
from mediscan.ai.prompts import DoctorSummaryPrompt, PatientSummaryPrompt
from mediscan.ai.structured import generate_structured
from mediscan.ai.templates import dietary, doctor_summary, patient_summary, specialist
from mediscan.medical.severity import assess_results
from mediscan.medical.urgency import assess_urgency
from mediscan.safety.guardrail import check
from mediscan.schemas import (
    DoctorSummary,
    LabResult,
    LLMResponse,
    PatientSummary,
    ReferenceRange,
)


class FakeLLM(LLMClient):
    provider_name = "fake"
    model = "fake-1"

    def __init__(self, text):
        self._text = text

    def complete(self, request):
        return LLMResponse(
            text=self._text,
            provider_name="fake",
            model="fake-1",
            temperature=0.2,
            latency_ms=0.0,
        )


def _verdict():
    labs = [
        LabResult(
            test_name="Hemoglobin",
            value=9.8,
            reference_range=ReferenceRange(low=13.0, high=17.0),
        )
    ]
    a = assess_results(labs)
    return a, assess_urgency(a)


def test_fake_llm_builds_patient_summary():
    text = '{"text": "Your hemoglobin is a little low.", "key_points": ["Hb low"]}'
    out = generate_structured(
        FakeLLM(text), PatientSummaryPrompt().build("Hb low"), PatientSummary
    )
    assert isinstance(out, PatientSummary)
    assert out.key_points == ["Hb low"]


def test_fake_llm_builds_doctor_summary():
    text = '{"text": "Mild anemia.", "clinical_notes": ["Hb 9.8"]}'
    out = generate_structured(
        FakeLLM(text), DoctorSummaryPrompt().build("Hb low"), DoctorSummary
    )
    assert isinstance(out, DoctorSummary)


def test_templates_produce_all_four():
    a, u = _verdict()
    assert patient_summary(a, u).text
    assert doctor_summary(a, u).text
    assert dietary(a, u)[0].informational_only is True
    assert specialist(a, u)[0].specialty


def test_guardrail_passes_clean_text():
    assert check("Your hemoglobin is 9.8 g/dL, moderately low.").passed


def test_guardrail_blocks_dose():
    assert not check("Take 500 mg of iron daily.").passed
