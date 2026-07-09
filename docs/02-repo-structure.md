# MediScan RC1 — Repository Structure

*A repo layout is a map of responsibilities. If you always know where a thing "should" live, you never create spaghetti. This layout is a modular monolith: one app, clean internal domains, ready to grow into RC2/RC3 without reshuffling.*

> **Note:** this document shows the **target** layout for the finished RC1,
> including modules not yet built (e.g. `rag/`, `reports/`, `ui/`,
> `orchestration/`) and some names that evolved during implementation (e.g.
> AI providers are now one `ai/providers/openai_compatible.py`, prompts live
> in `ai/prompts.py`). For a map of what is **actually built today** and how
> a request flows through it, see
> [docs/12-understanding-the-codebase.md](12-understanding-the-codebase.md).

---

```
mediscan/
├── pyproject.toml              # Project definition + pinned dependencies (managed by uv)
├── uv.lock                     # Exact dependency versions (commit this!)
├── README.md                   # What the project is, how to run it
├── LICENSE                     # MIT
├── .gitignore                  # Never commit: .env, temp files, caches, sample PHI
├── .env.example                # Names of required env vars, with FAKE values
├── .pre-commit-config.yaml     # Auto-runs Ruff/Black before every commit
│
├── .github/
│   └── workflows/
│       └── ci.yml              # Lint + tests + security scan on every push
│
├── docs/                       # These documents + future diagrams/ADRs
│
├── prompts/                    # ALL LLM prompts live here as versioned text files,
│   ├── extraction/             #   never as strings buried in Python code.
│   ├── summarization/          #   Why: prompts are product logic — they need review,
│   ├── urgency/                #   diffing, and reuse just like code.
│   ├── guardrails/
│   ├── diet/
│   ├── rag/
│   ├── confidence/
│   ├── fallback/
│   ├── formatting/
│   └── evaluation/
│
├── knowledge_base/             # Curated medical KB (the "open book" for RAG)
│   ├── reference_ranges/       #   JSON: generalized adult ranges + severity bands
│   ├── test_explanations/      #   Markdown: what each lab test measures/means
│   ├── dietary_guidance/       #   Markdown: informational-only diet notes
│   ├── urgency_guidance/       #   Markdown: interpretation guidance
│   └── specialist_mapping/     #   JSON: finding category → specialist type
│
├── src/
│   └── mediscan/
│       ├── __init__.py
│       ├── config.py           # Settings from env vars (pydantic-settings), one place
│       │
│       ├── schemas/            # ★ THE MASTER SCHEMA — the project's backbone.
│       │   ├── report.py       #   AnalysisReport (top-level object)
│       │   ├── labs.py         #   LabResult, ReferenceRange, Severity enums
│       │   ├── urgency.py      #   UrgencyAssessment
│       │   ├── summaries.py    #   PatientSummary, DoctorSummary, DietaryInfo
│       │   └── confidence.py   #   ConfidenceBreakdown, ProcessingMetadata
│       │
│       ├── ingestion/          # Security front door
│       │   ├── validators.py   #   MIME/magic-byte checks, size limits
│       │   └── storage.py      #   Secure temp file handling + guaranteed cleanup
│       │
│       ├── ocr/                # Document reading
│       │   ├── base.py         #   OcrEngine interface (the abstraction)
│       │   ├── router.py       #   text-PDF vs scan detection
│       │   ├── pymupdf_engine.py
│       │   ├── paddle_engine.py
│       │   └── preprocessing.py#   deskew/contrast for bad photos
│       │
│       ├── extraction/         # Text → structured LabResult objects
│       │   ├── deterministic.py#   regex/table parsing (runs first)
│       │   ├── llm_extractor.py#   LLM extraction (only when rules fail)
│       │   └── normalization.py#   synonym maps, unit canonicalization
│       │
│       ├── medical/            # ★ Deterministic medical engine (no AI here, ever)
│       │   ├── ranges.py       #   report-range-first, KB-range-fallback logic
│       │   ├── severity.py     #   Normal→Critical banding
│       │   └── urgency.py      #   conservative roll-up rules
│       │
│       ├── rag/
│       │   ├── kb_loader.py    #   loads knowledge_base/ into ChromaDB
│       │   ├── embeddings.py   #   BGE-small wrapper
│       │   └── retriever.py    #   query → grounded snippets
│       │
│       ├── ai/                 # Everything that talks to LLMs
│       │   ├── client.py       #   LLMClient interface + fallback chain
│       │   ├── providers/      #   gemini.py, github_models.py
│       │   ├── prompt_loader.py#   loads/fills templates from prompts/
│       │   └── validation.py   #   schema-validate output, repair-retry
│       │
│       ├── safety/
│       │   ├── guardrails.py   #   forbidden-content checks on AI text
│       │   └── disclaimers.py  #   single source of disclaimer text
│       │
│       ├── confidence/
│       │   └── scoring.py      #   hybrid weighted confidence
│       │
│       ├── orchestration/
│       │   └── pipeline.py     #   async pipeline wiring all stages together
│       │
│       ├── reports/
│       │   ├── templates/      #   HTML/CSS for the PDF
│       │   └── pdf.py          #   WeasyPrint generation
│       │
│       └── ui/
│           ├── app.py          #   Gradio app entry point
│           └── components.py   #   result cards, urgency badges, styling
│
└── tests/
    ├── fixtures/               # Sample reports (synthetic only — never real PHI!)
    ├── unit/                   # mirrors src/mediscan/ one-to-one
    ├── integration/            # multi-stage tests (OCR→extraction→medical)
    └── e2e/                    # upload → PDF, full pipeline
```

## The rules that keep this clean

1. **Dependencies point one way.** `schemas/` imports nothing from the app; everything
   imports `schemas/`. `medical/` never imports `ai/` — the deterministic engine cannot
   depend on AI, by construction.
2. **`src/` layout** (not a flat package) — forces installs/tests to run against the real
   package and prevents a whole class of import bugs.
3. **Tests mirror source.** `src/mediscan/medical/severity.py` ⇒
   `tests/unit/medical/test_severity.py`. Finding a test is never a search.
4. **Prompts and KB are data, not code.** Editable and reviewable without touching Python.
5. **One concept per module.** If a file needs "and" to describe it, split it.
6. **RC2 readiness:** when Django + PostgreSQL arrive, they slot in as new modules
   (`web/`, `db/`) consuming the same schemas — nothing above needs to move.
