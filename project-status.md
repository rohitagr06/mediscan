# MediScan — Project Status

*Single source of truth for resuming across sessions. Cowork has no memory
between chats, so this file carries it. Read this FIRST every session.*

**Last updated:** 2026-07-10 (Sprint 6 COMPLETE — RAG & the knowledge base built, tested, grounding live)

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
  12-understanding-the-codebase, 13-sprint-6-plan.

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
- **⚠️ Device-bridge hazard:** staging/reading sometimes serves STALE file
  copies. Before reviewing/editing Rohit's files, verify against live disk
  (`device_bash cat` the real file), or read the live tree first. Never
  overwrite his files from a stale read. (Bit us in Sprint 6: the review
  copy of `embedding.py` was pre-6.6.)
- **Cloud sandbox limits:** `pymupdf`/`paddleocr`/`chromadb`/`sentence-
  transformers` are NOT installable in the cloud container (PyPI blocked),
  so OCR + real-index tests SKIP/can't run there — they run on Rohit's Mac.
  Chromadb-FREE logic (schema, chunking, grounding wiring, the AST boundary
  test) is verifiable in the sandbox. Run non-OCR tests with
  `PYTHONPATH=/usr/local/lib/python3.11/dist-packages:src /root/.local/bin/pytest`.

## Current position

**Sprints 0–6 are COMPLETE.** Deterministic pipeline: document → parse →
normalize → resolve ranges (KB criticals merged, #023) → severity →
urgency, zero AI. AI explanation layer (Sprint 5): one medicine-blind
`LLMClient` contract; ONE `OpenAICompatibleProvider` driving Gemini +
GitHub Models via the openai SDK (#024); versioned PromptTemplates with
injection fencing (#025); structured output + one repair-retry; resilient
chain with backoff; deterministic template floor; regex guardrail (#026);
ExplanationProvenance on every output. **RAG layer (Sprint 6, #028): a
curated sourced KB → chunked snippets → local BGE-small embeddings (real in
prod, injectable fake in tests) → in-memory ChromaDB rebuilt from files →
bounded retriever → grounding wired into the Sprint-5 FACTS seam →
`grounding_sources` on every AI explanation.** The `medical/` engine is
forbidden from importing `rag/`, proven by an AST boundary test. **259 fast
tests + 3 slow (real BGE + PaddleOCR) passing on Rohit's Mac.**

## This session's accomplishments (Sprint 6)

- 6.7 — wired retrieved KB snippets into the FACTS block (`_grounding_snippets`,
  `_augment_facts`); normal findings skipped, snippets deduped, retrieval
  failure swallowed (never a single point of failure).
- 6.8 — added `grounding_sources: list[str]` to `ExplanationProvenance` and
  threaded the unique sources onto every AI-path output (empty on the
  deterministic path).
- 6.9 — RAG test suite: happy-path half (schema/source/chunking/index/retrieval)
  + adversarial half (K-bounds, odd queries, grounding wiring, provenance,
  the `medical/`⊬`rag/` AST boundary, a slow real-BGE meaning test).
- Two library-behaviour bugs fixed: unique per-build collection name
  (`EphemeralClient` shares one backend → "already exists"); fake embedder
  overrides `__init__` WITHOUT calling super (base stub only warns).
- 6.10 — sprint close: decision #028, roadmap Sprint 6 ✅, architecture
  banner → end of Sprint 6, README status/table, Sprint 6 reflection,
  this file.

## Key decisions (full log in docs/04; most relevant recent ones)

- **#006** Deterministic-first, AI-explains (never violated — RAG feeds the
  AI layer ONLY, never the engine).
- **#023** Report range kept for banding, KB criticals merged in.
- **#024** One openai SDK + one provider class for Gemini + GitHub Models.
- **#025** Versioned PromptTemplates + provenance on every output.
- **#026** Deterministic block-and-fall-back guardrail.
- **#027** RC1 scope = full-body checkup, both sexes (engine expansion = 6.5).
- **#028 (this session)** RAG built now on the CBC KB, feeding AI only:
  ChromaDB + local BGE-small, in-memory index rebuilt from files, injectable
  embedder (+ fake for offline tests), grounding into the FACTS seam,
  `grounding_sources` traceability, `medical/`⊬`rag/` enforced by a test.

## Current state of code

- All source under `src/mediscan/`. Built & tested: config, full schema
  family, ingestion, OCR, extraction, deterministic medical engine, AI
  explanation layer, **and now `rag/`**.
- `rag/` BUILT: `embedding.py` (`bge_embedding_function` + `FakeEmbeddingFunction`
  subclassing ChromaDB's `EmbeddingFunction`), `index.py` (`load_snippets`,
  `build_index` with unique collection name, `@cache get_index`),
  `retriever.py` (`retrieve`, `RetrievedSnippet`, BGE query prefix,
  `settings.rag_top_k`). `ai/explain.py` now grounds via the retriever;
  `schemas/ai.py` `ExplanationProvenance` carries `grounding_sources`.
- Tests: 259 fast passing (incl. `tests/unit/rag/test_rag_layer.py` +
  `test_rag_adversarial.py`); 3 slow (real BGE + Paddle) pass with `-m slow`.
- Knowledge base: `src/mediscan/knowledge_base/test_knowledge/cbc.json`
  (5 CBC tests → 25 snippets, MedlinePlus-sourced) drives RAG.
  `reference_ranges/cbc.json` still has `"STARTER VALUE"` sources (#019).

## Open issues / blockers / homework (Rohit's to do)

1. **KB reference-range sourcing (#019):** replace every `"STARTER VALUE"`
   in `reference_ranges/cbc.json` with a real cited source BEFORE clinical use.
2. **Architecture reflection exercises:** Sprint-4 (why deterministic
   severity) and Sprint-5 (why validate+guardrail despite a careful prompt)
   — 5 sentences each in docs/06. (Sprint-6 retro is written by the pair;
   Rohit can add a personal note.)
3. Minor/nominal: Sprint-0 "break the CI" exercise still open.

No hard blockers for starting Sprint 6.5.

## Exact next steps (to resume)

1. Confirm CI is green on GitHub after the Sprint-6 commits land.
2. **Sprint 6.5 — Full-Panel Scope Expansion (#027)** is the next sprint:
   extend the parser to one-sided ranges (`< 200`, `> 40`, `< 5.7 %`); make
   reference ranges SEX-AWARE with the patient's sex read from the report;
   author the multi-panel sourced reference-range + explanation KB (KFT,
   lipids, electrolytes, vitamins, diabetes/HbA1c, thyroid, numeric urine).
   The RAG layer absorbs the bigger KB with NO code change. Needs a detailed
   plan doc (docs/14) before starting, like docs/13 for Sprint 6.
3. RC2/parked: honor 429 `retryDelay` in the chain; wire `ReportExplanations`
   into `AnalysisReport` (Sprint 7 orchestration); confidence scoring;
   observability; persisted RAG index if rebuild-per-process gets slow (#028).

**Gemini note:** free tier worked with model `gemini-2.5-flash`
(gemini-2.0-flash had limit 0). Both keys live in Rohit's .env.
