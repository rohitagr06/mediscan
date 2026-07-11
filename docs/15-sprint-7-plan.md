# Sprint 7 Plan — Confidence, Orchestration & Explainability

*Mode: PAIR (Rohit writes core logic; Claude scaffolds, explains every line at
beginner level, writes adversarial tests, reviews). This sprint turns the
pile of well-built, independently-tested stages into ONE machine: a single
call that takes a document and returns a complete, validated, explained
`AnalysisReport` — and it retires the two pieces of technical debt the Sprint
6.5 code review flagged.*

**Milestone:** `analyze_document(path) -> AnalysisReport` — one call runs the
whole pipeline end to end (ingest → OCR/extract → parse → read sex → coverage
→ severity → urgency → RAG-grounded AI explanations per abnormal finding →
guardrail → confidence) and returns the master schema object, fully populated
and validated. It runs concurrently where safe, times out cleanly, logs
events (never PHI), and STILL produces a complete deterministic report when
every AI model is down.

---

## Scope locked for this sprint (decided with Rohit)

- **Core + both review add-ons.** The roadmap core (confidence scoring, async
  orchestration, per-finding explanation assembly) PLUS the two items the
  review deferred here: the composable-recognizer **parser refactor** and the
  **persisted RAG index**.
- **Sync wiring first, then asyncio.** We assemble the whole pipeline
  *synchronously* and get one-call → `AnalysisReport` working and tested
  FIRST (Phase A). Only then do we layer in asyncio concurrency, timeouts, and
  cancellation (Phase B). Lower risk, and it keeps the async lesson separate
  from the wiring lesson.

This is a bigger sprint than 6.5. If it runs long, the natural cut line is to
ship Phase A + confidence + explainability (a complete synchronous product),
and move the async phase and/or the two add-ons into a Sprint 7.5 — we decide
at the 7.1 checkpoint, not now.

---

## First, the plain-English concepts (read before any code)

**1. Orchestration = the conductor.** Every stage already works alone. The
orchestrator is the conductor that calls them in order and hands each one the
typed object the next expects: bytes → `PageText` → `ParseOutcome` →
`CoverageResult` → assessments → `UrgencyAssessment` → explanations →
`AnalysisReport`. It owns no medical logic — it only wires. That's why it can
be added last without touching any stage.

**2. Confidence is a blend, never one number (#011).** "How much should you
trust this report?" is not one thing. It's a weighted mix of: OCR quality
(did we read the pixels well?), extraction method (rules > LLM), schema
validation success, whether AI explanations were RAG-grounded, and how deep
the fallback chain went (did the primary model answer, or the last rung?).
A single naive number would hide *why* confidence is low. The schema
(`ConfidenceBreakdown`) already has the fields; this sprint fills them.

**3. An explanation CHAIN per abnormal finding.** Today `explain_report`
produces the four grounded outputs (patient / doctor / dietary / specialist)
for the report. This sprint assembles them *per abnormal finding* and attaches
them — with each output's `grounding_sources` and provenance — into a
`ReportExplanations` block on the `AnalysisReport`. Normal findings are not
explained (bounds cost and noise); only what's abnormal earns an explanation.

**4. Async concurrency (Phase B).** The per-finding explanation chains and
their RAG retrievals are INDEPENDENT — finding A's explanation doesn't need
finding B's. Running them one-by-one wastes wall-clock; `asyncio.gather` runs
them together. Async also gives us real **timeouts** (a hung provider can't
freeze the whole report) and **cancellation** (if the caller gives up, in-
flight work stops cleanly). The pure-function engine (#021) makes this safe:
no shared mutable state, so no data races.

**5. Composable-recognizer parser (add-on).** `parser.py` grew one regex
grammar that now carries every real-report special case (thousands-commas,
method columns, pre-flags). The refactor replaces the monolith with small,
independently-testable *recognizers* (name, value, unit, range, flag) composed
behind the SAME `parse_lab_text` contract — behavior-preserving, every
existing parser test still green.

**6. Persisted RAG index (add-on).** Today the ChromaDB index is rebuilt from
the KB files on every process start (#028). That's fine for 38 tests but
wasteful as the KB grows. We persist the built index to a cache, keyed by a
HASH of the KB content, and rebuild only when that hash changes — so a stale
index is impossible by construction, and startup gets cheap.

---

## What already exists vs what's new

**Exists and stays untouched in logic:** ingestion, OCR, extraction, the whole
deterministic medical engine (parser behavior, coverage, severity, urgency),
the AI layer (chain, providers, templates, guardrail), RAG retrieval, the
observability foundation from the 6.5 review, and the full `schemas/` family
(`AnalysisReport`, `ConfidenceBreakdown`, `ProcessingMetadata`,
`ReportExplanations` are already defined and tested).

**New code this sprint:** `confidence/` (the blend), `orchestration/` (the
conductor, sync then async), the per-finding explanation assembly, the parser
recognizer split, and the persisted-index layer in `rag/`.

---

## The safety spine (unchanged, restated because it constrains every task)

- **#006 stays absolute.** The orchestrator NEVER lets AI touch severity or
  urgency. It calls the deterministic engine, gets the verdict, and only then
  asks AI to *explain* it. If AI is down, the report is still complete.
- **Confidence is deterministic.** No AI decides how much to trust the report.
- **No PHI in logs or the index cache.** Logs are events/metrics only (6.5
  foundation). The persisted index contains only KB snippets — public,
  sourced, never patient data (#010).
- **Async adds no data races.** Only pure functions (#021) run concurrently;
  nothing shared is mutated.

---

## Open questions to confirm at 7.1 (before coding)

1. **Confidence weights.** Starting weights for the blend (OCR / extraction /
   validation / grounding / fallback-depth)? Propose sensible defaults in
   config, tune in Sprint 8 evaluation. **Leaning:** equal-ish with a heavier
   weight on extraction method and validation.
2. **Async API shape.** Async core with a thin sync wrapper (`analyze_document`
   calls `asyncio.run` on `analyze_document_async`), or async-only? **Leaning:**
   async core + sync wrapper, so callers and tests can use either.
3. **Persisted index location.** A cache dir (e.g. `~/.cache/mediscan/` or a
   configurable path) keyed by KB-content hash — NOT inside the package (built
   wheels stay clean). **Leaning:** configurable cache path, hash-keyed.
4. **Explanation breadth.** Explain every abnormal finding, or cap at the top-N
   most severe to bound token cost? **Leaning:** all abnormal, but behind a
   config cap so a 30-abnormal report can't explode cost.

---

## Tasks

### 7.1 — Kickoff + design the assembly contract — OWNER: pair (~1.5h)

**What:** Concept session on orchestration + async; lock the four open
questions above; sketch the exact shape of `analyze_document` and how a
`CoverageResult` + per-finding explanations + confidence compose into
`AnalysisReport`. **Why:** the wiring touches every layer — an agreed contract
prevents rework. **Done when:** the open questions are answered and the
`AnalysisReport` assembly shape is written down.

### 7.2 — Confidence scoring engine — OWNER: Rohit core + Claude tests (~2.5h)

**What:** `confidence/` module: a pure function that takes the run's signals
(OCR confidence, extraction method per result, validation outcomes, grounding
presence, fallback depth) and returns a populated `ConfidenceBreakdown` with a
weighted `overall`. Weights live in config (#020 pattern). **Why:** trust must
be explainable and deterministic (#011). **Safety note:** no defaults that
fake confidence — an unscored dimension is explicit, never silently 1.0.
**Done when:** each dimension maps to a tested rule; a low-OCR / deep-fallback
run scores visibly lower than a clean one.

### 7.3 — Per-finding explanation assembly — OWNER: pair (~2.5h)

**What:** For each ABNORMAL assessed finding, build its FACTS, run the
existing grounded explanation path (patient/doctor/dietary/specialist), and
collect the results — each with `grounding_sources` + provenance — into a
`ReportExplanations` block. Respect the config cap (open Q4). **Why:** this is
the "explainability" half of the sprint — every abnormal finding gets a
traceable, grounded explanation. **Safety note:** guardrail (#026) runs on
every AI string; a trip falls back to the deterministic template. **Done
when:** an abnormal CBC finding yields a grounded patient+doctor explanation
with sources; a normal finding yields none.

### 7.4 — Synchronous orchestrator (Phase A) — OWNER: pair (~3h)

**What:** `orchestration/`: `analyze_document(path) -> AnalysisReport` running
every stage in order, synchronously, assembling the master object incl.
`ProcessingMetadata` (timings, models used, fallback count), confidence, and
explanations. **Why:** the milestone — one call, whole pipeline. **Safety
note:** the deterministic verdict is computed and assembled BEFORE AI is
called; an AI failure downgrades explanations to templates but never blocks
the report. **Done when:** a real text-PDF fixture → a complete, validated
`AnalysisReport` in one call, AI on and AI off.

### 7.5 — End-to-end integration tests (sync) — OWNER: Claude (~2h)

**What:** document → full `AnalysisReport` for both the deterministic path (AI
disabled) and the AI path (fake provider); assert urgency, coverage split,
confidence, and explanations are all present and consistent. **Why:** proves
the whole machine, offline. **Done when:** both paths green in the fast suite.

### 7.6 — Async orchestration (Phase B) — OWNER: Rohit core + Claude tests (~3h)

**What:** `analyze_document_async`: run the independent per-finding
explanation chains (and their retrievals) concurrently with `asyncio.gather`;
add per-step timeouts and cancellation safety; keep the sync wrapper. **Why:**
concurrency + timeouts are the roadmap's async learning goal and cut latency.
**Safety note:** only pure functions run concurrently (#021); a per-finding
failure or timeout degrades THAT finding to a template, never sinks the
report. **Done when:** N findings explain concurrently, a slow provider hits
its timeout, and one failing finding leaves the rest intact.

### 7.7 — Concurrency adversarial tests — OWNER: Claude (~2h)

**What:** timeouts fire and are recorded; cancellation stops in-flight work
cleanly; one raising finding doesn't crash the gather; result ordering is
stable. **Why:** async bugs are silent and nasty. **Done when:** all hold with
injected fake delays/failures, offline.

### 7.8 — Parser: composable-recognizer refactor — OWNER: Rohit core + Claude adversarial (~3h)

**What:** replace the monolithic regex grammar with small composable
recognizers (name / value / unit / range / flag), composed behind the
UNCHANGED `parse_lab_text` contract. **Why:** retire the accreting-regex risk
before it grows (review WARNING). **Safety note:** BEHAVIOR-PRESERVING —
every existing parser test and all three real-report fixtures must stay green;
no new formats accepted, none dropped. **Done when:** the full parser suite +
real-fixture validation pass unchanged, with the grammar now modular.

### 7.9 — Parser refactor validation — OWNER: pair (~1h)

**What:** run the refactored parser against Tata/Lal/Labsmart + synthetic
fixtures; diff row-by-row against the pre-refactor output. **Why:** prove zero
regression. **Done when:** identical parse results before/after.

### 7.10 — Persisted RAG index + invalidation — OWNER: Rohit core + Claude tests (~2.5h)

**What:** persist the built ChromaDB index to a configurable cache keyed by a
hash of the KB files; on startup, load if the hash matches, else rebuild and
re-cache. Keep the injectable embedder and the `medical/`⊬`rag/` boundary.
**Why:** kill rebuild-per-process as the KB grows (review SUGGESTION); a
content-hash key makes a stale index impossible. **Safety note:** the cache
holds only public KB snippets, never PHI (#010). **Done when:** a warm start
loads without rebuilding; editing a KB file forces a rebuild; the offline fake
path is unchanged.

### 7.11 — Persisted index tests — OWNER: Claude (~1.5h)

**What:** cold-build vs warm-load; invalidation on KB change; corrupt/missing
cache falls back to a clean rebuild (never a crash). **Done when:** all green,
offline, with a temp cache dir.

### 7.12 — Wire observability through the pipeline — OWNER: pair (~1.5h)

**What:** use the 6.5 logging foundation across the orchestrator: log stage
latencies, fallback depth, guardrail trips, and final confidence — events and
metrics ONLY. Call `configure_logging()` at the entry point. **Why:** cash in
the observability foundation on the one path that now runs everything. **Safety
note:** never log report text, values, or model output (#010). **Done when:** a
run emits a clean, PHI-free event trail; a test asserts no PHI in the records.

### 7.13 — Tests throughout + coverage ratchet — OWNER: split (~2h)

**What:** fill gaps across confidence, assembly, orchestration, parser,
persisted index; raise the CI coverage floor now that it's measured (set an
honest `--cov-fail-under`). **Why:** lock the new surface. **Done when:** fast
suite green + a coverage gate that reflects reality.

### 7.14 — Sprint close — OWNER: Rohit (~1h)

**What:** log decisions (#031 confidence blend; #032 sync-then-async
orchestration + timeouts/cancellation; #033 composable-recognizer parser;
#034 persisted hash-keyed index); roadmap Sprint 7 ✅; architecture banner →
end of Sprint 7 (orchestration + confidence now BUILT); Sprint 7 reflection;
README status; `project-status.md`; confirm CI green. **Done when:** docs match
reality and a fresh session could resume from `project-status.md`.

---

## Cross-cutting: security, scalability, production-readiness

- **Security/PHI:** logs and the index cache are PHI-free by construction;
  `configure_logging` at the entry point, `get_logger` everywhere else.
- **Scalability:** async concurrency + persisted index are exactly the two
  levers that let this scale to bigger reports and a bigger KB without a
  rewrite — the reason they're in this sprint.
- **Production-readiness:** after this sprint MediScan has a real entry point,
  structured observability, measured coverage, and dependency/secret scanning
  (from the 6.5 review) — the remaining gap to RC1 is presentation (UI + PDF)
  and the Sprint-8 evaluation/deploy pass.

## Explicitly deferred (NOT this sprint)

- Gradio UI + WeasyPrint PDF + HF Spaces deploy + evaluation pass → **Sprint 8**.
- LangGraph / agent-framework migration → **RC2** (raw async first, #arch).
- Age-specific ranges (the sex block generalizes to a demographic key, #029) →
  RC2.
- KB sourcing review (#019) remains a clinical-use gate tracked separately.

---

## Appendix A — 7.1 assembly contract (LOCKED)

*Decided with Rohit at kickoff. This is the contract every later task builds
to. Grounded in the ACTUAL schemas, not the sketch.*

### The three forks (locked)

- **A1 — Explanations are REPORT-LEVEL for RC1.** The `AnalysisReport` schema
  already holds one `patient_summary`, one `doctor_summary`, and lists of
  `dietary_considerations` / `specialist_suggestions`. We keep that shape and
  ground those summaries across ALL abnormal findings. Per-finding explanation
  blocks are an RC2 enhancement — no schema churn now. (The 7.3 task title
  "per-finding chain" is downgraded to "report-level assembly grounded across
  abnormal findings".)
- **A2 — Add a coverage surface to the report.** One additive, optional field:
  `coverage: CoverageResult | None` on `AnalysisReport`. This carries the
  Sprint-6.5 split (assessed / acknowledged / unparsed) into the final output,
  so acknowledge-don't-skip holds end to end. `lab_results` stays as the raw
  extracted audit rows; `coverage` carries the interpretation. This is the
  ONLY schema change the sprint needs.
- **A3 — Async core + sync wrapper.** `analyze_document_async(...)` is the real
  function; `analyze_document(...) = asyncio.run(analyze_document_async(...))`.
  Phase A builds the async-shaped code but calls everything sequentially;
  Phase B makes the independent per-finding work concurrent.

### Default decisions (my leanings, locked unless you object)

- **Confidence blend (7.2).** `overall = w_ocr·ocr + w_ext·extraction +
  w_val·validation + w_ground·grounding`, then a fallback penalty
  `overall *= max(floor, 1 − k·fallback_depth)`. Default weights in config:
  ocr 0.25, extraction 0.30, validation 0.25, grounding 0.20 (sum 1.0);
  penalty k 0.10, floor 0.5. All tunable, all in config (#020 pattern).
- **Explanation cap (7.3).** Config `max_explained_findings` (default 12),
  most-severe-first, so a 30-abnormal report can't explode token cost.
- **Persisted index (7.10).** Cache at a configurable path (default
  `~/.cache/mediscan/rag_index`), keyed by a SHA-256 of the KB JSON files;
  mismatch → rebuild + re-cache. Cache holds only public KB snippets (#010).

### The pipeline order (what fills each AnalysisReport field)

```
analyze_document_async(path) ->
  1. validate_upload(path)                 -> DocumentType            [ingestion]
  2. store + extract text (factory/router) -> full_text, ocr_conf     [ocr]
       -> metadata.ocr_engine, confidence.ocr
  3. parse_lab_text(full_text)             -> ParseOutcome            [extraction]
       -> AnalysisReport.lab_results (raw audit rows)
  4. extract_patient_context(full_text)    -> sex                     [extraction]
  5. classify_coverage(outcome, sex)       -> CoverageResult          [medical]
       -> AnalysisReport.coverage            (NEW field, A2)
  6. assess_urgency(coverage.assessed)     -> UrgencyAssessment       [medical]
       -> AnalysisReport.urgency             (assessed ONLY — #006)
  7. explain (abnormal assessed findings)  -> summaries + lists       [ai + rag]
       guardrail each string; record provenance + grounding_sources
       -> patient_summary, doctor_summary, dietary_*, specialist_*
       -> metadata.models_used, metadata.fallback_count
       *** this is the concurrent step in Phase B ***
  8. score_confidence(signals)             -> ConfidenceBreakdown     [confidence]
       -> AnalysisReport.confidence
  9. metadata.duration_ms = elapsed; disclaimer defaulted
  -> validated AnalysisReport
```

**Invariants the orchestrator must uphold:** the deterministic verdict (steps
3–6) is complete BEFORE any AI runs (step 7); AI failure/timeout degrades
step 7 to templates but never blocks steps 1–6, 8–9; only `coverage.assessed`
reaches urgency; nothing but events/metrics is logged.

**Done-when (7.1):** ✅ forks locked (A1–A3), defaults set, pipeline order +
the single schema change (`AnalysisReport.coverage`) written down. Ready for
7.2.
