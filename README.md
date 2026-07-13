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

🚧 **RC1 in development — Sprints 0–7 complete.** One call —
`analyze_document(path) -> AnalysisReport` — now runs the whole pipeline, with
**zero AI in any safety decision** and a complete report even when every AI
model is down.

| Sprint | Focus | Status |
|---|---|---|
| 0 | Foundations & tooling — uv, Ruff/Black, pre-commit, CI | ✅ Complete |
| 1 | The master schema family (Pydantic v2) | ✅ Complete |
| 2 | Ingestion & text-PDF extraction (PyMuPDF) | ✅ Complete |
| 3 | OCR for scans & photos (PaddleOCR) | ✅ Complete |
| 4 | Extraction, normalization & the deterministic medical engine | ✅ Complete |
| 5 | AI explanation layer — providers, fallback chain, guardrail | ✅ Complete |
| 6 | RAG & the knowledge base (ChromaDB + BGE-small) | ✅ Complete |
| 6.5 | Full-panel scope expansion — both sexes, one-sided ranges, coverage tiers | ✅ Complete |
| 7 | Confidence, orchestration & explainability — one call → full report | ✅ Complete |
| 8 | UI, PDF & ship — Gradio, WeasyPrint, evaluation & deploy | ⏳ Next (RC1 live) |

**What one call does now:** secure ingestion → PyMuPDF/PaddleOCR extraction →
parsing (two-sided *and* one-sided ranges) → normalization → sex-aware range
resolution → assessed/acknowledged coverage split → severity → conservative
urgency roll-up → RAG-grounded AI explanations (guardrailed, run concurrently
with timeouts) → a deterministic hybrid confidence score. It reads a full-body
checkup (CBC, KFT, lipids, glucose/HbA1c, thyroid) for both sexes; out-of-scope
and sensitive tests are acknowledged but never graded.

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
