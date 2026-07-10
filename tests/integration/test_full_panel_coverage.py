"""End-to-end integration for the scope-aware pipeline (Sprint 6.5.10).

Sprint 6.5's milestone in one file: a realistic, multi-panel full-body-checkup
report becomes a *scoped* medical verdict, with ZERO AI involved. It drives the
whole deterministic chain the sprint built:

    text  ->  read patient sex   (extraction/metadata)
          ->  parse              (extraction/parser)
          ->  classify coverage  (medical/coverage: assessed vs acknowledged)
          ->  severity per value (medical/severity, via coverage)
          ->  one urgency roll-up over ASSESSED tests only (medical/urgency)

It proves the three things Sprint 6.5 added on top of Sprint 4's CBC pipeline:

  1. SEX is read from the report and the report's sex-appropriate ranges band
     the same value differently — Hemoglobin 12.5 is LOW for the male variant
     (12.5 < 13.0) but NORMAL for the female variant (within 12.0-15.0).
  2. ONE-SIDED ranges band end to end without inventing a direction — LDL
     "< 100" bands HIGH, HDL "> 40" bands LOW.
  3. OUT-OF-SCOPE tests are ACKNOWLEDGED, never graded, and never touch the
     urgency roll-up — a sensitive CEA carries no range/verdict, a deferred
     hs-CRP and an unknown Ferritin are shown but not graded.

The fixtures are 100% synthetic (decision #010); see tests/fixtures/full_panel.py.
"""

from fixtures.full_panel import FEMALE_REPORT, MALE_REPORT, SENTINEL
from mediscan.extraction.metadata import extract_patient_context
from mediscan.extraction.parser import parse_lab_text
from mediscan.medical.coverage import classify_coverage
from mediscan.medical.urgency import assess_urgency
from mediscan.schemas import AbnormalDirection, Severity, Sex, UrgencyLevel
from mediscan.schemas.coverage import AcknowledgeClass

# The three out-of-scope rows every variant carries. None may ever be graded.
OUT_OF_SCOPE = {"CEA", "hs-CRP", "Ferritin"}


def _run(text: str, sex: Sex):
    """Drive one report all the way to (coverage, urgency)."""
    ctx = extract_patient_context(text)
    assert ctx.sex is sex  # the header was read correctly
    assert ctx.age == 40

    outcome = parse_lab_text(text)
    coverage = classify_coverage(outcome, ctx.sex)
    urgency = assess_urgency(coverage.assessed)
    return coverage, urgency


def _assessed_by_name(coverage):
    return {a.test_name: a for a in coverage.assessed}


def _assert_common_scope(coverage, urgency):
    """Everything that must hold regardless of the patient's sex."""
    assessed = _assessed_by_name(coverage)

    # --- lipid panel bands correctly, one-sided ranges included -------------
    assert assessed["Total Cholesterol"].abnormal_direction is AbnormalDirection.HIGH
    assert assessed["Triglycerides"].abnormal_direction is AbnormalDirection.HIGH
    # HDL "> 40" is one-sided-high; 38 is BELOW it -> LOW (not invented HIGH).
    assert assessed["HDL Cholesterol"].abnormal_direction is AbnormalDirection.LOW
    # LDL "< 100" is one-sided-high; 165 is ABOVE it -> HIGH (never LOW).
    assert assessed["LDL Cholesterol"].abnormal_direction is AbnormalDirection.HIGH

    # --- the normal tests really are normal --------------------------------
    for name in ("Fasting Glucose", "HbA1c", "TSH", "Creatinine", "Platelet Count"):
        assert assessed[name].severity is Severity.NORMAL
        assert assessed[name].abnormal_direction is None

    # --- nothing critical anywhere; the verdict is Urgent ------------------
    assert all(a.severity is not Severity.CRITICAL for a in coverage.assessed)
    assert urgency.level is UrgencyLevel.URGENT
    assert urgency.reasons  # explainability is mandatory (schema guarantees >=1)

    # --- OUT-OF-SCOPE tests are acknowledged, NEVER graded ------------------
    ack = {a.test_name: a for a in coverage.acknowledged}
    assert set(ack) == OUT_OF_SCOPE
    # none of them leaked into the graded set or the urgency roll-up
    assert OUT_OF_SCOPE.isdisjoint(assessed)
    assert OUT_OF_SCOPE.isdisjoint(set(urgency.contributing_tests))
    # a sensitive tumour marker shows NO range or verdict — only "see a doctor"
    assert ack["CEA"].classification is AcknowledgeClass.SENSITIVE
    assert ack["CEA"].reference_range is None
    # a deferred numeric is acknowledged WITH its range, but still not graded
    assert ack["hs-CRP"].classification is AcknowledgeClass.NUMERIC
    assert ack["hs-CRP"].reference_range is not None

    # --- non-lab lines are recorded, never silently dropped ----------------
    assert coverage.unparsed  # panel headers / demographics land here
    assert any(SENTINEL in line for line in coverage.unparsed)


def test_male_full_panel_end_to_end():
    coverage, urgency = _run(MALE_REPORT, Sex.MALE)
    _assert_common_scope(coverage, urgency)

    # SEX MATTERS: the male range is 13.0-17.0, so 12.5 is LOW.
    hb = _assessed_by_name(coverage)["Hemoglobin"]
    assert hb.abnormal_direction is AbnormalDirection.LOW
    assert hb.severity is Severity.MILD


def test_female_full_panel_end_to_end():
    coverage, urgency = _run(FEMALE_REPORT, Sex.FEMALE)
    _assert_common_scope(coverage, urgency)

    # SAME 12.5 value, SAME pipeline — but the female range is 12.0-15.0, so
    # 12.5 is NORMAL. This is the sex-difference the fixture exists to prove.
    hb = _assessed_by_name(coverage)["Hemoglobin"]
    assert hb.severity is Severity.NORMAL
    assert hb.abnormal_direction is None


def test_sex_is_the_only_difference_between_the_two_variants():
    """The two variants differ ONLY in the Hemoglobin verdict.

    Every other assessed test — and the whole acknowledged bucket — must be
    identical, so we know the sex plumbing changed exactly what it should and
    nothing else.
    """
    male_cov, _ = _run(MALE_REPORT, Sex.MALE)
    female_cov, _ = _run(FEMALE_REPORT, Sex.FEMALE)

    male = _assessed_by_name(male_cov)
    female = _assessed_by_name(female_cov)
    assert set(male) == set(female)

    for name in male:
        if name == "Hemoglobin":
            continue  # the one intended difference
        assert male[name].severity is female[name].severity, name
        assert male[name].abnormal_direction is female[name].abnormal_direction, name
