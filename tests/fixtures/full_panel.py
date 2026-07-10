"""Synthetic full-body-checkup fixtures for the coverage pipeline (Sprint 6.5.10).

Two variants of the SAME multi-panel report — one male, one female — built to
drive the whole scope-aware pipeline end to end:

    parse  ->  read patient sex  ->  classify coverage (assessed vs acknowledged)
           ->  severity per assessed value  ->  one urgency roll-up

WHY A MALE AND A FEMALE VARIANT
    Every row prints its OWN reference range (decision #018), and in a real
    report those ranges are already sex-appropriate. So the Hemoglobin range
    differs between the two variants, and the SAME 12.5 value bands LOW for the
    male variant (12.5 < 13.0) but NORMAL for the female variant (within
    12.0-15.0). That is the sex difference this fixture proves end to end — on
    top of the patient sex being read from each variant's header.

OUT-OF-SCOPE ROWS ARE INCLUDED ON PURPOSE
    * CEA      — a Tier-C SENSITIVE tumour marker: must be acknowledged with NO
                 range or verdict, and must NEVER reach the urgency roll-up.
    * hs-CRP   — a Tier-B DEFERRED numeric: acknowledged with its range, not
                 graded in RC1.
    * Ferritin — a test the policy has never seen: acknowledged NUMERIC, the
                 safe default for anything unvetted.

100% synthetic — no real patient data (decision #010).
"""

SENTINEL = "SYNTHETIC FULL-PANEL DOCUMENT FOR SOFTWARE TESTING - NOT A REAL REPORT"


def full_panel_text(sex_label: str, hemoglobin_range: str) -> str:
    """Build one variant's report text.

    Args:
        sex_label: "Male" or "Female" — planted in the demographics header so
            extract_patient_context can read it back.
        hemoglobin_range: the printed Hb range for this variant
            ("13.0 - 17.0" for male, "12.0 - 15.0" for female) — realistic and
            sex-appropriate, so the same value bands differently per sex.
    """
    return f"""\
DipsAI Diagnostics - Full Body Checkup
Name : Synthetic Patient    Age/Sex : 40/{sex_label}

Complete Blood Count (CBC)
Hemoglobin 12.5 g/dL {hemoglobin_range}
Total Leukocyte Count 7.5 10^3/uL 4.0 - 11.0
Platelet Count 250 10^3/uL 150 - 410

Lipid Profile
Total Cholesterol 245 mg/dL 125 - 200 H
Triglycerides 180 mg/dL < 150 H
HDL Cholesterol 38 mg/dL > 40 L
LDL Cholesterol 165 mg/dL < 100 H

Glucose
Fasting Glucose 92 mg/dL 70 - 100
HbA1c 5.4 % 4.0 - 5.6

Thyroid Profile
TSH 2.1 uIU/mL 0.4 - 4.0

Kidney Function
Creatinine 0.9 mg/dL 0.7 - 1.3

Tumour Markers
CEA 2.1 ng/mL 0 - 5

Inflammation
hs-CRP 1.8 mg/L 0 - 3

Iron Studies
Ferritin 210 ng/mL 30 - 400
{SENTINEL}
"""


# The two ready-to-use variants.
MALE_REPORT = full_panel_text("Male", "13.0 - 17.0")
FEMALE_REPORT = full_panel_text("Female", "12.0 - 15.0")
