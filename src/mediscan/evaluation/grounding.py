"""Grounding & confidence-sanity evaluation (Sprint 8.9b).

Two safety audits over a finished AnalysisReport, both PURE and offline:

1. HALLUCINATION (grounding). The deterministic verdict is ground truth
   (#006). The human-facing summaries must never introduce a NUMBER or a lab
   TEST NAME that the deterministic results don't support. This module scans
   the patient- and doctor-facing narratives and flags any ungrounded number,
   or any recognised lab-test name that isn't actually in the report.

   Scope note: only the clinical narratives (patient/doctor) are numeric-
   checked. The diet/lifestyle notes legitimately carry non-lab quantities
   ("stay hydrated", a future "30 minutes of activity"), so value-grounding
   does not apply to them — flagging those would be noise, not safety.

2. CONFIDENCE SANITY. A few invariants the confidence breakdown must satisfy
   for the report's state: every score in [0, 1]; zero parsed rows -> zero
   overall (a report that read nothing must not look confident); and overall
   never exceeds its own best component (it is a blend times a <=1 penalty).

Both audits are reusable as a runtime guardrail; here they power an offline
eval over synthetic reports — a faithful deterministic one and a deliberately
tampered one — so we can prove the detector actually has teeth. 100%
synthetic (#010): no real report text ever enters this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mediscan.extraction.normalization import normalize_test_name
from mediscan.medical.coverage import policy_test_names
from mediscan.schemas import AnalysisReport, PatientSummary, Severity

# A number token: optional sign, digits, optional decimal part. Deliberately
# simple — we compare the parsed value against the grounded set with tolerance,
# so we don't need to be clever about scientific notation here.
_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _numbers_in(text: str) -> list[float]:
    return [float(tok) for tok in _NUMBER_RE.findall(text)]


def grounded_numbers(report: AnalysisReport) -> set[float]:
    """Every number the deterministic layer supports.

    That is: each lab value, each printed reference-range bound, and the
    structural COUNTS the summaries legitimately cite ("6 finding(s)"). Any
    number in a clinical narrative outside this set is unsupported.
    """
    nums: set[float] = set()
    for r in report.lab_results:
        nums.add(float(r.value))
        rr = r.reference_range
        if rr is not None:
            if rr.low is not None:
                nums.add(float(rr.low))
            if rr.high is not None:
                nums.add(float(rr.high))
    assessed = report.coverage.assessed
    for a in assessed:
        nums.add(float(a.value))
    abnormal = sum(1 for a in assessed if a.severity is not Severity.NORMAL)
    for count in (
        len(report.lab_results),
        len(assessed),
        len(report.coverage.acknowledged),
        len(report.urgency.contributing_tests),
        abnormal,
    ):
        nums.add(float(count))
    return nums


def _clinical_texts(report: AnalysisReport) -> list[str]:
    """The patient- and doctor-facing strings — where any number must be
    lab-grounded. Diet/lifestyle/specialist text is intentionally excluded."""
    texts: list[str] = []
    ps = report.patient_summary
    if ps is not None:
        texts.append(ps.text)
        texts.extend(ps.key_points)
    ds = report.doctor_summary
    if ds is not None:
        texts.append(ds.text)
        texts.extend(ds.clinical_notes)
    return texts


def find_ungrounded_numbers(report: AnalysisReport) -> tuple[float, ...]:
    """Numbers asserted in the clinical narratives that no lab value, range
    bound or structural count supports — i.e. hallucinated figures."""
    allowed = grounded_numbers(report)

    def is_grounded(n: float) -> bool:
        # absolute tolerance for near-zero values; relative for the rest.
        return any(
            abs(n - a) <= 1e-6 or (a != 0.0 and abs(n - a) / abs(a) <= 1e-3)
            for a in allowed
        )

    bad: list[float] = []
    for text in _clinical_texts(report):
        for n in _numbers_in(text):
            if not is_grounded(n):
                bad.append(n)
    return tuple(sorted(set(bad)))


def find_ungrounded_test_names(report: AnalysisReport) -> tuple[str, ...]:
    """Recognised lab-test names mentioned in the clinical narratives that are
    NOT in the report — e.g. an explanation that talks about "PSA" when no PSA
    was tested.

    Conservative by construction: we only consider the controlled vocabulary of
    policy test names, match on WORD BOUNDARIES (so "MCH" doesn't fire inside
    "MCHC"), and additionally skip any name that appears as a word inside a
    grounded test's own name (so "Urea" doesn't fire on "Blood Urea Nitrogen").
    """
    grounded_canon = {normalize_test_name(r.test_name) for r in report.lab_results}
    grounded_raw = " ".join(r.test_name for r in report.lab_results).lower()
    hay = " ".join(_clinical_texts(report)).lower()

    bad: list[str] = []
    for name in policy_test_names():
        if name in grounded_canon:
            continue
        pattern = rf"\b{re.escape(name.lower())}\b"
        if re.search(pattern, hay) and not re.search(pattern, grounded_raw):
            bad.append(name)
    return tuple(sorted(set(bad)))


def check_confidence_sanity(report: AnalysisReport) -> tuple[str, ...]:
    """Invariants the confidence breakdown must satisfy. Returns a tuple of
    human-readable violations — empty when the confidence is sane."""
    c = report.confidence
    if c is None:
        return ("confidence not scored",)

    problems: list[str] = []
    subs = {
        "ocr": c.ocr,
        "extraction": c.extraction,
        "validation": c.validation,
        "grounding": c.grounding,
    }
    for label, value in {**subs, "overall": c.overall}.items():
        if not (0.0 <= value <= 1.0):
            problems.append(f"{label}={value!r} outside [0, 1]")

    if not report.lab_results and c.overall != 0.0:
        problems.append(f"no lab results but overall={c.overall!r} (must be 0.0)")

    ceiling = max(subs.values())
    if c.overall > ceiling + 1e-9:
        problems.append(f"overall={c.overall!r} exceeds best component {ceiling!r}")

    return tuple(problems)


@dataclass(frozen=True)
class GroundingAudit:
    """The result of auditing one report for hallucination + confidence sanity."""

    label: str
    ungrounded_numbers: tuple[float, ...]
    ungrounded_test_names: tuple[str, ...]
    confidence_problems: tuple[str, ...]

    @property
    def is_clean(self) -> bool:
        return not (
            self.ungrounded_numbers
            or self.ungrounded_test_names
            or self.confidence_problems
        )


def audit_report(label: str, report: AnalysisReport) -> GroundingAudit:
    """Run both safety audits over one report."""
    return GroundingAudit(
        label=label,
        ungrounded_numbers=find_ungrounded_numbers(report),
        ungrounded_test_names=find_ungrounded_test_names(report),
        confidence_problems=check_confidence_sanity(report),
    )


# --- Synthetic evaluation cases --------------------------------------------
# A faithful deterministic report (must audit CLEAN) and a tampered copy whose
# patient summary injects an ungrounded value and an un-tested marker (the
# detector MUST catch both). All synthetic (#010).

_FAITHFUL_TEXT = """\
Hemoglobin 15.3 g/dL 13.0 - 17.0
LDL Cholesterol 131 mg/dL < 100
Uric Acid 8.5 mg/dL 3.5 - 7.2
Creatinine 1.33 mg/dL 0.7 - 1.3
"""


def _faithful_report() -> AnalysisReport:
    """The deterministic pipeline (no AI, stubbed retriever) writes summaries
    straight from the verdict, so every figure is grounded by construction."""
    from mediscan.orchestration.pipeline import analyze_text

    return analyze_text(_FAITHFUL_TEXT, providers=[], retrieve_fn=lambda _q: [])


def _tampered_report(base: AnalysisReport) -> AnalysisReport:
    """Same report, but the patient summary is rewritten to hallucinate: an
    ungrounded value (999.0) and a test never in the report (PSA)."""
    poisoned = PatientSummary(
        text=(
            "Your LDL Cholesterol is 999.0 and your PSA is markedly elevated. "
            "Please act on these results promptly."
        ),
        key_points=["PSA is a concern."],
    )
    return base.model_copy(update={"patient_summary": poisoned})


def run_grounding_eval() -> list[GroundingAudit]:
    """Build the synthetic cases and audit each."""
    faithful = _faithful_report()
    tampered = _tampered_report(faithful)
    return [
        audit_report("faithful_deterministic", faithful),
        audit_report("tampered_hallucination", tampered),
    ]


def format_grounding_report(audits: list[GroundingAudit]) -> str:
    """Render the audits as a small Markdown table (for docs / the console)."""
    clean = sum(1 for a in audits if a.is_clean)
    lines = [
        "# Grounding & confidence-sanity evaluation (synthetic)",
        "",
        f"**{clean}/{len(audits)} reports audited clean.**",
        "",
        "| Report | Ungrounded numbers | Ungrounded test names | Confidence problems |",
        "|---|---|---|---|",
    ]
    for a in audits:
        nums = ", ".join(f"{x:g}" for x in a.ungrounded_numbers) or "—"
        names = ", ".join(a.ungrounded_test_names) or "—"
        conf = "; ".join(a.confidence_problems) or "—"
        lines.append(f"| {a.label} | {nums} | {names} | {conf} |")
    return "\n".join(lines) + "\n"
