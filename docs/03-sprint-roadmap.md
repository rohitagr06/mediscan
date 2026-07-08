# MediScan RC1 — Sprint Roadmap

*8 weekly sprints at your 20+ hrs/week pace. **You write the code; I mentor, review, and unblock.** Sprints 0–1 are fully detailed below. Later sprints are outlined only — we detail each one together when we reach it, applying what earlier sprints taught us. That's how real teams plan: precisely for now, loosely for later.*

**How to work each sprint:** tasks are micro-sized (30 min – 2 hrs each). Do one at a time, in order. Commit after every task with a clear message. If stuck > 30 minutes, that's not failure — bring it to me, debugging together is the curriculum.

---

## Sprint 0 — Foundations & Tooling (Week 1) ✅ COMPLETE

**Learning goals:** virtual environments and packaging with `uv` · project layout · linting/formatting · pytest basics · pre-commit hooks · your first CI pipeline.

**Milestone:** an installable, tested, CI-green empty skeleton on GitHub.

### Tasks

| # | Task | ~Time |
|---|---|---|
| 0.1 | Install `uv` (`curl -LsSf https://astral.sh/uv/install.sh \| sh`), verify `uv --version` | 30m |
| 0.2 | Create GitHub repo `mediscan`, clone into your Mediscan folder, add MIT LICENSE + .gitignore (Python template) | 45m |
| 0.3 | `uv init` → make `pyproject.toml`; understand every line of it (I'll explain each) | 1h |
| 0.4 | Create the `src/mediscan/` skeleton from the repo-structure doc (empty `__init__.py` files) | 1h |
| 0.5 | Add Ruff + Black as dev dependencies; configure in `pyproject.toml`; run them | 1h |
| 0.6 | Write `src/mediscan/config.py` with a trivial `Settings` class (pydantic-settings) reading one env var; create `.env.example` | 1.5h |
| 0.7 | Write your first test: `tests/unit/test_config.py` — assert settings load. Run `uv run pytest` | 1h |
| 0.8 | Add pre-commit with Ruff/Black hooks; make a commit and watch it auto-format | 1h |
| 0.9 | Write `.github/workflows/ci.yml`: install uv → sync deps → ruff → pytest. Push, watch it go green | 2h |
| 0.10 | Write README.md: what MediScan is, how to set up dev env | 1h |

**Try Yourself:** deliberately break the CI (commit a lint error) and read the failure log until you understand exactly which line the pipeline objected to. Then fix it.
**Debugging Exercise:** rename `.env` and see what error `Settings` gives; make the error message friendlier.
**Architecture Reflection (write 5 sentences in docs/):** why do we pin dependencies? What could go wrong if two developers had different library versions?

---

## Sprint 1 — The Master Schema (Week 2) ✅ COMPLETE

**Learning goals:** Python type hints deeply · Pydantic v2 models, validators, enums · schema-first design · unit-testing validation logic · why the schema is the backbone every other module plugs into.

**Milestone:** the complete `AnalysisReport` schema family, fully tested, able to round-trip to/from JSON.

### Tasks

| # | Task | ~Time |
|---|---|---|
| 1.1 | Concept session with me: type hints, `Optional`, `Enum`, what Pydantic adds. You write 5 toy models to feel it | 2h |
| 1.2 | `schemas/labs.py`: `Severity` + `AbnormalDirection` enums, `ReferenceRange` model (with validator: `low < high`) | 1.5h |
| 1.3 | `schemas/labs.py`: `LabResult` (name, value, unit, range, severity, flag, confidence). Reject negative values where impossible | 2h |
| 1.4 | `schemas/urgency.py`: `UrgencyLevel` enum (Routine/Consult Soon/Urgent/Seek Immediate Care) + `UrgencyAssessment` (level, reasons list, contributing findings) | 1.5h |
| 1.5 | `schemas/summaries.py`: `PatientSummary`, `DoctorSummary`, `DietaryConsideration` (informational_only flag hardwired True), `SpecialistSuggestion` | 1.5h |
| 1.6 | `schemas/confidence.py`: `ConfidenceBreakdown` (ocr, extraction, validation, grounding, overall — all 0.0–1.0 validated) + `ProcessingMetadata` (timings, models used, fallback count) | 1.5h |
| 1.7 | `schemas/report.py`: `AnalysisReport` composing everything + mandatory `disclaimer` field with default text | 1.5h |
| 1.8 | Tests: valid data passes; each invalid case (bad range, out-of-bounds confidence, unknown enum) raises `ValidationError` | 2h |
| 1.9 | Round-trip test: `AnalysisReport` → `model_dump_json()` → `model_validate_json()` → equal | 1h |
| 1.10 | Build one complete realistic fake `AnalysisReport` fixture (a pretend CBC report) — this becomes test data for every future sprint | 1.5h |

**Try Yourself:** add a `model_validator` that forces `severity=NORMAL` whenever the value sits inside its reference range — the schema itself now refuses inconsistent medical states.
**Optimization Challenge:** compare `model_dump()` vs `model_dump_json()` performance on 1,000 reports with `timeit`.
**Debugging Exercise:** I'll hand you a malformed JSON blob; your job is to read the `ValidationError` and pinpoint all 3 problems without running the data through fixes first.
**Architecture Reflection:** why did we build schemas before OCR, when OCR is stage 1 of the pipeline?

---

## Sprint 2 — Ingestion & Text-PDF Extraction ✅ COMPLETE *(full plan: docs/08)*

Secure upload validation (magic bytes, size caps, temp-file hygiene) · PyMuPDF text + table extraction · the text-vs-scan router · fixtures from synthetic lab PDFs we generate ourselves.
**Milestone:** a real text-PDF lab report in → raw structured text out, safely.

## Sprint 3 — OCR for Scans & Photos ✅ COMPLETE *(full plan: docs/09)*

PaddleOCR setup on your Mac (with Tesseract escape hatch) · `OcrEngine` abstraction · image preprocessing · OCR confidence capture · router completion.
**Milestone:** a phone photo of a report in → text + confidence out.

## Sprint 4 — Extraction, Normalization & the Medical Engine ✅ COMPLETE *(full plan: docs/10)*

Regex/table parsing into `LabResult` · synonym + unit normalization · reference-range logic (report-first, KB-fallback) · severity banding · conservative urgency roll-up. **The safety-critical sprint — pure deterministic Python, heaviest testing of the project.**
**Milestone:** text in → flagged, severity-ranked, urgency-assessed results out, zero AI involved. Decisions #018–#022 logged; an end-to-end integration test turns the CBC fixture into a Consult-Soon verdict.

## Sprint 5 — The AI Layer *(outline)*

`LLMClient` interface · Gemini + GitHub Models providers · fallback chain, timeouts, backoff · prompt templates in `prompts/` · schema-validated structured output with repair-retry · patient & doctor summaries · guardrail pass.
**Milestone:** grounded, safe, friendly summaries — that degrade gracefully when APIs die.

## Sprint 6 — RAG & the Knowledge Base *(outline)*

Author the curated KB (ranges, test explanations, diet notes, specialist mapping) · ChromaDB + BGE-small embeddings · retrieval into prompts · grounding citations in explanations.
**Milestone:** every AI explanation traceable to a KB source.

## Sprint 7 — Confidence, Orchestration & Explainability *(outline)*

Hybrid confidence scoring · async pipeline wiring (concurrency, timeouts, cancellation) · full explanation chain assembly per abnormal finding.
**Milestone:** the complete `AnalysisReport` produced end-to-end from one function call.

## Sprint 8 — UI, PDF & Ship *(outline)*

Gradio app (upload → progress → color-coded results → urgency badge) · WeasyPrint professional PDF · E2E tests · evaluation pass (extraction accuracy, hallucination check) · deploy to Hugging Face Spaces.
**Milestone:** **RC1 live.** A stranger can use it from a URL.

---

## Standing rules for every sprint

- Every sprint ends with: working demo, green tests, a short refactor, and one "what I'd improve" note in docs.
- New concept → I explain it *before* you code it, with a toy example first.
- Nothing merges to `main` with failing CI.
- No real medical documents in the repo or tests — synthetic fixtures only.
