"""Extraction-recall evaluation (Sprint 8.9).

Measures the deterministic parser's RECALL — "of the tests a report contains,
how many did we actually parse?" — on synthetic fixtures. The point is to turn
the messy-real-world recall gap into a NUMBER we can track and improve, instead
of a vibe. Pure and offline (only parse_lab_text), so it runs anywhere.

100% synthetic (decision #010). Real-report recall is checked LOCALLY on
Rohit's Mac and only aggregate numbers are ever recorded — never report text.
"""

from dataclasses import dataclass

from mediscan.extraction.parser import parse_lab_text


@dataclass(frozen=True)
class ExtractionMetrics:
    """Recall for one evaluation case: how many expected tests we parsed."""

    label: str
    expected: int
    matched: int
    missed: tuple[str, ...]
    unexpected: tuple[str, ...]  # parsed rows that were NOT expected (false +)

    @property
    def recall(self) -> float:
        """Fraction of expected tests parsed. 1.0 when nothing was expected."""
        return self.matched / self.expected if self.expected else 1.0

    @property
    def false_positives(self) -> int:
        """How many rows we parsed that should NOT have been (precision risk)."""
        return len(self.unexpected)


def evaluate_extraction(
    label: str, text: str, expected_names: set[str]
) -> ExtractionMetrics:
    """Parse ``text`` and score how many of ``expected_names`` were recovered."""
    parsed = {r.test_name for r in parse_lab_text(text).results}
    expected = set(expected_names)
    matched = expected & parsed
    missed = tuple(sorted(expected - parsed))
    unexpected = tuple(sorted(parsed - expected))
    return ExtractionMetrics(
        label=label,
        expected=len(expected),
        matched=len(matched),
        missed=missed,
        unexpected=unexpected,
    )


# --- Evaluation cases -------------------------------------------------------
# Each case is (label, report_text, expected_test_names). Names are what a
# CORRECT parse should yield; anything in `missed` is a real recall gap.

_CLEAN_MULTIPANEL = """\
Complete Blood Count
Hemoglobin 12.5 g/dL 13.0 - 17.0
Total Leukocyte Count 7.5 10^3/uL 4.0 - 11.0
Platelet Count 250 10^3/uL 150 - 410
Lipid Profile
LDL Cholesterol 165 mg/dL < 100
Triglycerides 180 mg/dL < 150
Glucose
HbA1c 5.4 % 4.0 - 5.6
Kidney Function
Creatinine 0.9 mg/dL 0.7 - 1.3
Uric Acid 5.1 mg/dL 3.5 - 7.2
"""

_CLEAN_EXPECTED = {
    "Hemoglobin",
    "Total Leukocyte Count",
    "Platelet Count",
    "LDL Cholesterol",
    "Triglycerides",
    "HbA1c",
    "Creatinine",
    "Uric Acid",
}

# Messy formats taken from the real Tata 1mg report (post row-reconstruction):
# a range prefixed with a word ("Normal - 70 - 140,") and a range wrapped in
# descriptive text ("Undesirable/high risk <40mg/dL"). These currently defeat
# the range grammar — this case makes that gap a measured number.
_REAL_WORLD_MESSY = """\
Creatinine 1.33 mg/dL 0.7-1.3
Uric Acid 8.5 mg/dL 3.5-7.2
Glucose- Random 80 mg/dL Normal - 70 - 140,
Cholesterol - HDL 47 mg/dL Undesirable/high risk <40mg/dL
"""

_MESSY_EXPECTED = {
    "Creatinine",
    "Uric Acid",
    "Glucose- Random",
    "Cholesterol - HDL",
}

# Real Tata 1mg boilerplate — headers, footers, the pregnancy-range table,
# comments and marketing. NONE of these are lab results: this case guards
# PRECISION (parsing any of them would be a false finding, worse than a miss).
_REAL_WORLD_NOISE = """\
PO No :PO2165710010-237
Name : Mr.ROHIT AGARWAL Client Name : TATA 1MG HYDERABAD
Age/Gender : 33/Male Registration Date : 13/Feb/2025 10:51AM
Barcode ID/Order ID : D16212892 / 11946834 Report Date : 13/Feb/2025 12:46PM
Page 1 of 15
Address: SCB Door No. 3-14-011, 1st Floor,
1st trimester 0.1-2.5 0.81-1.90 7.33-14.8
2nd trimester 0.2-3.0 1.00-2.60 7.93-16.1
TSH T3 T4 Interpretation
High Normal Normal Subclinical Hypothyroidism
The variation is of the order of 50%, hence time of the day has influence.
Get Optimal Requirement of Omega 3 in 1 Capsule
*** End Of Report ***
"""

EVAL_CASES: list[tuple[str, str, set[str]]] = [
    ("clean_multipanel", _CLEAN_MULTIPANEL, _CLEAN_EXPECTED),
    ("real_world_messy", _REAL_WORLD_MESSY, _MESSY_EXPECTED),
    ("real_world_noise", _REAL_WORLD_NOISE, set()),
]


def run_extraction_eval() -> list[ExtractionMetrics]:
    """Run every evaluation case and return its metrics."""
    return [evaluate_extraction(label, text, exp) for label, text, exp in EVAL_CASES]


def format_extraction_report(results: list[ExtractionMetrics]) -> str:
    """Render the metrics as a small Markdown report (for docs / the console)."""
    total_expected = sum(m.expected for m in results)
    total_matched = sum(m.matched for m in results)
    total_fp = sum(m.false_positives for m in results)
    overall = total_matched / total_expected if total_expected else 1.0

    lines = [
        "# Extraction-recall evaluation (synthetic)",
        "",
        f"**Overall recall: {overall:.0%}** "
        f"({total_matched}/{total_expected} expected tests parsed). "
        f"**False positives: {total_fp}** (rows parsed that should not be).",
        "",
        "| Case | Recall | Parsed / Expected | Missed | False+ |",
        "|---|---|---|---|---|",
    ]
    for m in results:
        missed = ", ".join(m.missed) if m.missed else "—"
        fp = ", ".join(m.unexpected) if m.unexpected else "—"
        lines.append(
            f"| {m.label} | {m.recall:.0%} | {m.matched}/{m.expected} "
            f"| {missed} | {fp} |"
        )
    return "\n".join(lines) + "\n"
