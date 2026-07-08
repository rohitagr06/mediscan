# MediScan — Project Status

*Single source of truth for resuming across sessions. Cowork has no memory
between chats, so this file carries it. Read this FIRST every session.*

**Last updated:** 2026-07-08 (end of Sprint 4 + decision #023; Sprint 5 planned, not started)

---

## What MediScan is

"MediScan by DipsAI" — a production-grade, safety-first medical document
analyzer. A lab report (PDF/photo) goes in; a validated, explainable
analysis comes out. RC1 scope = English CBC-style lab reports. The core
rule: **everything that could harm if wrong (severity, urgency) is decided
by deterministic Python; AI only ever *explains* what the rules decided**
(decision #006).

- Repo: `/Users/rohit/Claude/Projects/Mediscan` · GitHub `rohitagr06/mediscan`
- Run tests: `uv run pytest` (from repo root, venv active)
- Full context lives in `docs/`: 00-product-brief, 01-architecture,
  02-repo-structure, 03-sprint-roadmap, 04-decision-log, 05-environment,
  06-reflections, 07-starter-playbook, 08/09/10/11 = sprint plans 2–5.

## How we work (standing agreements)

- **Pair mode:** Rohit writes core logic; Claude scaffolds, writes
  adversarial tests, reviews, unblocks. Rohit is a beginner — explain
  everything step by step (concept → why → steps → verification), in easy
  language, point-wise.
- **Review surface:** Rohit reviews every change via `git diff` on his Mac
  before committing. Claude delivers files via SendUserFile + writes them
  to the Mac via the device bridge.
- **⚠️ Device-bridge hazard:** staging sometimes serves STALE file copies.
  Before reviewing/editing Rohit's files, verify against live disk
  (checksum or `device_bash cat`), or bundle the live tree into one fresh
  file and stage that. Never overwrite his files from a stale read.
- **Cloud sandbox limits:** `pymupdf`/`paddleocr` are NOT installable in
  the cloud container (PyPI blocked), so OCR/integration tests that need
  them SKIP there — they run on Rohit's Mac. Run non-OCR tests with
  `PYTHONPATH=/usr/local/lib/python3.11/dist-packages:src /root/.local/bin/pytest`.

## Current position

**Sprints 0–4 are COMPLETE, including decision #023.** The deterministic
pipeline works end to end: document → parse → normalize → resolve ranges
→ severity → urgency → verdict, ZERO AI, fully tested. **Sprint 5 (the AI
explanation layer) is fully PLANNED in `docs/11-sprint-5-plan.md` but NOT
started.**

## This session's accomplishments

- Finished Sprint 4: severity engine (#020/#021), urgency roll-up (#022),
  exhaustive truth-table + adversarial tests, the 4.10 end-to-end
  integration test, and sprint-close docs.
- Fixed a fixture bug: `cbc_report.pdf` drew table cells separately so
  PyMuPDF extracted one token per line; regenerated it to one line per row.
- Full codebase review (added beginner comments/docstrings; hardened KB
  against NaN/Infinity; fixed an urgency wording bug where all-mild reports
  said "within normal limits").
- **Decision #023 implemented end to end** (the big one — see below).
- Planned Sprint 5 (`docs/11`).

## Key decisions (full log in docs/04; most relevant recent ones)

- **#006** Deterministic-first, AI-explains (never violated).
- **#011** No default confidence; unknown never masquerades as fine.
- **#018** Parser recognizes a row ONLY if it prints a two-sided positive
  reference range.
- **#020** Hybrid severity banding: Option B (fraction toward KB critical)
  where sourced criticals exist, else Option A (percentage), capped at
  HIGH — never invent CRITICAL.
- **#021** Medical engine is a pure function, never mutates input.
- **#022** Urgency = conservative graduated roll-up (worst finding wins;
  one Critical → Seek Immediate Care; un-assessable floors at Consult Soon).
- **#023 (this session)** When a report supplies its own range, keep it for
  banding but MERGE IN the KB's critical thresholds — only those strictly
  OUTSIDE the report range (conflicts dropped, report wins). Criticals now
  live in a `CriticalThresholds` value object with a DERIVED `source`;
  range provenance recorded separately (`reference_range_source`). Fixes an
  emergent gap where critically low values (e.g. Hb 3.0 in a printed 13–17
  range) could never reach CRITICAL. Engine stays 100% deterministic.

## Current state of code

- All source under `src/mediscan/`. Built & tested: config, full schema
  family, ingestion (validation/storage/secure temp), OCR (PyMuPDF +
  PaddleOCR + preprocessing + router + factory), extraction (parser +
  normalization), medical engine (ranges + severity + urgency + KB loader).
- Sprint-5 packages (`ai/`, `ai/providers/`, `safety/`, `prompts/`,
  `rag/`, `reports/`, `ui/`, `orchestration/`, `confidence/`) exist as
  EMPTY stubs — to be filled starting Sprint 5.
- Tests all green on Rohit's Mac after #023 (last sandbox run: 200 passed,
  1 skipped for the non-OCR subset; ruff clean).
- Knowledge base: `src/mediscan/knowledge_base/reference_ranges/cbc.json`
  — 5 CBC entries, but every `source` is still `"STARTER VALUE …"`.

## Open issues / blockers / homework (Rohit's to do)

1. **Confirm #023 green + commit:** run `uv run pytest` on the Mac
   (full suite incl. OCR), review the 11 #023 files via `git diff`, commit.
2. **KB sourcing (#019):** replace every `"STARTER VALUE"` in `cbc.json`
   with a real cited source BEFORE any clinical use. Blocks real use.
3. **Sprint-4 architecture reflection exercise:** 5 sentences on why
   severity must be deterministic (#006 in his own words), in docs/06.
4. Minor/nominal: Sprint-0 "break the CI" exercise still open.

No hard blockers for starting Sprint 5.

## Exact next steps (to resume)

1. Confirm #023 is committed and green (item 1 above).
2. Start **Sprint 5, task 5.1** from `docs/11-sprint-5-plan.md`: add the AI
   API keys to `config.py` as `SecretStr` (`gemini_api_key`,
   `github_models_token`) plus bounded AI knobs (timeout, retries,
   temperature, model IDs), and update `.env.example`. Rohit has BOTH a
   Gemini free-tier key and a GitHub Models token.
3. Then proceed 5.2 → 5.12 in order (contract → prompts → structured output
   → providers → resilient chain → deterministic templates → guardrail →
   assemble 4 outputs → tests → close).

**Sprint 5 confirmed choices:** full Gemini → GPT-4.1-mini → Phi-4 →
deterministic chain; AI generates all four outputs (patient, doctor,
dietary, specialist); fallback = deterministic template summary.

**SDKs (verify current at build):** `google-genai` (`from google import
genai`) for Gemini; `openai` SDK pointed at the GitHub Models endpoint for
both GitHub fallbacks.
