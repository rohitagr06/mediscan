# MediScan by DipsAI — Product Brief (Lean PRD)

**Intelligent Medical Report Analyzer**
*AI-assisted medical document intelligence platform with explainable clinical analysis and safety-first architecture.*

> **Version:** RC1 planning · **Date:** 2026-07-03 · **Status:** Approved to build

---

## 1. What we are building (in one paragraph)

MediScan lets a person upload a medical lab report (a PDF or a photo) and get back a clear,
honest, plain-English analysis: which values are normal, which are abnormal and how severe,
how urgently they should talk to a doctor, and *why* the system thinks so — every claim
traced back to a verified reference range or a curated knowledge source. It is an
**informational tool, never a doctor**.

## 2. Who it's for

| User | What they need |
|---|---|
| **Patients / families** | "What does this report actually say? Should I worry?" in friendly language |
| **Doctors (secondary)** | A compact clinical summary with flagged values and confidence scores |
| **You (the builder)** | A realistic, production-grade project to learn AI engineering deeply |

## 3. RC1 scope — what's IN

RC1 handles **English-language laboratory reports only** (blood panels, lipid profiles,
thyroid panels, etc. — the classic tabular diagnostic-lab PDF).

1. Upload a PDF or image (drag & drop, validated, size-limited, sanitized)
2. Hybrid OCR: PyMuPDF for text PDFs, PaddleOCR for scans/photos, automatic routing
3. Structured extraction: test name, value, unit, reference range → strict Pydantic schema
4. Abnormality detection with severity bands: **Normal · Mild · Moderate · High · Critical**
   — computed by *deterministic rules*, never by AI guessing
5. Urgency assessment: **Routine · Consult Soon · Urgent · Seek Immediate Care**
   — deterministic-first, medically conservative
6. AI-written summaries (patient-friendly + doctor-oriented), grounded via RAG on a local
   curated knowledge base
7. Informational-only diet/lifestyle considerations and suggested specialist categories
8. Explainability for every flag: detected value, expected range, severity reason,
   confidence score, grounding source
9. Confidence scoring (OCR + extraction + validation + grounding + fallback count)
10. Downloadable professional PDF report (WeasyPrint, MediScan branding, disclaimers)
11. Gradio UI (blue/white medical theme)
12. Free-model AI chain: **Gemini free tier → GitHub Models (GPT-4.1-mini / Phi-4) →
    deterministic parser fallback** — zero API cost
13. Tests, CI (GitHub Actions), security hygiene from day one

## 4. RC1 scope — what's OUT (deliberately)

- ❌ No database (files processed in-session; nothing persisted) — arrives in RC2
- ❌ No Django / web framework — arrives in RC2 with the DB and sessions
- ❌ No chat-with-your-report — RC2
- ❌ No prescriptions, discharge summaries, imaging reports, non-English documents
- ❌ No user accounts, no analytics dashboard — RC3

Cutting scope is not laziness — it is the single most important production-engineering skill.
A narrow thing that works beats a broad thing that almost works.

## 5. Medical safety requirements (non-negotiable)

The system must **NEVER**: diagnose diseases, prescribe medication, recommend dosages,
give emergency treatment advice, or present itself as a medical professional.

The system must **ALWAYS**: stay informational, recommend physician consultation where
appropriate, stay medically conservative (when unsure, escalate urgency, never downplay),
ground explanations in the curated KB, and include disclaimers on every output surface
(UI, summaries, PDFs).

**Design consequence:** anything safety-critical (severity, urgency) is computed by plain
auditable code. AI only *explains* what the rules already decided.

## 6. Success criteria for RC1

- A real Indian diagnostic-lab PDF goes upload → analysis → downloadable PDF, end to end
- ≥ 95% of lab rows in our test set extracted with correct value + unit + range
- Zero hallucinated medical claims in summaries (evaluated against extraction output)
- Every abnormal flag shows its full explanation chain
- All AI calls run on free tiers; deterministic fallback produces a usable (if plainer)
  report even if every model is down
- Test suite green in CI; no PHI ever written to logs

## 7. Release roadmap (context)

| Release | Adds |
|---|---|
| **RC1** (now) | Everything in section 3 |
| **RC2** | Chat with reports, report comparison, LangGraph orchestration, PostgreSQL, Django, session persistence |
| **RC3** | Analytics dashboard, advanced agents, evaluation dashboards, Docker, scalable infra |

## 8. Key risks & mitigations

| Risk | Mitigation |
|---|---|
| OCR quality on phone photos | Confidence scoring + preprocessing + clear "retake photo" UX |
| Free-tier rate limits | Aggressive caching, deterministic-first design, fallback chain, retry backoff |
| AI hallucination | RAG grounding, schema validation, guardrail prompts, hallucination evals |
| PaddleOCR install pain on macOS | Documented setup; Tesseract as emergency dev substitute |
| Beginner overwhelm | Micro-task sprints, one concept at a time (see sprint roadmap) |

---

*MediScan is an informational tool and does not provide medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional.*
