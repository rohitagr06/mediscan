"""Coverage classification + the assessment allowlist (decision #030).

Splits a report's parsed results into ASSESSED (Tier-A tests, run through the
deterministic engine) and ACKNOWLEDGED (everything else — read and shown, not
graded). Whether a test is assessable is decided by an explicit POLICY table,
kept SEPARATE from the medical KB. Only assessed tests reach the urgency
roll-up, so an acknowledged PSA can never influence the verdict (#006).

A test that isn't in the policy at all defaults to acknowledged-NUMERIC: shown
with the report's own range, never graded — the safe choice for a test we
haven't vetted.
"""

from mediscan.extraction.normalization import normalize_test_name
from mediscan.medical.severity import assess_lab_result
from mediscan.schemas import ParseOutcome
from mediscan.schemas.coverage import (
    AcknowledgeClass,
    AcknowledgedTest,
    AssessmentPolicy,
    AssessmentTier,
    CoverageResult,
)
from mediscan.schemas.patient import Sex

_A = AssessmentTier.ASSESSED
_B = AssessmentTier.DEFERRED
_C = AssessmentTier.EXCLUDED
_NUM = AcknowledgeClass.NUMERIC
_SEN = AcknowledgeClass.SENSITIVE

# (canonical name, tier, classification). Canonical names MUST match the
# right-hand side of normalize_test_name. Data, not logic — extend as scope
# grows. Classification only matters for tests that are NOT assessed.
_POLICY_DATA: list[tuple[str, AssessmentTier, AcknowledgeClass]] = [
    # --- Tier A: ASSESSED (CBC + first wave) ---
    ("Hemoglobin", _A, _NUM),
    ("Total Leukocyte Count", _A, _NUM),
    ("Platelet Count", _A, _NUM),
    ("Hematocrit", _A, _NUM),
    ("MCV", _A, _NUM),
    ("Total Cholesterol", _A, _NUM),
    ("Triglycerides", _A, _NUM),
    ("HDL Cholesterol", _A, _NUM),
    ("LDL Cholesterol", _A, _NUM),
    ("VLDL Cholesterol", _A, _NUM),
    ("Non-HDL Cholesterol", _A, _NUM),
    ("Fasting Glucose", _A, _NUM),
    ("Postprandial Glucose", _A, _NUM),
    ("HbA1c", _A, _NUM),
    ("TSH", _A, _NUM),
    ("Free T3", _A, _NUM),
    ("Free T4", _A, _NUM),
    ("Creatinine", _A, _NUM),
    ("Urea", _A, _NUM),
    ("Blood Urea Nitrogen", _A, _NUM),
    ("Uric Acid", _A, _NUM),
    # --- Tier C: EXCLUDED / sensitive (acknowledged, refer to a doctor) ---
    ("PSA", _C, _SEN),
    ("Free PSA", _C, _SEN),
    ("CEA", _C, _SEN),
    ("AFP", _C, _SEN),
    ("CA 19-9", _C, _SEN),
    ("CA 125", _C, _SEN),
    ("CA 15-3", _C, _SEN),
    ("HIV", _C, _SEN),
    ("HBsAg", _C, _SEN),
    ("Anti-HCV", _C, _SEN),
    ("VDRL", _C, _SEN),
    ("Testosterone", _C, _SEN),
    ("SHBG", _C, _SEN),
    ("FSH", _C, _SEN),
    ("LH", _C, _SEN),
    ("Estradiol", _C, _SEN),
    ("Prolactin", _C, _SEN),
    ("Cortisol", _C, _SEN),
    # --- Tier B: DEFERRED numeric (acknowledged, not graded in RC1) ---
    ("hs-CRP", _B, _NUM),
    ("Homocysteine", _B, _NUM),
    ("Lipoprotein(a)", _B, _NUM),
    ("Apolipoprotein B", _B, _NUM),
    ("NT-proBNP", _B, _NUM),
    ("HOMA-IR", _B, _NUM),
    ("Fasting Insulin", _B, _NUM),
]

_POLICY: dict[str, AssessmentPolicy] = {
    name: AssessmentPolicy(test_name=name, tier=tier, classification=cls)
    for name, tier, cls in _POLICY_DATA
}


def policy_for(canonical_name: str) -> AssessmentPolicy | None:
    """Return the assessment policy for a canonical test name, or None."""
    return _POLICY.get(canonical_name)


def classify_coverage(outcome: ParseOutcome, sex: Sex = Sex.UNKNOWN) -> CoverageResult:
    """Split parsed results into assessed vs acknowledged; keep unparsed lines.

    Args:
        outcome: The parser's output (recognized results + unparsed lines).
        sex: Patient sex, passed to the engine for assessed tests.

    Returns:
        A CoverageResult. Every parsed test is accounted for — graded if the
        policy allows it, otherwise acknowledged with the right presentation
        class. Acknowledged tests never reach the urgency roll-up.
    """
    assessed = []
    acknowledged = []

    for result in outcome.results:
        canonical = normalize_test_name(result.test_name)
        policy = policy_for(canonical)

        if policy is not None and policy.assessable:
            assessed.append(assess_lab_result(result, sex))
            continue

        # Not assessable: acknowledge it. Unknown tests (no policy) default to
        # NUMERIC — shown with their range, never graded.
        classification = policy.classification if policy is not None else _NUM
        acknowledged.append(
            AcknowledgedTest(
                test_name=canonical,
                value=result.value,
                unit=result.unit,
                # A sensitive test shows no range or verdict — only that it is
                # present and needs a doctor.
                reference_range=(
                    result.reference_range
                    if classification is AcknowledgeClass.NUMERIC
                    else None
                ),
                classification=classification,
            )
        )

    return CoverageResult(
        assessed=assessed,
        acknowledged=acknowledged,
        unparsed=list(outcome.unparsed_lines),
    )
