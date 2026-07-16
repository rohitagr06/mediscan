# Evaluation (Sprint 8.9)

Honest, repeatable quality metrics for MediScan's deterministic engine.
**Synthetic only** (#010) — real-report accuracy is checked locally on Rohit's
Mac and only *aggregate numbers* are ever recorded here, never report text.

Regenerate with: `uv run python -m mediscan.evaluation`.

## Extraction recall + precision

Measures, on synthetic fixtures: **recall** (of the tests a report contains,
how many did we parse?) and **precision** (did we ever parse something we
shouldn't — a false finding, which for a medical tool is worse than a miss).

**Baseline** (before the 8.9 parser fix): overall recall **83%** (10/12). The
messy real-world formats missed — HDL's descriptive wrapped range
(`Undesirable/high risk <40mg/dL`) and glucose's word-prefixed range
(`Normal - 70 - 140,`).

**After the 8.9 parser fix** (a digit-free, bounded descriptive prefix before
the range + a consumer for units glued onto a one-sided range):

| Case | Recall | Parsed / Expected | False positives |
|---|---|---|---|
| clean_multipanel | 100% | 8/8 | 0 |
| real_world_messy | 100% | 4/4 | 0 |
| real_world_noise | — | 0/0 | 0 |
| **Overall** | **100%** | **12/12** | **0** |

The `real_world_noise` case (real Tata boilerplate: headers, footers, the
pregnancy reference-range table, comments, marketing) parses to **zero** rows —
precision held while recall rose from 83% to 100%. Guarded by
`test_noise_case_yields_no_false_positives` and the parser precision tests.

## Still to do in this evaluation pass

- **Real-report accuracy** — run the app locally on the real Tata / Lal PathLabs
  / Labsmart PDFs; record only aggregate recall numbers here (never text, #010).
- **Hallucination + confidence sanity** — every AI output grounded or
  guardrailed; degraded input scores lower (confidence-on-zero already covered
  by `test_scoring_empty`).
- **Grading / scope review (#030 / #019)** — the urgency-inflation issue: minor
  indices (PDW, Absolute Basophil Count) graded "Highly abnormal" push the
  verdict to "Urgent". A careful per-test `AssessmentPolicy` review, never a
  blanket change (Absolute Neutrophil Count lives in the same bucket, where a
  low value is a real emergency).
