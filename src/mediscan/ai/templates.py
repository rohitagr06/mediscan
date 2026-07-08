"""Deterministic template fallback — rung 4 of the #004 chain, ZERO AI.

WHY THIS FILE EXISTS
    When every AI provider fails (AllProvidersFailed) or the guardrail (5.9)
    rejects AI text, MediScan must STILL produce all four outputs. These pure
    functions write plain, correct summaries straight from the deterministic
    verdict — no network, no keys, no model. The product degrades to plainer
    language, never to nothing (decision #004).

    NOTE: this is not an LLMClient. It consumes the VERDICT (severities +
    urgency), not prompts — it is the floor the assembly drops to.
"""

from mediscan.schemas import (
    DietaryConsideration,
    DoctorSummary,
    PatientSummary,
    Severity,
    SpecialistSuggestion,
    UrgencyAssessment,
    UrgencyLevel,
)
from mediscan.schemas.medical import SeverityAssessment

# Plain-language next-step phrase per urgency level.
_URGENCY_PHRASE: dict[UrgencyLevel, str] = {
    UrgencyLevel.ROUTINE: "routine follow-up is suggested",
    UrgencyLevel.CONSULT_SOON: "seeing a doctor soon is suggested",
    UrgencyLevel.URGENT: "seeing a doctor promptly is suggested",
    UrgencyLevel.IMMEDIATE: "seeking immediate medical care is suggested",
}


def _notable(assessments: list[SeverityAssessment]) -> list[SeverityAssessment]:
    """Findings that are not confirmed-normal (abnormal bands OR un-assessable)."""
    return [a for a in assessments if a.severity is not Severity.NORMAL]


def _describe(a: SeverityAssessment) -> str:
    """One plain sentence for a single notable finding."""
    if a.severity is None:
        return f"{a.test_name} could not be assessed (no reference range)."
    direction = a.abnormal_direction.value if a.abnormal_direction else "abnormal"
    return f"{a.test_name} is {a.severity.value} ({direction}) at {a.value}."


def patient_summary(
    assessments: list[SeverityAssessment], urgency: UrgencyAssessment
) -> PatientSummary:
    notable = _notable(assessments)
    step = _URGENCY_PHRASE[urgency.level]
    if not notable:
        return PatientSummary(
            text=f"All of your results are within the normal range, and {step}.",
            key_points=["All results within normal limits."],
        )
    points = [_describe(a) for a in notable]
    text = (
        f"Your results show {len(notable)} finding(s) that stand out. "
        + " ".join(points)
        + f" As a next step, {step}."
    )
    return PatientSummary(text=text, key_points=points)


def doctor_summary(
    assessments: list[SeverityAssessment], urgency: UrgencyAssessment
) -> DoctorSummary:
    notable = _notable(assessments)
    notes = [_describe(a) for a in notable] or ["All assessed values within range."]
    text = (
        f"{len(notable)} abnormal/un-assessable finding(s). "
        f"Overall urgency: {urgency.level.value}."
    )
    return DoctorSummary(text=text, clinical_notes=notes)


def dietary(
    assessments: list[SeverityAssessment], urgency: UrgencyAssessment
) -> list[DietaryConsideration]:
    # No test-specific diet knowledge base yet (RC2), so the deterministic
    # floor gives one safe, generic informational note.
    return [
        DietaryConsideration(
            suggestion=(
                "General dietary and lifestyle questions are best discussed "
                "with your doctor."
            ),
            rationale="Automatic fallback provides no test-specific dietary advice.",
        )
    ]


def specialist(
    assessments: list[SeverityAssessment], urgency: UrgencyAssessment
) -> list[SpecialistSuggestion]:
    notable = _notable(assessments)
    if not notable:
        return []
    return [
        SpecialistSuggestion(
            specialty="General Practitioner",
            reason=(
                f"{len(notable)} lab finding(s) outside the normal range "
                "warrant clinical review."
            ),
        )
    ]
