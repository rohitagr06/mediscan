"""Report-level explanation assembly + finding selection (Sprint 7.3).

The existing explain_report already produces the four grounded, guardrailed,
provenance-tagged outputs. 7.3 adds the SELECTION layer in front of it:
noteworthy findings only, most-severe-first, capped — so a huge report stays
affordable — and an all-normal report still gets a reassuring summary.
"""

from mediscan.ai.explain import _findings_to_explain, assemble_report_explanations
from mediscan.config import settings
from mediscan.medical.severity import assess_lab_result
from mediscan.medical.urgency import assess_urgency
from mediscan.schemas import ExplanationSource, LabResult, ReferenceRange, Severity


def _assess(name, value, low, high):
    """Build a real SeverityAssessment via the deterministic engine."""
    return assess_lab_result(
        LabResult(
            test_name=name,
            value=value,
            unit="u",
            reference_range=ReferenceRange(low=low, high=high),
        )
    )


# --- selection: which findings get explained -------------------------------


def test_normal_findings_are_excluded():
    normal = _assess("A", 15.0, 10.0, 20.0)  # inside range -> NORMAL
    abnormal = _assess("B", 2.0, 10.0, 20.0)  # far below -> abnormal
    assert normal.severity is Severity.NORMAL

    selected = _findings_to_explain([normal, abnormal])
    names = [a.test_name for a in selected]
    assert names == ["B"]  # only the abnormal one


def test_most_severe_comes_first():
    mild = _assess("mild", 9.5, 10.0, 20.0)  # just below -> mild
    severe = _assess("severe", 2.0, 10.0, 20.0)  # far below -> high
    # pass them in the "wrong" order to prove sorting, not input order
    selected = _findings_to_explain([mild, severe])
    assert selected[0].test_name == "severe"
    assert selected[1].test_name == "mild"


def test_cap_limits_to_config(monkeypatch):
    monkeypatch.setattr(settings, "max_explained_findings", 2)
    many = [_assess(f"T{i}", 2.0, 10.0, 20.0) for i in range(5)]  # 5 abnormal
    selected = _findings_to_explain(many)
    assert len(selected) == 2  # capped
    assert all(a.severity is not Severity.NORMAL for a in selected)


def test_all_normal_keeps_the_full_list():
    # an all-normal report still needs context so the summary can reassure
    normals = [_assess(f"N{i}", 15.0, 10.0, 20.0) for i in range(3)]
    selected = _findings_to_explain(normals)
    assert len(selected) == 3


# --- assembly end to end (deterministic path, offline) ---------------------


def test_assemble_grounds_only_noteworthy_and_returns_four_outputs():
    normal = _assess("Normal", 15.0, 10.0, 20.0)
    low = _assess("Low", 2.0, 10.0, 20.0)
    high = _assess("High", 40.0, 10.0, 20.0)
    assessments = [normal, low, high]
    urgency = assess_urgency(assessments)

    queries: list[str] = []

    def spy_retrieve(query: str):
        queries.append(query)
        return []  # no snippets — keeps it offline, still exercises the path

    # providers=[] -> the chain finds nothing -> every output uses the
    # deterministic template. No AI, no network.
    result = assemble_report_explanations(
        assessments, urgency, providers=[], retrieve_fn=spy_retrieve
    )

    # all four outputs exist and came from the deterministic floor
    for out in (result.patient, result.doctor, result.dietary, result.specialist):
        assert out.provenance.source is ExplanationSource.DETERMINISTIC

    # grounding was queried ONLY for the two abnormal findings, never the normal
    assert len(queries) == 2
    assert all("Normal" not in q for q in queries)
