# Understanding This Codebase: A Beginner's Guide

*You know some Python. You know nothing about this project, its medical
domain, or its tools. This guide gets you from zero to "I can find things
and make a small change safely." Read it top to bottom once; keep it open
as a map afterward.*

> This guide describes what is **actually built today** (end of Sprint 5).
> The forward-looking target layout lives in
> [docs/02-repo-structure.md](02-repo-structure.md); the day-to-day status
> lives in [project-status.md](../project-status.md).

---

## 1. What this project is (in one minute)

**MediScan** reads a lab report (a PDF or a photo) and produces a clear,
plain-English analysis: which blood values are abnormal, how serious each
is, how urgently you should see a doctor, and *why*.

The single rule that shapes the entire codebase:

> **Anything that could hurt someone if it's wrong — deciding "this value
> is critical" or "see a doctor immediately" — is computed by plain,
> testable Python rules. The AI is only ever allowed to *explain* those
> decisions in friendly words. The AI never decides.**

This is called **deterministic-first, AI-explains**. If you remember only
one thing, remember that. It is why the code is split the way it is.

---

## 2. The big picture: a pipeline

A document flows through a series of stages, each doing one job and handing
a well-defined object to the next. Think of an assembly line:

```
  Upload (PDF / photo)
        │
        ▼
  1. INGESTION        validate it's really a PDF/image, check size,
     (ingestion/)     store it under a safe random name
        │
        ▼
  2. ROUTER + OCR     is this a text-PDF or a scan/photo?
     (ocr/)           extract the text (PyMuPDF for text, PaddleOCR for pixels)
        │             → produces raw text
        ▼
  3. PARSE            turn text lines into structured LabResult objects
     (extraction/)    "Hemoglobin 9.8 g/dL 13.0-17.0 L"  →  a typed object
        │
        ▼
  4. MEDICAL ENGINE   THE SAFETY CORE — pure rules, zero AI
     (medical/)       resolve each value's normal range, decide its severity
        │             (normal/mild/moderate/high/critical), roll up an
        │             overall urgency. Every number is auditable.
        ▼
  5. AI EXPLANATION   turn the verdict into four friendly write-ups
     (ai/ + safety/)  (patient summary, doctor summary, dietary notes,
        │             specialist suggestions). If the AI is down or says
        │             something unsafe, plain templates fill in instead.
        ▼
  Result: a verdict + four explanations, each tagged with where it came from
```

Stages 1–4 are **fully deterministic** — no AI, no internet. Stage 5 is the
only place an AI model is used, and even there it can only *phrase* what
stage 4 already decided. If every AI provider is offline, stage 5 still
produces all four outputs from templates. The product never goes blank.

*(Not built yet: RAG grounding from a knowledge base (Sprint 6), a
confidence score, async orchestration that wires all stages into one call
(Sprint 7), and the Gradio web UI + PDF report (Sprint 8).)*

---

## 3. Follow one report through the system (a worked walkthrough)

Say a user uploads `cbc_report.pdf` containing the line
`Hemoglobin 9.8 g/dL 13.0 - 17.0 L`. Here is the actual journey, with the
functions that do each step:

1. **Validate** — `ingestion/validators.py::validate_upload` checks the
   file's real type by its *magic bytes* (the first few bytes of the file),
   not its name, so `virus.exe` renamed to `report.pdf` is rejected. It also
   enforces a size limit.
2. **Store safely** — `ingestion/storage.py::SecureUploadDir` copies the
   file into a temporary directory under a random UUID name (the original
   filename could itself be sensitive) and guarantees the directory is
   deleted afterward, even on a crash.
3. **Route** — `ocr/router.py::detect_document_type` peeks at the PDF: does
   it already contain real text, or is it just pixels? It returns a
   `DocumentType` (`PDF_TEXT`, `PDF_SCANNED`, or `IMAGE`).
4. **Pick an engine** — `ocr/factory.py::get_engine_for` maps that
   `DocumentType` to the right reader: `PyMuPdfEngine` for text PDFs,
   `PaddleOcrEngine` (real OCR) for photos, `ScannedPdfEngine` for scans.
5. **Extract text** — the engine's `.extract()` returns an
   `ExtractedDocument` whose `.full_text` holds the text.
6. **Parse** — `extraction/parser.py::parse_lab_text` reads the text line by
   line. A line matching the lab-row shape becomes a `LabResult`; anything
   else (headers, page numbers) is kept in `unparsed_lines`, never silently
   dropped. Our line becomes:
   `LabResult(test_name="Hemoglobin", value=9.8, unit="g/dL",
   reference_range=ReferenceRange(low=13.0, high=17.0), flag_in_report="L")`.
7. **Judge severity** — `medical/severity.py::assess_results` calls, for
   each value, `medical/ranges.py::resolve_reference_range` to decide which
   normal range and critical thresholds apply (the report's own range wins;
   the knowledge base fills in critical thresholds), then bands the value:
   9.8 is moderately below 13.0, so **MODERATE / low**. The result is a
   `SeverityAssessment` — a *new* object; the original `LabResult` is never
   modified.
8. **Roll up urgency** — `medical/urgency.py::assess_urgency` takes all the
   per-value verdicts and produces one `UrgencyAssessment` for the whole
   report. The worst finding wins; a single CRITICAL forces "Seek Immediate
   Care." Here the worst is MODERATE, so overall = **Consult Soon**.
9. **Explain** — `ai/explain.py::explain_report` builds a facts block from
   the verdict, and for each of the four outputs: fills a prompt template,
   runs it through the provider chain (Gemini → GitHub models), validates
   the JSON the model returns, and runs it past the safety guardrail. If any
   step fails, it uses the deterministic template instead. Every output
   comes back tagged with its provenance (AI or template, which model).

That's the whole current pipeline. Steps 1–8 involve no AI whatsoever.

---

## 4. Project structure: what's in each folder and why

Everything lives under `src/mediscan/`. The golden rule: **dependencies
point one way — everything can import `schemas/`, but `schemas/` imports
nothing from the app, and `medical/` never imports `ai/`.** The safety
engine literally *cannot* depend on AI, by construction.

| Folder | What it holds | Depends on |
|---|---|---|
| `config.py` | All settings, loaded from environment variables (one place). | — |
| `schemas/` | Every data shape in the project (Pydantic models). The backbone. `labs.py`, `medical.py`, `urgency.py`, `summaries.py`, `ai.py`, `documents.py`, `knowledge.py`, `report.py`, and `base.py` (the shared parent class). | nothing app-internal |
| `ingestion/` | The security front door: `validators.py` (type/size checks), `storage.py` (safe temp files), `exceptions.py`. | schemas |
| `ocr/` | Reading documents: `router.py`, the engines (`pymupdf_engine.py`, `paddle_engine.py`, `scanned_pdf.py`), `preprocessing.py`, `factory.py`, plus `base.py` (the engine contract). | schemas, config |
| `extraction/` | Turning text into data: `parser.py` (regex line parser), `normalization.py` (synonyms/units). | schemas |
| `medical/` | **The deterministic engine.** `ranges.py`, `severity.py`, `urgency.py`, `reference_data.py` (loads the KB). No AI, ever. | schemas, extraction |
| `knowledge_base/` | Curated medical data as JSON (`reference_ranges/cbc.json`). Data, not code — reviewable by a clinician. | — |
| `ai/` | Everything that talks to an LLM: `base.py` (the provider contract), `providers/openai_compatible.py`, `prompts.py`, `structured.py`, `chain.py`, `templates.py` (the no-AI fallback), `explain.py` (assembly), `exceptions.py`. | schemas, config, safety, medical |
| `safety/` | `guardrail.py` — blocks forbidden content in AI text. | — |
| `rag/`, `reports/`, `ui/`, `orchestration/`, `confidence/` | **Empty stubs** — future sprints (6, 8, 7). | — |

Tests mirror this exactly: `src/mediscan/medical/severity.py` is tested by
`tests/unit/medical/test_severity.py`. Finding a test is never a search.

---

## 5. Key technologies (and where to learn them)

| Tool | What it does here | Docs |
|---|---|---|
| **Python 3.12** | The language. | https://docs.python.org/3/ |
| **uv** | Manages the virtual environment and dependencies (like `pip` + `venv`, much faster). Every command below starts with `uv run`. | https://docs.astral.sh/uv/ |
| **Pydantic v2** | Defines and *validates* every data shape. If data is the wrong shape, it's rejected at the boundary, not deep in the code. | https://docs.pydantic.dev/latest/ |
| **pydantic-settings** | Loads config from environment variables into a typed object. | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ |
| **PyMuPDF** | Extracts text from real text-PDFs, fast. | https://pymupdf.readthedocs.io/ |
| **PaddleOCR** | Optical Character Recognition — reads text out of *pixels* (photos, scans). | https://github.com/PaddlePaddle/PaddleOCR |
| **Pillow (PIL)** | Image cleanup (grayscale, contrast) before OCR. | https://pillow.readthedocs.io/ |
| **openai (SDK)** | One client library that talks to *both* Gemini and GitHub Models (both speak the OpenAI API). | https://github.com/openai/openai-python |
| **pytest** | The test runner. | https://docs.pytest.org/ |
| **Ruff + Black** | Ruff = linter (catches mistakes/style); Black = auto-formatter. Run automatically before every commit. | https://docs.astral.sh/ruff/ · https://black.readthedocs.io/ |

---

## 6. Glossary (domain + project terms)

**Medical / domain terms**

- **Lab report / CBC** — a "Complete Blood Count" is a common blood test.
  RC1 focuses on CBC-style reports.
- **Reference range** — the "normal" interval for a test, e.g. Hemoglobin
  13.0–17.0 g/dL. A value outside it is flagged.
- **Critical threshold** — a value so extreme it's an emergency (e.g.
  Hemoglobin ≤ 7.0). Comes only from the reviewed knowledge base, never
  invented by code.
- **Severity** — how far outside normal a value is: Normal, Mild, Moderate,
  High, Critical.
- **Urgency** — how soon to see a doctor for the *whole report*: Routine,
  Consult Soon, Urgent, Seek Immediate Care.
- **PHI** — Protected Health Information. Anything identifying a patient's
  health. We must **never** log it or commit it. Test data is 100%
  synthetic.

**Project-specific terms**

- **Deterministic-first** — the core rule: rules decide, AI only explains.
- **The verdict** — the deterministic output: the per-value
  `SeverityAssessment`s plus the one `UrgencyAssessment`.
- **Provider / the chain** — an AI model (Gemini, etc.) behind a common
  interface; "the chain" tries them in order and falls back to templates.
- **Guardrail** — a deterministic filter that blocks AI text containing a
  diagnosis, a drug dose, or a prescription.
- **Provenance** — a record on every output of how it was made (AI vs
  template, which model, which prompt version).
- **Decision log** — [docs/04-decision-log.md](04-decision-log.md). Every
  "why did we do it this way?" is a numbered row (e.g. **#006**). Code
  comments cite these numbers.
- **Sprint** — a week-sized chunk of work. See
  [docs/03-sprint-roadmap.md](03-sprint-roadmap.md).

---

## 7. Set up your environment from scratch

You need Python 3.12+ and `git`. Everything else is handled by `uv`.

```bash
# 1. Install uv (the package/venv manager)
curl -LsSf https://astral.sh/uv/install.sh | sh      # macOS/Linux

# 2. Get the code
git clone https://github.com/rohitagr06/mediscan.git
cd mediscan

# 3. Create the venv and install ALL dependencies (incl. dev tools)
uv sync --all-groups

# 4. Copy the example config. The AI keys are OPTIONAL — without them the
#    deterministic pipeline and the whole test suite still run.
cp .env.example .env

# 5. Install the pre-commit hooks (auto-format/lint on every commit)
uv run pre-commit install

# 6. Confirm everything works
uv run pytest
```

If step 6 is green, you're set. The fuller, hand-held version is in
[docs/05-environment-setup.md](05-environment-setup.md).

---

## 8. Commands you'll use constantly

```bash
uv run pytest                       # run the fast test suite
uv run pytest tests/unit/medical    # run just one area's tests
uv run pytest -m slow               # run the heavy OCR tests too (downloads
                                    #   ~200 MB of models the first time)
uv run pytest -k severity           # run tests whose name contains "severity"
uv run ruff check .                 # lint the whole project
uv run ruff check . --fix           # lint and auto-fix what it can
uv run black .                      # auto-format
uv run python playground.py         # a scratch file for trying things by hand
```

**A note on `playground.py`:** throughout development we use a throwaway
`playground.py` at the repo root to try a function by hand before writing
tests. It's git-ignored — treat it as a scratchpad.

---

## 9. Where things live

- **Configuration** — all settings are fields on the `Settings` class in
  `src/mediscan/config.py`. Each maps to an environment variable prefixed
  `MEDISCAN_` (so `max_upload_mb` ← `MEDISCAN_MAX_UPLOAD_MB`). Local values
  go in `.env` (never committed). Secrets like API keys use Pydantic's
  `SecretStr`, which refuses to print itself.
- **Tests** — under `tests/`, mirroring `src/`. Run with `uv run pytest`.
- **Logs** — there is **no logging yet** (it arrives in Sprint 7, and even
  then it will record *events and metrics only, never PHI*). For now,
  debugging is done via tests and `playground.py`.
- **The knowledge base** — `src/mediscan/knowledge_base/reference_ranges/
  cbc.json`. Editable data; every entry carries a mandatory `source`.

---

## 10. Your first contribution (a concrete example)

**Goal: teach the parser that "Haemoglobin" (British spelling) means the
same as "Hemoglobin."**

The normalization map already handles this, so let's instead add a *brand
new* synonym as practice — say the abbreviation "HB%" for Hemoglobin.

1. **Find the right file.** Synonyms live in
   `src/mediscan/extraction/normalization.py`. Notice `_TEST_NAME_SYNONYMS`
   is a plain dictionary — *data, not logic*. That's deliberate: adding a
   synonym should never mean changing code logic.

2. **Make the change.** Add one line to the dictionary:
   ```python
   "hb%": "Hemoglobin",
   ```
   Keys are always lowercase (the function lowercases input before looking
   up).

3. **Write a test.** Open `tests/unit/extraction/test_normalization.py` and
   add:
   ```python
   def test_hb_percent_alias():
       assert normalize_test_name("HB%") == "Hemoglobin"
   ```

4. **Run it.** `uv run pytest tests/unit/extraction -q` — green means done.

5. **Commit.** `git add -A && git commit -m "Add HB% synonym for Hemoglobin"`
   — the pre-commit hooks auto-format and lint before the commit lands.

That's the whole loop: find the right small place, change data not logic
where possible, prove it with a test, commit. Most contributions are this
shape.

---

## 11. Coding standards and conventions

- **Every data shape is a Pydantic model** subclassing `MediScanModel`
  (`schemas/base.py`). That base forbids unknown fields, strips whitespace,
  and re-validates on mutation — security by default.
- **Type hints everywhere.** Functions declare their parameter and return
  types. This is enforced socially, not by a checker (yet).
- **Docstrings** explain *why*, not just *what*, and are written for a
  beginner. New public functions get a docstring with Args/Returns/Raises.
- **Comments cite decisions.** When code encodes a non-obvious choice, the
  comment references a decision-log number (e.g. `# decision #023`). Look it
  up in [docs/04-decision-log.md](04-decision-log.md).
- **Errors are specific and clean.** Catch specific exception types, wrap
  third-party errors in our own (`raise OurError(...) from err`), and never
  put secrets or PHI in an error message — only the exception *type* name.
- **One concept per module.** If a file needs "and" to describe it, split it.
- **Ruff + Black are law.** The pre-commit hooks run them; CI runs them
  again. Don't fight the formatter.
- **The deterministic boundary is sacred.** Never let `medical/` import
  `ai/`. Never let an AI model compute a severity, urgency, range, or
  abnormality. AI *explains*; it never *decides* (decision #006).

---

## 12. Troubleshooting

**`uv: command not found`** — the installer didn't add uv to your PATH.
Restart your terminal, or add `~/.local/bin` (macOS/Linux) to your PATH.

**`uv run pytest` fails on import errors** — you probably skipped
`uv sync --all-groups`. Run it. If it still fails, delete `.venv/` and sync
again.

**OCR tests fail or hang / "No module named paddle..."** — the OCR tests are
marked `slow` and excluded from the default run *on purpose*; they download
~200 MB of models on first use. Run the normal suite (`uv run pytest`)
without them, or run `uv run pytest -m slow` when you specifically want them.

**AI/live calls fail with a 429 or "quota" error** — that's a rate limit
from the free AI tier, not a bug. The code handles it (it falls back down
the chain to deterministic templates). For live experiments, the free
Gemini tier currently works with model `gemini-2.5-flash`
(`gemini-2.0-flash` may report a zero quota).

**"API key is not configured" when running AI code** — the keys in `.env`
are optional. The deterministic pipeline and all tests work without them.
Set `MEDISCAN_GEMINI_API_KEY` / `MEDISCAN_GITHUB_MODELS_TOKEN` in `.env`
only if you want live AI explanations.

**pre-commit reformatted my files and the commit "failed"** — that's normal.
Black/Ruff fixed your formatting; the files are now changed on disk. Just
`git add -A` and commit again — it'll pass the second time.

**A test asserts a specific number and I don't know why** — check the
decision log. Medical cutoffs (severity bands, critical thresholds) are
deliberate, sourced choices, not arbitrary.

---

## 13. Where to go next

- **The full architecture, stage by stage:**
  [docs/01-architecture.md](01-architecture.md)
- **Why every choice was made:** [docs/04-decision-log.md](04-decision-log.md)
- **The build story, sprint by sprint:**
  [docs/06-reflections.md](06-reflections.md)
- **What's happening right now / where to resume:**
  [project-status.md](../project-status.md)

Welcome aboard. When in doubt: rules decide, AI explains, and never log PHI.
