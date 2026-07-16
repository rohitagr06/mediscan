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
messy real-world formats missed — HDL's descriptive wrapped range and
glucose's word-prefixed range (`Normal - 70 - 140,`).

**After the 8.9 parser fix** (a digit-free, bounded descriptive prefix before
the range + a consumer for units glued onto a one-sided range):

| Case | Recall | Parsed / Expected | False+ |
|---|---|---|---|
| clean_multipanel | 100% | 8/8 | 0 |
| real_world_messy (single-line) | 100% | 4/4 | 0 |
| real_world_multiline (real Tata HDL) | 0% | 0/1 | 0 |
| real_world_noise | — | 0/0 | 0 |
| **Overall** | **92%** | **12/13** | **0** |

**What the fix won, and what it did NOT.** Glucose-Random and the *single-line*
HDL format now parse (verified on the real Tata report — glucose appears in the
acknowledged section). But the REAL Tata HDL row reconstructs across TWO lines
(value on one, `<40mg/dL` range on the next), so it is STILL missed — captured
honestly by `real_world_multiline`. Fixing it needs cross-line range
association (#033), deferred: a miss is acceptable (HDL shows in 'could not
read'), a wrong value never is. Precision held at **0 false positives**
throughout — the noise case (real boilerplate + pregnancy table + marketing)
parses to zero.

## Grounding & confidence sanity (8.9b)

`python -m mediscan.evaluation` now also prints a grounding report from
`evaluation/grounding.py` — two pure, offline audits over a finished
AnalysisReport:

- **Hallucination** — the deterministic verdict is ground truth (#006), so the
  patient/doctor narratives must not introduce a NUMBER or a lab TEST NAME the
  results don't support. `find_ungrounded_numbers` flags any figure outside the
  grounded set (lab values, range bounds, structural counts); the diet/lifestyle
  notes are intentionally exempt (they carry non-lab quantities).
  `find_ungrounded_test_names` flags a policy test named in the narrative but
  absent from the report — conservative (word-boundary, and it skips a name that
  is a word inside a grounded name, e.g. "Urea" in "Blood Urea Nitrogen").
- **Confidence sanity** — `check_confidence_sanity`: every score in [0, 1]; zero
  parsed rows => zero overall (also locked by `test_scoring_empty`); overall
  never exceeds its own best component.

Proven with two synthetic cases: a faithful deterministic report (audits clean)
and a tampered copy that injects `999.0` and "PSA" (both caught).

## Grading / scope calibration (8.9, done)

The urgency-inflation issue is fixed in two layers. (1) Seven low-actionability
CBC indices (MCHC, RDW-CV, MPV, PDW, Absolute Mono/Eos/Baso Count) moved from
Tier A to Tier B — acknowledged, not graded — while Absolute NEUTROPHIL Count
stays graded (a low ANC is a real emergency). (2) The severity engine now caps
any UNSOURCED band (no cited critical threshold) at MODERATE / "Consult Soon":
URGENT/IMMEDIATE requires a real, sourced critical line (#034). Verified on the
real Tata report — the verdict drops from "Urgent" to "Consult a doctor soon".

## Still to do in this evaluation pass

- **Real-report accuracy (8.9c)** — run the app locally on the real Tata / Lal
  PathLabs / Labsmart PDFs; record only aggregate recall numbers here (never
  text, #010).
