# MediScan — Project Status

*Single source of truth for resuming across sessions. Cowork has no memory
between chats, so this file carries it. Read this FIRST every session.*

**Last updated:** 2026-07-09 (Sprint 5 COMPLETE — AI explanation layer built, tested, verified live)

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
- **⭐ EXPLAIN THE CODE ITSELF (Rohit is a Python BEGINNER).** Never hand
  over a code block with only a one-line "why". For EVERY snippet, explain
  how it works at beginner level: what each new construct means (decorator,
  NamedTuple, lazy import, try/except/from, for/else, comprehension, `@cache`,
  generics, etc.), why the line is written that way, and what would break
  without it. Even when Rohit delegates ("you write it"), still explain the
  code fully so he UNDERSTANDS what he's typing — never just copies it. This
  drifted during Sprint 5's fast pace; Rohit corrected it. Do not drift again.
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

**Sprints 0–5 are COMPLETE.** Deterministic pipeline: document → parse →
normalize → resolve ranges (KB criticals merged, #023) → severity →
urgency, zero AI. AI explanation layer (Sprint 5): one medicine-blind
`LLMClient` contract; ONE `OpenAICompatibleProvider` driving Gemini +
GitHub Models via the openai SDK (#024 — Rohit's design); versioned
PromptTemplates with injection fencing (#025); structured output with one
repair-retry; resilient chain with backoff; deterministic template floor;
regex guardrail block-and-fall-back (#026); ExplanationProvenance on every
output. All verified LIVE (all four outputs via gemini-2.5-flash). 240
tests passing on Rohit's Mac. Working agreement: EVERY task ends with git
sync instructions (add/commit/push).

## This session's accomplishments

- Closed Sprint 4 (#020–#023) and executed ALL of Sprint 5 (tasks 5.1–5.12):
  secrets in config, LLMClient contract, versioned PromptTemplates,
  structured output + repair-retry, unified OpenAI-compatible provider
  (Rohit's one-SDK insight, #024), resilient chain, deterministic
  templates, guardrail, assembly with provenance, mock-first test suite
  (happy + adversarial), sprint-close docs (#024–#026).
- Survived a real Gemini 429 on first live call — switched model to
  gemini-2.5-flash; the error normalization worked as designed.
- Each task committed + pushed individually (new standing rule: every task
  ends with git sync instructions).

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
- AI layer (Sprint 5) BUILT: `schemas/ai.py` (LLMRequest/LLMResponse/
  ExplanationProvenance), `ai/base.py` (LLMClient ABC), `ai/exceptions.py`
  (LLMError, AllProvidersFailed), `ai/prompts.py` (4 versioned templates),
  `ai/structured.py` (validate + one repair), `ai/providers/
  openai_compatible.py` (one class, 3 builders), `ai/chain.py`
  (backoff fallback), `ai/templates.py` (deterministic floor),
  `ai/explain.py` (assembly), `safety/guardrail.py` (regex block).
  Still-empty stubs: `rag/`, `reports/`, `ui/`, `orchestration/`,
  `confidence/`.
- Tests: 240 passed / 2 deselected on Rohit's Mac (incl. 14 AI-layer
  tests, all mock-first — no keys/network needed).
- Knowledge base: `src/mediscan/knowledge_base/reference_ranges/cbc.json`
  — 5 CBC entries, but every `source` is still `"STARTER VALUE …"`.

## Open issues / blockers / homework (Rohit's to do)

1. **KB sourcing (#019):** replace every `"STARTER VALUE"` in `cbc.json`
   with a real cited source BEFORE any clinical use. Blocks real use.
2. **Architecture reflection exercises:** Sprint-4 (why deterministic
   severity) and Sprint-5 (why validate+guardrail despite a careful
   prompt) — 5 sentences each in docs/06.
3. Minor/nominal: Sprint-0 "break the CI" exercise still open.

No hard blockers for starting Sprint 6.

## Exact next steps (to resume)

1. Rohit commits the Sprint-5 close docs (04/01/03/06 + project-status.md)
   and confirms CI green — the last step of task 5.12.
2. Then plan **Sprint 6 — RAG & the Knowledge Base** (roadmap outline:
   curated KB content, ChromaDB + BGE-small embeddings, retrieval into the
   existing 5.3 prompt seam — only WHERE facts come from changes).
3. RC2/parked notes: honor 429 retryDelay in the chain; wire
   ReportExplanations into AnalysisReport (Sprint 7 orchestration);
   BandingPolicy; tuple returns; frozen models (#013).

**Gemini note:** free tier worked with model `gemini-2.5-flash`
(gemini-2.0-flash had limit 0). Both keys live in Rohit's .env.
