# MediScan — Project Status

*Single source of truth for resuming across sessions. Cowork has no memory
between chats, so this file carries it. Read this FIRST every session.*

**Last updated:** 2026-07-15 (Sprint 8: 8.1–8.6 in progress + a MAJOR real-PDF fix. 8.3/8.4 = WeasyPrint HTML→PDF rendering (#035); 8.5 = Gradio app skeleton with the testable `analyze()` seam (#036). **MILESTONE: the app reads a REAL report.** A real Tata 1mg 15-page PDF went from `assessed=0` (parser saw a column-major text stream) to `assessed=33 acknowledged=22` after switching PyMuPDF to WORD-GEOMETRY row reconstruction (`ocr/_rows.py`, `reconstruct_lines`); every value stayed matched to its OWN range; confidence now collapses to 0 when nothing parses (`parsed_count` in scoring). 8.6 = result-rendering polish: shared `medical/phrasing.py::describe_finding` fixed the confusing 'X is high (low) at …' wording (now 'Creatinine is mildly elevated at 1.33') across BOTH urgency reasons and template summaries; chain.py no longer logs ERROR when demo mode passes 0 providers. Commits through ec8b49f (8.6 pending commit). Suite: 444 passing + new phrasing tests. Next: finish 8.6 commit, then **8.7 — demo mode + deploy config**. Parser/scope refinements catalogued below for **8.9 (evaluation)**.)

---

## Session protocol (Cowork has no cross-chat memory — follow this every time)

- **START of every session:** read THIS file (and any core docs the task needs)
  BEFORE anything else, then confirm the current state back to Rohit in 2–3
  sentences before starting new work.
- **END / "wrap up" / "end session" / nearing usage limit:** immediately update
  this file before stopping, covering: (a) what we accomplished, (b) key
  decisions + why, (c) current state of files/code touched, (d) open issues /
  blockers, (e) exact next steps to resume. Concise but complete enough for a
  zero-memory session to pick up seamlessly. (Map: "accomplishments" = a,
  "Key decisions" = b, "Current state of code" = c, "Open issues" = d,
  "Exact next steps" = e.)
- **Scope:** load only the folders/connectors the task needs — nothing extra.
- **Brevity:** reference this file; don't re-explain context already written here.
- **Model choice:** lightest capable model for routine/mechanical work; reserve
  the strongest for genuinely complex reasoning or coding.

---

## ✅ Sprint 7 — Confidence, Orchestration & Explainability (COMPLETE)

*Full plan: `docs/15-sprint-7-plan.md`. Milestone MET:
`analyze_document(path) -> AnalysisReport` — one call runs the whole pipeline,
still complete when every AI model is down.*

**What Sprint 7 built (all committed):**

- **The orchestrator** (`orchestration/pipeline.py`): `analyze_text` (testable
  core: text → report, all deps injectable) + `analyze_document` (thin OCR
  front, lazy imports). Order: parse → sex → `classify_coverage` → urgency
  (assessed ONLY, #006) → explanations → confidence → assembled `AnalysisReport`.
  Built SYNC first (7.4/7.5), then made ASYNC: the four explanation outputs run
  CONCURRENTLY in a thread executor with per-output `wait_for` timeouts and
  per-output template fallback (#032); public API = async core + sync wrapper.
- **Confidence engine** (`confidence/scoring.py`, #031): deterministic weighted
  blend + fallback penalty; weights in config with a sum-to-1 startup guard.
- **Schema change:** `AnalysisReport.coverage: CoverageResult | None` surfaces
  the assessed/acknowledged split end to end (7.1 decision A1; explanations stay
  REPORT-LEVEL, not per-finding).
- **Explanation assembly** (`ai/explain.py`): `assemble_report_explanations[_async]`
  selects noteworthy, most-severe-first, capped (`max_explained_findings`) findings.
- **Add-ons:** parser decomposed into named recognizers, behaviour-preserving
  (#033); RAG index PERSISTED + hash-keyed with prune + corrupt-cache rebuild (#034).
- **Observability** wired through the pipeline (stage counts, fallback depth,
  duration — metrics only, PHI-safe; a test asserts no PHI in any log record).
- **CI:** 90% coverage gate (`--cov-fail-under=90`; measured baseline 92%).

**Decisions logged:** #031 (confidence blend), #032 (sync-then-async orchestration
+ executor timeouts), #033 (composable-recognizer parser), #034 (persisted
hash-keyed RAG index). Full text in docs/04.

**Before Sprint 7 this session also did** a Staff-level code review (clean, no
criticals) + post-review hardening: the `observability/` module, CI security
(pip-audit, gitleaks job + hook, Dependabot), docstring/scaffold fills.

---

## What MediScan is

"MediScan by DipsAI" — a production-grade, safety-first medical document
analyzer. A lab report (PDF/photo) goes in; a validated, explainable
analysis comes out. **RC1 scope (revised, #027): a full-body health
checkup for BOTH sexes — CBC, KFT, lipid profile, electrolytes, vitamins,
diabetes/HbA1c, thyroid, numeric urine — NOT just CBC.** (The deterministic
engine today only handles CBC; the full-panel expansion is Sprint 6.5. The
RAG layer is already panel-agnostic — the KB is data.) The core rule:
**everything that could harm if wrong (severity, urgency) is decided by
deterministic Python; AI only ever *explains* what the rules decided**
(decision #006).

- Repo: `/Users/rohit/Claude/Projects/Mediscan` · GitHub `rohitagr06/mediscan`
- Run tests: `uv run pytest` (fast suite) · `uv run pytest -m slow` (real models)
- Full context lives in `docs/`: 00-product-brief, 01-architecture,
  02-repo-structure, 03-sprint-roadmap, 04-decision-log, 05-environment,
  06-reflections, 07-starter-playbook, 08/09/10/11 = sprint plans 2–5,
  12-understanding-the-codebase, 13-sprint-6-plan, 14-sprint-6.5-plan,
  15-sprint-7-plan.

## How we work (standing agreements)

- **Pair mode:** Rohit writes core logic; Claude scaffolds, writes
  adversarial tests, reviews, unblocks. Rohit is a beginner — explain
  everything step by step (concept → why → steps → verification), in easy
  language, point-wise.
- **⭐ EXPLAIN THE CODE ITSELF (Rohit is a Python BEGINNER).** Never hand
  over a code block with only a one-line "why". For EVERY snippet, explain
  how it works at beginner level: what each new construct means (decorator,
  NamedTuple, lazy import, try/except, comprehension, `@cache`, `dict.fromkeys`
  dedupe, AST walk, etc.), why the line is written that way, and what would
  break without it. Even when Rohit delegates ("you write it"), still explain
  the code fully so he UNDERSTANDS what he's typing — never just copies it.
- **Every task ends with git sync instructions** (`git add ... && commit && push`).
- **Review surface:** Rohit reviews every change via `git diff` on his Mac
  before committing. Claude delivers files via SendUserFile + writes them
  to the Mac via the device bridge.
- **⚠️ Device-bridge hazard (HARD RULE after the Sprint-8.2 incident):**
  staging/reading sometimes serves STALE file copies — even a fresh
  `device_stage_files` call. Before writing back an EDITED version of any
  existing repo file, Claude MUST first verify the base copy matches live
  disk (`device_bash cat/sed` the real file, or diff against a known-live
  version). Never overwrite from an unverified read. (Bit us in Sprint 6:
  stale `embedding.py`. Bit us HARD in Sprint 8.2: a stale `pyproject.toml`
  was edited + written back, gutting uv.lock in commit ae4da8c — recovered
  in 9cf82ad with `git checkout ae4da8c~1 -- pyproject.toml uv.lock`.)
- **Cloud sandbox limits:** `pymupdf`/`paddleocr`/`chromadb`/`sentence-
  transformers` are NOT installable in the cloud container (PyPI blocked),
  so OCR + real-index tests SKIP/can't run there — they run on Rohit's Mac.
  Chromadb-FREE logic (schema, chunking, grounding wiring, the AST boundary
  test) is verifiable in the sandbox. Run non-OCR tests with
  `PYTHONPATH=/usr/local/lib/python3.11/dist-packages:src /root/.local/bin/pytest`.

## Current position

**Sprints 0–7 are COMPLETE.** ONE call now runs everything:
`analyze_document(path) -> AnalysisReport` (orchestration/pipeline.py, #032).
Deterministic pipeline: document → read
patient sex → parse (two-sided AND one-sided ranges) → normalize → resolve
ranges (sex-aware KB fallback, KB criticals merged, #023/#029) → **classify
coverage (assessed vs acknowledged, #030)** → severity → urgency, zero AI.
AI explanation layer (Sprint 5): one medicine-blind `LLMClient` contract; ONE
`OpenAICompatibleProvider` driving Gemini + GitHub Models via the openai SDK
(#024); versioned PromptTemplates with injection fencing (#025); structured
output + one repair-retry; resilient chain with backoff; deterministic template
floor; regex guardrail (#026); ExplanationProvenance on every output. RAG layer
(Sprint 6, #028): a curated sourced KB → chunked snippets → local BGE-small
embeddings (real in prod, injectable fake in tests) → in-memory ChromaDB
rebuilt from files → bounded retriever → grounding wired into the Sprint-5
FACTS seam → `grounding_sources` on every AI explanation. The `medical/` engine
is forbidden from importing `rag/`, proven by an AST boundary test. **Sprint
6.5 widened the engine from CBC to a full-body checkup (CBC, KFT, lipids,
glucose/HbA1c, thyroid) for both sexes; out-of-scope and sensitive tests are
acknowledged but never graded.** **Sprint 7 assembled it all into the
orchestrator, added a deterministic confidence blend (#031), ran the AI
explanations concurrently with timeouts (#032), decomposed the parser (#033),
persisted the RAG index (#034), and wired PHI-safe observability.** Suite:
413 passing on Rohit's Mac (incl. OCR + real-BGE), 92% coverage; CI enforces a
90% floor.

## This session's accomplishments (Sprint 6.5)

- 6.5.2–6.5.4 — parser learns ONE-SIDED ranges (`< 100`, `> 40`, `< 5.7 %`)
  and survives real Tata/Lal/Labsmart report formats (thousands-commas,
  trailing method column, pre-flags); `extraction/metadata.py` reads the
  patient's SEX + age from the header; sex-aware + one-sided range resolution
  (`resolve_reference_range(result, sex)`), union fallback for unknown sex.
- 6.5.5–6.5.7 — `RangeBounds` value object + sex-aware `ReferenceRangeEntry`
  (`male`/`female` blocks); one-sided severity banding via `None` guards; the
  coverage split — `AssessmentPolicy` (Tiers A/B/C) kept SEPARATE from the KB,
  `classify_coverage` → `CoverageResult` (assessed/acknowledged/unparsed),
  only assessed feed urgency (#030).
- 6.5.8–6.5.9 — the multi-panel sourced KB grew to **38 tests** across
  reference_ranges + test_knowledge (CBC-22, lipids, glucose, thyroid, KFT),
  MedlinePlus/standards-cited, sex-aware where real reports gave the numbers.
- 6.5.10 — **KB integrity checks:** `load_test_knowledge()`, policy-name
  helpers, and `test_kb_integrity.py` catch cross-layer drift (a Tier-A test
  missing a range/knowledge entry, an orphan KB entry, a non-canonical name/
  unit, a duplicate) with a clear message.
- 6.5.11 — synthetic full-panel fixture (male + female) + an end-to-end
  coverage integration test: the same 12.5 Hb bands LOW for male / NORMAL for
  female, one-sided lipids band correctly, out-of-scope tests acknowledged.
- 6.5.12 — adversarial coverage tests: a scary ACKNOWLEDGED value (PSA at 50×)
  cannot move urgency (#006 boundary); sex threads through `classify_coverage`
  into the KB fallback (male→low, female→normal, unknown→union).
- 6.5.13 — sprint close: decisions #029 + #030, roadmap Sprint 6.5 ✅,
  architecture banner → end of Sprint 6.5, README status, Sprint 6.5
  reflection, this file.

## Key decisions (full log in docs/04; most relevant recent ones)

- **#006** Deterministic-first, AI-explains (never violated — RAG feeds the
  AI layer ONLY, never the engine).
- **#023** Report range kept for banding, KB criticals merged in.
- **#024** One openai SDK + one provider class for Gemini + GitHub Models.
- **#025** Versioned PromptTemplates + provenance on every output.
- **#026** Deterministic block-and-fall-back guardrail.
- **#027** RC1 scope = full-body checkup, both sexes (engine expansion = 6.5).
- **#028** RAG built now on the CBC KB, feeding AI only: ChromaDB + local
  BGE-small, in-memory index rebuilt from files, injectable embedder (+ fake
  for offline tests), grounding into the FACTS seam, `grounding_sources`
  traceability, `medical/`⊬`rag/` enforced by a test.
- **#029 (this session)** Sex-aware + one-sided range resolution: parser reads
  one-sided ranges; patient sex read from the report; report-first still wins
  (#023), sex only steers the KB fallback; UNKNOWN sex → union of both sexes
  (widest band); one-sided banding never invents a direction.
- **#030 (this session)** Scope tiers + acknowledge-don't-skip: an explicit
  `AssessmentPolicy` (Tiers A/B/C) kept SEPARATE from the medical KB decides
  what gets graded; `classify_coverage` splits every test into assessed /
  acknowledged / unparsed; only assessed feed urgency, so a sensitive or
  out-of-scope value can never move the verdict; KB integrity checks guard the
  policy↔KB coupling.

## Current state of code

- All source under `src/mediscan/`. Built & tested: config, full schema
  family, ingestion, OCR, extraction, deterministic medical engine, AI
  explanation layer, and `rag/`.
- Sprint 6.5 additions: `extraction/metadata.py` (`extract_patient_context` →
  `PatientContext`), `schemas/patient.py` (`Sex`, `PatientContext`),
  `schemas/coverage.py` (`AssessmentTier`, `AcknowledgeClass`,
  `AssessmentPolicy`, `AcknowledgedTest`, `CoverageResult`),
  `medical/coverage.py` (`_POLICY_DATA`, `classify_coverage`, `policy_for`,
  `assessable_test_names`/`policy_test_names`). `extraction/parser.py` reads
  one-sided ranges; `schemas/knowledge.py` gained `RangeBounds` + sex blocks;
  `medical/ranges.py` resolves sex-aware (`_union`, `_bounds_for_sex`);
  `medical/severity.py` + `rag/index.py` (`load_test_knowledge`) extended.
- Tests: fast suite green — 304 in the cloud subset (OCR + RAG excluded, not
  installable there); Rohit's Mac runs the full suite incl. OCR + slow real-BGE.
  New this sprint: `test_metadata.py`, `test_patient.py`, `test_coverage.py`,
  `test_coverage_schema.py`, `test_kb_integrity.py`, `test_coverage_adversarial.py`,
  `tests/integration/test_full_panel_coverage.py`, `tests/fixtures/full_panel.py`.
- Knowledge base: grew to **38 tests** across `test_knowledge/` (177 snippets)
  and `reference_ranges/` (cbc/lipid/glucose/thyroid/kft), MedlinePlus/
  standards-cited; Hemoglobin/Hematocrit/RBC/HDL/Creatinine/Uric-Acid sex-aware
  from real report intervals. NOTE: Hemoglobin's CRITICAL thresholds are still
  example-sourced; some later-wave values lean on standards, not a printed
  range (#019 sourcing review still pending before clinical use).

## Open issues / blockers / homework (Rohit's to do)

1. **KB reference-range sourcing (#019):** replace remaining example/STARTER
   sources with real cited ones BEFORE clinical use — priority: Hemoglobin's
   critical thresholds (still example-sourced) and the later-wave values not
   backed by a printed range (HDL/glucose/thyroid; Free T3/T4 is the softest,
   assay-dependent).
2. **Architecture reflection exercises:** Sprint-4 (why deterministic
   severity) and Sprint-5 (why validate+guardrail despite a careful prompt)
   — 5 sentences each in docs/06. (Later retros are written by the pair;
   Rohit can add a personal note.)
3. Minor/nominal: Sprint-0 "break the CI" exercise still open.

No hard blockers for starting Sprint 8.

## Sprint 8 real-run findings — 8.9 (evaluation) targets

From uploading a REAL Tata 1mg report through the app (2026-07-15). The parser now reads it well (33 assessed, 22 acknowledged, ranges correctly matched), but a long tail remains — to be measured + fixed systematically at 8.9, not hacked now:

1. **Missed tests with prefixed / multi-line ranges** (currently land in 'could not read'): **HDL 47** (range wraps: 'Undesirable/high risk <40mg/dL'), **Glucose-Random 80** (range 'Normal - 70 - 140,' — the word 'Normal' + trailing comma break the range grammar). HDL missing from a lipid panel matters.
2. **Vitamin D shows the WRONG range** ('31.7 … < 20'): parser grabbed the 'Deficiency:<20' threshold as the range. Acknowledged (not graded) so no false verdict, but the displayed range misleads (31.7 is actually sufficient, 30–100).
3. **Scope/threshold — urgency inflation:** PDW (29.2) and Absolute Basophil Count (0.01) were graded 'highly abnormal' and pushed the overall verdict to URGENT, which over-alarms. Question for #030/#019: should platelet indices + absolute differential counts be in the ASSESSED (graded) tier, or ACKNOWLEDGED? Genuinely notable values were only Creatinine (mild high), Uric Acid (moderate high), LDL (high) — none individually urgent.
4. **Eval harness (the 8.9 deliverable itself):** measure extraction recall + grading precision on synthetic fixtures in CI, and once locally on the real Tata/Lal/Labsmart reports (#010 — aggregate numbers only, never commit report text).

## Exact next steps (to resume)

1. **Sprint 8 in progress** (plan: `docs/16-sprint-8-plan.md`; milestone:
   **RC1 LIVE** on Hugging Face Spaces). 8.1 ✅ done — the four deploy
   decisions are locked (see the appendix in docs/16). Next task:
   **8.2 — declare `knowledge_base/**/*.json` as package data in
   `pyproject.toml` + a built-wheel test** (`uv build`, assert the KB JSON is
   inside the wheel, per #019) — Rohit core + Claude test (~1.5h).
   Then 8.3 WeasyPrint PDF → 8.4 render tests → 8.5 Gradio skeleton → 8.6
   result rendering → 8.7 demo mode + deploy config → 8.8 app E2E → 8.9 eval
   → 8.10 HF deploy → 8.11 coverage ratchet → 8.12 close (log #035–#037).
   NOTE for deploy: the persisted RAG index cache path (#034,
   `~/.cache/mediscan`) needs a writable location on the Space.
3. RC2/parked: native async provider SDK for true timeout cancellation (#032);
   per-finding explanation chains (needs a schema change; RC1 is report-level);
   honor 429 `retryDelay` in the chain; age-specific ranges (#029); the
   full scanner-pipeline parser rewrite if a new format needs it (#033).

**Gemini note:** free tier worked with model `gemini-2.5-flash`
(gemini-2.0-flash had limit 0). Both keys live in Rohit's .env.
