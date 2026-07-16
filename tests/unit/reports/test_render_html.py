"""Unit tests for the HTML report renderer (Sprint 8.3/8.4).

The renderer is a pure function, so these are plain string assertions:
take the shared `full_report` fixture (built in conftest.py), render it,
and grep the output for every section that must never silently vanish —
above all the disclaimer and the acknowledged bucket's "not graded"
labelling (#030), plus the guarantee that untrusted document text cannot
inject markup.
"""

import pytest

from mediscan.reports.render import render_html
from mediscan.schemas.coverage import CoverageResult
from mediscan.schemas.labs import LabResult, ReferenceRange, Severity
from mediscan.schemas.report import AnalysisReport
from mediscan.schemas.summaries import (
    DietaryConsideration,
    LifestyleConsideration,
)

# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------


def test_disclaimer_always_present_even_on_empty_report():
    # An EMPTY report (nothing analysed) must still carry the disclaimer.
    html = render_html(AnalysisReport())
    assert "informational tool" in html
    assert "does not provide medical advice" in html


def test_all_sections_render_for_a_full_report(full_report):
    html = render_html(full_report)
    # Branding + both summaries + urgency badge + coverage sections.
    assert "MediScan" in html
    assert "Summary for you" in html
    assert "Summary for your doctor" in html
    assert "Urgent — see a doctor promptly" in html
    assert "urg-urgent" in html  # badge carries the level's CSS class
    assert "Assessed results" in html
    assert "Also in your report (not graded)" in html
    assert "Lines we could not read" in html
    assert "informational tool" in html  # disclaimer


def test_each_assessed_finding_has_its_severity_class(full_report):
    html = render_html(full_report)
    assert "sev-high" in html  # Hemoglobin banding
    assert "sev-moderate" in html  # LDL banding
    assert "Hemoglobin" in html
    assert "LDL Cholesterol" in html


def test_one_sided_range_renders_as_less_than(full_report):
    html = render_html(full_report)
    # LDL's report range has only an upper bound -> rendered as "< 100".
    assert "&lt; 100 mg/dL" in html


# ---------------------------------------------------------------------------
# The #030 acknowledged bucket: shown, never graded
# ---------------------------------------------------------------------------


def test_numeric_acknowledged_shows_value_but_no_grade(full_report):
    html = render_html(full_report)
    assert "Vitamin D" in html
    assert "Shown, not graded by MediScan" in html


def test_sensitive_acknowledged_shows_no_value_no_range_no_verdict(full_report):
    html = render_html(full_report)
    assert "PSA" in html
    assert "please review with your doctor" in html
    # The scary 250.0 value must NOT appear anywhere in the document.
    assert "250" not in html


def test_acknowledged_never_carries_severity_styling(full_report):
    html = render_html(full_report)
    # Slice out the acknowledged table and prove no severity class leaked in.
    ack_section = html.split("Also in your report")[1].split("<h2>")[0]
    for css in ("sev-mild", "sev-moderate", "sev-high", "sev-critical"):
        assert css not in ack_section


# ---------------------------------------------------------------------------
# Injection safety: document text is untrusted (it came from OCR)
# ---------------------------------------------------------------------------


def test_unparsed_lines_are_collapsed(full_report):
    # The (long, noisy) unparsed dump is hidden behind a <details> accordion
    # so it never buries the analysis (8.6).
    html = render_html(full_report)
    assert "<details>" in html
    assert "unparsed line" in html


def test_diet_and_lifestyle_sections_render():
    report = AnalysisReport(
        dietary_considerations=[
            DietaryConsideration(suggestion="Favour fibre-rich foods.")
        ],
        lifestyle_considerations=[
            LifestyleConsideration(suggestion="A brisk daily walk is often discussed.")
        ],
    )
    html = render_html(report)
    assert "Diet (informational only)" in html
    assert "Lifestyle (informational only)" in html
    assert "Diet &amp; lifestyle summary" in html
    assert "brisk daily walk" in html
    assert "fibre-rich" in html


def test_malicious_test_name_is_escaped(assessment_factory):
    report = AnalysisReport(
        lab_results=[
            LabResult(
                test_name="<script>alert(1)</script>",
                value=1.0,
                reference_range=ReferenceRange(low=0.0, high=2.0),
            )
        ],
        coverage=CoverageResult(
            assessed=[
                assessment_factory("<script>alert(1)</script>", 1.0, Severity.NORMAL)
            ]
        ),
    )
    html = render_html(report)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_malicious_unparsed_line_is_escaped():
    report = AnalysisReport(
        coverage=CoverageResult(unparsed=['<img src=x onerror="x">'])
    )
    html = render_html(report)
    assert "<img" not in html


# ---------------------------------------------------------------------------
# No advice leakage: the renderer adds no medical language of its own
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("forbidden", ["dosage", "prescribe", "diagnos"])
def test_renderer_adds_no_dosage_or_diagnosis_language(forbidden, full_report):
    # Check the renderer's OWN vocabulary. (AI text is guardrailed upstream;
    # this asserts the template itself is clean.) The disclaimer is the ONE
    # legitimate use ("does not provide ... diagnosis ..."), so it is cut
    # out before checking the rest.
    html = render_html(full_report).lower()
    body_without_disclaimer = html.split('<div class="disclaimer">')[0]
    assert forbidden not in body_without_disclaimer
