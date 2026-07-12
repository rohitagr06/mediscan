# MediScan by DipsAI

**Intelligent Medical Report Analyzer**

![CI](https://github.com/rohitagr06/mediscan/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

MediScan is an AI-assisted medical document intelligence platform. Upload a lab report
(PDF or photo) and get back a clear, plain-English analysis: which values are normal,
which are abnormal and how severe, how urgently a doctor should be consulted — and *why*,
with every claim traced to a verified reference range or curated knowledge source.

Severity and urgency are computed by **deterministic, auditable rules** — never by AI
guesswork. AI is used only to *explain* findings in friendly language, grounded via RAG
on a curated medical knowledge base.

> ## ⚠️ Medical Disclaimer
>
> MediScan is an **informational tool only**. It does **not** provide medical advice,
> diagnosis, or treatment, and it is **not** a substitute for a qualified healthcare
> professional. Always consult a doctor about your medical reports and health decisions.

## Status

🚧 **RC1 in development** — Sprints 0–7 complete. **One call now turns a
document into a full analysis:** `analyze_document(path) → AnalysisReport` runs
the whole pipeline — secure ingestion → PyMuPDF/PaddleOCR extraction → parsing
(two-sided *and* one-sided ranges) → normalization → sex-aware range resolution
→ the assessed/acknowledged coverage split → severity → conservative urgency
roll-up (**zero AI** in any safety decision) → RAG-grounded AI explanations
(Gemini → GitHub Models → deterministic templates, guardrailed) → a
deterministic hybrid confidence score. The explanation outputs run concurrently
with per-output timeouts, the RAG index is persisted, and the whole run emits
PHI-safe metrics — yet it still produces a complete report when every AI model
is down. It reads a full-body checkup (CBC, KFT, lipids, glucose/HbA1c, thyroid)
for both sexes; out-of-scope and sensitive tests are acknowledged but never
graded. Remaining before RC1: the Gradio UI, the WeasyPrint PDF, and the
evaluation/deploy pass (Sprint 8).

## Quick start

See **[docs/05-environment-setup.md](docs/05-environment-setup.md)** for the full
step-by-step guide from a blank machine to running tests.

The short version:

```bash
git clone https://github.com/rohitagr06/mediscan.git
cd mediscan
uv sync --all-groups
cp .env.example .env
uv run pre-commit install
uv run pytest
```

## Documentation

| Document | What it covers |
|---|---|
| [Product brief](docs/00-product-brief.md) | What we're building, scope, safety rules |
| [Architecture overview](docs/01-architecture.md) | The pipeline, stage by stage |
| [Repository structure](docs/02-repo-structure.md) | Where everything lives and why |
| [Sprint roadmap](docs/03-sprint-roadmap.md) | The build plan, sprint by sprint |
| [Decision log](docs/04-decision-log.md) | Every significant choice and its reasoning |
| [Environment setup](docs/05-environment-setup.md) | Blank machine → running tests |

## Tech stack (RC1)

Python 3.12+ · uv · Pydantic v2 · PyMuPDF + PaddleOCR (hybrid OCR) · ChromaDB +
BGE-small embeddings (RAG) · Gemini / GitHub Models with deterministic fallback ·
WeasyPrint (PDF reports) · Gradio (UI) · pytest · Ruff + Black · GitHub Actions

## License

[MIT](LICENSE) © 2026 Rohit
