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

from mediscan.medical.phrasing import describe_finding
from mediscan.schemas import (
    DietaryConsideration,
    DoctorSummary,
    LifestyleConsideration,
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
    """One plain sentence for a single notable finding (shared phrasing)."""
    return describe_finding(a)


def patient_summary(
    assessments: list[SeverityAssessment], urgency: UrgencyAssessment
) -> PatientSummary:
    """Write a plain-language patient summary from the verdict, no AI.

    Args:
        assessments: One SeverityAssessment per lab value (the judged verdict).
        urgency: The rolled-up urgency for the whole report.

    Returns:
        A PatientSummary whose text names the notable findings and the
        suggested next step; an all-normal report gets a reassuring note.
    """
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
    """Write a concise clinician-facing summary from the verdict, no AI.

    Args:
        assessments: One SeverityAssessment per lab value.
        urgency: The rolled-up urgency for the whole report.

    Returns:
        A DoctorSummary: a one-line overview plus one clinical note per
        notable finding (or an all-in-range note).
    """
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
    """Return informational-only dietary notes from the verdict, no AI.

    Args:
        assessments: One SeverityAssessment per lab value (unused today; kept
            for signature parity with the AI path and future per-test notes).
        urgency: The rolled-up urgency (unused today, same reason).

    Returns:
        A single generic, informational DietaryConsideration. There is no
        per-test diet knowledge base yet (RC2), so the deterministic floor
        stays deliberately generic and safe.
    """
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


def lifestyle(
    assessments: list[SeverityAssessment], urgency: UrgencyAssessment
) -> list[LifestyleConsideration]:
    """Generic, informational lifestyle note from the verdict, no AI.

    No per-test lifestyle knowledge base yet (RC2), so the deterministic
    floor stays deliberately generic and safe.
    """
    return [
        LifestyleConsideration(
            suggestion=(
                "General lifestyle habits — regular physical activity, good "
                "sleep, stress management and staying hydrated — are best "
                "discussed with your doctor."
            ),
            rationale=(
                "Automatic fallback provides no test-specific lifestyle advice."
            ),
        )
    ]


def specialist(
    assessments: list[SeverityAssessment], urgency: UrgencyAssessment
) -> list[SpecialistSuggestion]:
    """Suggest a specialist category from the verdict, no AI.

    Args:
        assessments: One SeverityAssessment per lab value.
        urgency: The rolled-up urgency (unused today).

    Returns:
        One general-review SpecialistSuggestion when any finding is notable,
        or an empty list when everything is normal. The deterministic floor
        does not name specialties beyond "General Practitioner" (no sourced
        test-to-specialist mapping yet — RC2).
    """
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
