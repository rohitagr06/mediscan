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

🚧 **RC1 in development** — Sprint 0 (foundations & tooling) complete:
project skeleton, linting (Ruff + Black), tests (pytest), pre-commit hooks, and CI.

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
