# MediScan — Decision Log

*Every significant decision gets a row. When future-you asks "why on earth did we do it this way?", the answer lives here. Real teams call these ADRs (Architecture Decision Records).*

| # | Date | Decision | Why | Revisit when |
|---|---|---|---|---|
| 001 | 2026-07-03 | **Mentor mode**: Rohit writes the code, Claude architects, explains, reviews, unblocks | Primary goal is deep learning, not just a shipped product | Never — this is the point |
| 002 | 2026-07-03 | **Lean docs first**, deep docs (LLD, full diagrams, security architecture) written as the system grows | 21 upfront documents would delay hands-on learning by weeks | If docs fall behind reality |
| 003 | 2026-07-03 | **No Django in RC1.** RC1 = Python package + Gradio. Django arrives in RC2 with PostgreSQL/sessions | RC1 has no DB, no auth — Django would be dead weight and cognitive overload for a first web project | Start of RC2 |
| 004 | 2026-07-03 | **Free-model chain**: Gemini free tier → GitHub Models (GPT-4.1-mini) → GitHub Models (Phi-4) → deterministic templates | No paid OpenAI key; GitHub Models + Gemini free tiers cover development at ₹0 | If free limits block development, or the project gets budget |
| 005 | 2026-07-03 | **RC1 scope = English lab reports only** (tabular diagnostic-lab PDFs/photos) | Narrow-and-working beats broad-and-broken; it's also the most common real document | RC2 scope planning |
| 006 | 2026-07-03 | **Deterministic-first, AI-explains**: severity + urgency computed only by auditable rules; LLMs restricted to explanation/summarization | Medical safety, auditability, and zero-AI graceful degradation | Never (safety principle) |
| 007 | 2026-07-03 | 8 weekly sprints; sprints detailed just-in-time (next sprint fully specified, later ones outlined) | 20+ hrs/week pace; plans made months ahead of code always rot | End of every sprint |
| 008 | 2026-07-03 | PaddleOCR is the target OCR engine; **Tesseract permitted as dev-time substitute** behind the same `OcrEngine` interface if macOS install fights us | Apple Silicon PaddleOCR installs are notoriously flaky; the abstraction makes the engine swappable | Sprint 3 |
| 009 | 2026-07-03 | `src/` layout, uv, Ruff+Black, pre-commit, CI from Sprint 0 | Production habits are learned by starting with them, not bolting them on | — |
| 010 | 2026-07-03 | No real medical documents ever enter the repo, tests, or logs — synthetic fixtures only | PHI protection is absolute; a public GitHub repo must never contain anyone's health data | Never |
| 011 | 2026-07-03 | Confidence scores have NO defaults — every score must be set explicitly; an absent ConfidenceBreakdown means "not yet scored" | A default of 1.0 could silently present unscored output as fully confident — unacceptable in a medical tool. Raised by Rohit during schema review | Never (safety principle) |
| 012 | 2026-07-03 | Schema security hardening: all models inherit MediScanModel with extra="forbid" + whitespace stripping; lab values ban NaN/Infinity and booleans; length caps on extracted strings | Probing found 6 silent acceptance holes (NaN values, hallucinated extra fields silently dropped, whitespace names, 1MB strings, bool→1.0 coercion). All are realistic OCR/LLM failure modes | If extra="forbid" proves too strict for a future provider integration |
| 013 | 2026-07-03 | validate_assignment=True on MediScanModel: mutating any field re-runs all validators. frozen=True considered and deferred | Post-construction mutation bypassed every validator (found by Rohit while evaluating frozen=True). frozen rejected for now: it is shallow (lists stay mutable), model_copy(update=) skips validation anyway, and the pipeline's enrichment flow (engine sets severity later) fits validated mutation better | RC2 — revisit frozen snapshots for audit trail |
| 014 | 2026-07-04 | PageText.char_count is a COMPUTED field, never stored/supplied | A stored copy drifted from its source: the base model's whitespace stripping shortened text after the engine had counted it (off-by-one crash on first real extraction). Derived values are measured, not remembered | If a counted-before-normalization value is ever genuinely needed |

## How to add a decision

One row, four honest answers: what we decided, why, what we gave up, and what would make us
reconsider. If a decision has no downside listed, we haven't thought hard enough about it.
