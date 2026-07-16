"""Render an AnalysisReport as a self-contained HTML document (Sprint 8.3).

WHY THIS FILE EXISTS
    The PDF is the takeaway artifact of MediScan — the thing a user saves
    and shows their doctor. We build it in TWO deliberate steps:

        AnalysisReport --render_html()--> HTML string --render_pdf()--> bytes

    This module is step one, and it is a PURE FUNCTION: report in, string
    out, no I/O, no WeasyPrint, no system libraries. That makes every
    section unit-testable with plain string assertions — the disclaimer,
    the acknowledged bucket, and the severity colours can never silently
    vanish, because a test greps for each of them.

SAFETY RULES BAKED IN
    - #006: this module only RENDERS what the engine decided. It never
      computes severity or urgency — it looks the verdicts up in the report.
    - The disclaimer is rendered UNCONDITIONALLY from report.disclaimer
      (which the schema guarantees is non-empty).
    - Every dynamic string is HTML-escaped. Report text originates from
      OCR of an untrusted uploaded document; without escaping, a document
      containing "<script>" would inject markup into our output.
    - Acknowledged SENSITIVE tests render name + guidance only — no value,
      no range, no verdict (#030).
"""

import html as _html_stdlib  # stdlib escaping; renamed to avoid any confusion
from collections.abc import Iterable

from mediscan.schemas.coverage import AcknowledgeClass
from mediscan.schemas.labs import AbnormalDirection, LabResult, Severity
from mediscan.schemas.report import AnalysisReport
from mediscan.schemas.urgency import UrgencyLevel

# ---------------------------------------------------------------------------
# Deterministic display mappings (data, not logic — the engine already decided)
# ---------------------------------------------------------------------------

_SEVERITY_CLASS: dict[Severity, str] = {
    Severity.NORMAL: "sev-normal",
    Severity.MILD: "sev-mild",
    Severity.MODERATE: "sev-moderate",
    Severity.HIGH: "sev-high",
    Severity.CRITICAL: "sev-critical",
}

_SEVERITY_LABEL: dict[Severity, str] = {
    Severity.NORMAL: "Normal",
    Severity.MILD: "Mildly abnormal",
    Severity.MODERATE: "Moderately abnormal",
    Severity.HIGH: "Highly abnormal",
    Severity.CRITICAL: "Critical",
}

_URGENCY_CLASS: dict[UrgencyLevel, str] = {
    UrgencyLevel.ROUTINE: "urg-routine",
    UrgencyLevel.CONSULT_SOON: "urg-consult",
    UrgencyLevel.URGENT: "urg-urgent",
    UrgencyLevel.IMMEDIATE: "urg-immediate",
}

_URGENCY_LABEL: dict[UrgencyLevel, str] = {
    UrgencyLevel.ROUTINE: "Routine — discuss at your next regular visit",
    UrgencyLevel.CONSULT_SOON: "Consult a doctor soon",
    UrgencyLevel.URGENT: "Urgent — see a doctor promptly",
    UrgencyLevel.IMMEDIATE: "Seek immediate medical care",
}

_DIRECTION_ARROW: dict[AbnormalDirection, str] = {
    AbnormalDirection.LOW: "&darr;",  # down arrow entity
    AbnormalDirection.HIGH: "&uarr;",  # up arrow entity
}

# The print stylesheet. Kept inline so the HTML is fully self-contained —
# one string IS the whole document, nothing to ship alongside it.
_CSS = """
  @page { size: A4; margin: 18mm 15mm; }
  body { font-family: Helvetica, Arial, sans-serif; color: #1a1a2e; font-size: 11pt; }
  h1 { font-size: 20pt; margin: 0; }
  h2 { font-size: 13pt; border-bottom: 2px solid #16324f; padding-bottom: 2pt;
       margin-top: 16pt; }
  .brand { color: #16324f; }
  .tagline { color: #667; font-size: 9pt; margin-top: 2pt; }
  table { border-collapse: collapse; width: 100%; margin-top: 6pt; }
  th { text-align: left; background: #16324f; color: #fff; padding: 4pt 6pt;
       font-size: 9.5pt; }
  td { padding: 4pt 6pt; border-bottom: 0.5pt solid #ccd; font-size: 10pt; }
  .badge { display: inline-block; padding: 5pt 10pt; border-radius: 4pt;
           color: #fff; font-weight: bold; font-size: 12pt; }
  .urg-routine { background: #2e7d32; }
  .urg-consult { background: #b58900; }
  .urg-urgent { background: #d84315; }
  .urg-immediate { background: #b71c1c; }
  .sev-normal { color: #2e7d32; font-weight: bold; }
  .sev-mild { color: #b58900; font-weight: bold; }
  .sev-moderate { color: #e65100; font-weight: bold; }
  .sev-high { color: #d84315; font-weight: bold; }
  .sev-critical { color: #b71c1c; font-weight: bold; }
  .sev-none { color: #667; }
  .note { color: #556; font-size: 9pt; }
  .disclaimer { margin-top: 18pt; padding: 8pt; background: #fff8e1;
                border: 1pt solid #b58900; font-size: 9pt; }
  ul { margin: 4pt 0 4pt 14pt; padding: 0; }
  li { margin-bottom: 2pt; }
"""


def _esc(value: object) -> str:
    """HTML-escape any value for safe embedding in the document.

    str() first (values may be floats/enums), then html.escape turns
    <, >, & and quotes into harmless entities. EVERY dynamic value in
    this module goes through here — no exceptions.
    """
    return _html_stdlib.escape(str(value), quote=True)


def _fmt_number(value: float) -> str:
    """Render 12.0 as '12' and 12.5 as '12.5' — the way lab reports print."""
    return f"{value:g}"


def _fmt_range(low: float | None, high: float | None, unit: str | None) -> str:
    """Format a (possibly one-sided) reference range for display."""
    unit_part = f" {unit}" if unit else ""
    if low is not None and high is not None:
        return f"{_fmt_number(low)}–{_fmt_number(high)}{unit_part}"
    if high is not None:  # one-sided: only an upper bound, e.g. "< 200"
        return f"&lt; {_fmt_number(high)}{unit_part}"
    if low is not None:  # one-sided: only a lower bound, e.g. "> 40"
        return f"&gt; {_fmt_number(low)}{unit_part}"
    return "—"  # em dash: no range available


def _bullet_list(items: Iterable[str]) -> str:
    """Render a list of strings as <ul><li>…</li></ul> (escaped), or ''."""
    lis = "".join(f"<li>{_esc(item)}</li>" for item in items)
    return f"<ul>{lis}</ul>" if lis else ""


# ---------------------------------------------------------------------------
# Section renderers — one small function per PDF section, each testable alone
# ---------------------------------------------------------------------------


def _header_section() -> str:
    return (
        '<h1 class="brand">MediScan <span class="tagline">by DipsAI</span></h1>'
        '<div class="tagline">Intelligent Medical Report Analyzer '
        "&mdash; informational report</div>"
    )


def _urgency_section(report: AnalysisReport) -> str:
    if report.urgency is None:
        return ""
    level = report.urgency.level
    badge = (
        f'<span class="badge {_URGENCY_CLASS[level]}">'
        f"{_esc(_URGENCY_LABEL[level])}</span>"
    )
    reasons = _bullet_list(report.urgency.reasons)
    return f"<h2>Overall urgency</h2>{badge}{reasons}"


def _findings_section(report: AnalysisReport) -> str:
    """The colour-coded table of ASSESSED findings (engine verdicts only)."""
    if report.coverage is None or not report.coverage.assessed:
        return ""
    # Join units/report-printed ranges back in from the raw lab rows.
    # dict comprehension: {test name -> its LabResult} for O(1) lookup.
    raw_by_name: dict[str, LabResult] = {r.test_name: r for r in report.lab_results}

    rows: list[str] = []
    for finding in report.coverage.assessed:
        raw = raw_by_name.get(finding.test_name)
        unit = raw.unit if raw else None
        rng = raw.reference_range if raw else None
        range_txt = _fmt_range(rng.low, rng.high, unit) if rng else "—"

        if finding.severity is not None:
            sev_class = _SEVERITY_CLASS[finding.severity]
            sev_label = _SEVERITY_LABEL[finding.severity]
        else:  # engine could not band this value (no usable range)
            sev_class, sev_label = "sev-none", "Not assessed"

        arrow = (
            _DIRECTION_ARROW[finding.abnormal_direction]
            if finding.abnormal_direction is not None
            else ""
        )
        value_txt = _fmt_number(finding.value) + (f" {_esc(unit)}" if unit else "")
        rows.append(
            "<tr>"
            f"<td>{_esc(finding.test_name)}</td>"
            f"<td>{value_txt} {arrow}</td>"
            f"<td>{range_txt}</td>"
            f'<td class="{sev_class}">{_esc(sev_label)}</td>'
            "</tr>"
        )
    return (
        "<h2>Assessed results</h2>"
        "<table><thead><tr>"
        "<th>Test</th><th>Your value</th><th>Reference range</th><th>Assessment</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _acknowledged_section(report: AnalysisReport) -> str:
    """Tests we read but did not grade — shown, clearly labelled (#030)."""
    if report.coverage is None or not report.coverage.acknowledged:
        return ""
    rows: list[str] = []
    for ack in report.coverage.acknowledged:
        if ack.classification is AcknowledgeClass.SENSITIVE:
            # SENSITIVE: name + guidance ONLY — no value, no range, no verdict.
            rows.append(
                "<tr>"
                f"<td>{_esc(ack.test_name)}</td><td>—</td><td>—</td>"
                "<td>Result present &mdash; please review with your doctor</td>"
                "</tr>"
            )
        else:  # NUMERIC: value + the report's own range, explicitly ungraded
            rng = ack.reference_range
            range_txt = _fmt_range(rng.low, rng.high, ack.unit) if rng else "—"
            value_txt = _fmt_number(ack.value) + (
                f" {_esc(ack.unit)}" if ack.unit else ""
            )
            rows.append(
                "<tr>"
                f"<td>{_esc(ack.test_name)}</td>"
                f"<td>{value_txt}</td><td>{range_txt}</td>"
                "<td>Shown, not graded by MediScan</td>"
                "</tr>"
            )
    return (
        "<h2>Also in your report (not graded)</h2>"
        '<div class="note">These tests are outside MediScan’s assessed '
        "scope. They are listed for completeness and are never part of the "
        "urgency verdict.</div>"
        "<table><thead><tr>"
        "<th>Test</th><th>Your value</th><th>Report range</th><th>Status</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _summary_sections(report: AnalysisReport) -> str:
    parts: list[str] = []
    if report.patient_summary is not None:
        parts.append(
            "<h2>Summary for you</h2>"
            f"<p>{_esc(report.patient_summary.text)}</p>"
            f"{_bullet_list(report.patient_summary.key_points)}"
        )
    if report.doctor_summary is not None:
        parts.append(
            "<h2>Summary for your doctor</h2>"
            f"<p>{_esc(report.doctor_summary.text)}</p>"
            f"{_bullet_list(report.doctor_summary.clinical_notes)}"
        )
    return "".join(parts)


def _extras_sections(report: AnalysisReport) -> str:
    parts: list[str] = []
    if report.dietary_considerations:
        items = [
            d.suggestion + (f" ({d.rationale})" if d.rationale else "")
            for d in report.dietary_considerations
        ]
        parts.append(
            "<h2>Dietary considerations (informational only)</h2>"
            f"{_bullet_list(items)}"
        )
    if report.specialist_suggestions:
        items = [f"{s.specialty}: {s.reason}" for s in report.specialist_suggestions]
        parts.append(f"<h2>Specialists you could ask about</h2>{_bullet_list(items)}")
    return "".join(parts)


def _confidence_section(report: AnalysisReport) -> str:
    if report.confidence is None:
        return ""
    c = report.confidence
    # Score is a 0..1 float; display as a whole percentage.
    pct = f"{round(c.overall * 100)}%"
    return (
        "<h2>Analysis confidence</h2>"
        f"<p>Overall confidence: <strong>{_esc(pct)}</strong> "
        '<span class="note">(text extraction '
        f"{round(c.ocr * 100)}%, parsing {round(c.extraction * 100)}%, "
        f"validation {round(c.validation * 100)}%, "
        f"grounding {round(c.grounding * 100)}%)</span></p>"
    )


def _unparsed_section(report: AnalysisReport) -> str:
    if report.coverage is None or not report.coverage.unparsed:
        return ""
    count = len(report.coverage.unparsed)
    return (
        "<h2>Lines we could not read</h2>"
        f'<div class="note">{count} line(s) — mostly page headers, '
        "comments and lab boilerplate — were not recognised as results "
        "and are not part of the analysis above.</div>"
        f"<details><summary>Show the {count} unparsed line(s)</summary>"
        f"{_bullet_list(report.coverage.unparsed)}</details>"
    )


def _disclaimer_section(report: AnalysisReport) -> str:
    # Rendered UNCONDITIONALLY — there is no code path around this call,
    # and the schema guarantees report.disclaimer is never empty.
    return (
        f'<div class="disclaimer"><strong>⚠</strong> '
        f"{_esc(report.disclaimer)}</div>"
    )


def render_html(report: AnalysisReport) -> str:
    """Render the complete, self-contained HTML document for one report.

    Pure function: no I/O, no network, no WeasyPrint. Section order is the
    reading order a patient needs: verdict first, details after.
    """
    body = (
        _header_section()
        + _urgency_section(report)
        + _summary_sections(report)
        + _findings_section(report)
        + _acknowledged_section(report)
        + _extras_sections(report)
        + _confidence_section(report)
        + _unparsed_section(report)
        + _disclaimer_section(report)
    )
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>MediScan report</title><style>{_CSS}</style></head>"
        f"<body>{body}</body></html>"
    )
