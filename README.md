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
guesswork. AI is used only to *explain* findings in friendly language, and if every AI
model is unavailable the product still produces a full analysis from deterministic
templates.

> ## ⚠️ Medical Disclaimer
>
> MediScan is an **informational tool only**. It does **not** provide medical advice,
> diagnosis, or treatment, and it is **not** a substitute for a qualified healthcare
> professional. Always consult a doctor about your medical reports and health decisions.

## Status

🚧 **RC1 in development** — Sprint 5 complete (240 tests passing).

| Sprint | Delivered |
|---|---|
| 0 ✅ | Tooling: uv, Ruff+Black, pytest, pre-commit, CI |
| 1 ✅ | Security-hardened master schema (Pydantic v2), full test suite |
| 2 ✅ | Secure upload validation (magic bytes, spoof detection), self-destructing storage, PyMuPDF text extraction, text-vs-scan router, synthetic fixtures |
| 3 ✅ | OCR: PaddleOCR engine (images + scanned PDFs), image preprocessing, OcrEngine contract, DocumentType→engine factory; security-hardened (image-bomb guard, config bounds, page cap) |
| 4 ✅ | Deterministic medical engine: tolerant line parser, name/unit normalization, report-first/KB-fallback range resolution (with merged KB critical thresholds), hybrid severity banding, conservative urgency roll-up; end-to-end integration test — zero AI |
| 5 ✅ | AI explanation layer: one medicine-blind `LLMClient` contract; one OpenAI-compatible provider driving Gemini + GitHub Models; versioned prompt templates with injection fencing; structured output with repair-retry; resilient fallback chain; deterministic template floor; output guardrail; provenance on every output |
| 6 🔜 | RAG & the knowledge base: curated KB content, ChromaDB + embeddings, retrieval grounding |

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

The AI explanation layer reads free-tier API keys from `.env`
(`MEDISCAN_GEMINI_API_KEY`, `MEDISCAN_GITHUB_MODELS_TOKEN`). They are **optional**:
without them, the deterministic pipeline and template-based explanations run unchanged —
the test suite is fully mock-first and needs no keys or network.

Note: the OCR tests are marked `slow` and excluded from the default run. Run them with
`uv run pytest -m slow` (downloads ~200 MB of PaddleOCR models on first use).

## Documentation

| Document | What it covers |
|---|---|
| [Product brief](docs/00-product-brief.md) | What we're building, scope, safety rules |
| [Architecture overview](docs/01-architecture.md) | The pipeline, stage by stage |
| [Repository structure](docs/02-repo-structure.md) | Where everything lives and why |
| [Sprint roadmap](docs/03-sprint-roadmap.md) | The build plan, sprint by sprint |
| [Decision log](docs/04-decision-log.md) | Every significant choice and its reasoning |
| [Environment setup](docs/05-environment-setup.md) | Blank machine → running tests |
| [Reflections & retros](docs/06-reflections.md) | Per-sprint lessons learned |
| [Project starter playbook](docs/07-python-project-starter-playbook.md) | Reusable setup pipeline for any Python project |
| [Sprint plans](docs/) | Detailed just-in-time plans: docs/08 (S2), 09 (S3), 10 (S4), 11 (S5) |
| [**Understanding this codebase**](docs/12-understanding-the-codebase.md) | **New-contributor onboarding guide — start here if you're new** |
| [Project status](project-status.md) | Live single-source-of-truth for resuming work |

## Tech stack (RC1)

Python 3.12+ · uv · Pydantic v2 · PyMuPDF + PaddleOCR (hybrid OCR) · Pillow (preprocessing) ·
`openai` SDK driving Gemini + GitHub Models (OpenAI-compatible endpoints) with deterministic
fallback · ChromaDB + BGE-small embeddings (RAG, Sprint 6) · WeasyPrint (PDF reports, Sprint 8) ·
Gradio (UI, Sprint 8) · pytest · Ruff + Black · GitHub Actions

## License

[MIT](LICENSE) © 2026 Rohit
