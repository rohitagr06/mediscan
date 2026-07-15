# Sprint 8 Plan — UI, PDF & Ship (RC1 live)

*Mode: PAIR (Rohit writes core logic; Claude scaffolds, explains every line at
beginner level, writes tests, reviews). This is the LAST RC1 sprint: it wraps
the one-call engine from Sprint 7 in a face a stranger can use — a web UI, a
downloadable PDF report — and ships it.*

**Milestone: RC1 LIVE.** A stranger opens a URL, uploads a lab report, and gets
back a clear, colour-coded analysis plus a downloadable PDF — powered by the
`analyze_document()` pipeline, still safe and still working when every AI model
is down.

---

## Scope for this sprint (confirm the forks at 8.1)

Sprint 7 finished the engine: `analyze_document(path) -> AnalysisReport`. Sprint
8 adds only PRESENTATION and DEPLOY around it — no new medical logic. The work
is four things: **package** the app so it runs when installed, **render** the
report (PDF + web), **evaluate** it honestly, and **deploy** it.

**Open questions to confirm at 8.1 (each with my leaning):**

1. **Deploy target.** Hugging Face Spaces (per the roadmap) vs local-only for
   RC1. **Leaning:** HF Spaces — it's free, Gradio-native, and "a stranger can
   use it from a URL" is the RC1 milestone.
2. **Public-demo secrets.** A public Space with real API keys risks abuse/cost.
   **Leaning:** default the public Space to **deterministic demo mode**
   (`providers=[]` — no keys, fully safe, still a complete report), with keyed
   AI as an opt-in for a private/local run. This keeps secrets out of a public
   Space entirely.
3. **Evaluation set.** The real Tata/Lal/Labsmart reports are PHI (#010) and
   live only on Rohit's Mac. **Leaning:** the eval runs on SYNTHETIC fixtures in
   CI; the real-report accuracy check runs LOCALLY, never committed.
4. **PDF engine.** WeasyPrint (per the roadmap) needs system libraries
   (pango/cairo) that HF Spaces must install. **Leaning:** WeasyPrint, with the
   system deps declared for the Space; if it fights the Space, fall back to a
   print-friendly HTML the browser can "Save as PDF".

---

## First, the plain-English concepts (read before any code)

**1. Packaging & package-data.** Until now we've run from the source tree. A
deployed app runs from an INSTALLED wheel — and a wheel only ships the files you
declare. Our knowledge base is JSON *inside* the package (#019); we must tell
the build to include `knowledge_base/**/*.json`, then prove the built wheel
actually contains it. Miss this and the deployed app has an empty KB.

**2. Gradio.** A Python library that turns a function into a web UI. We write
`analyze(file) -> rendered results`, and Gradio gives us the upload box,
progress bar, and output panels — no HTML/JS project. The whole UI is a thin
wrapper over `analyze_document()`.

**3. WeasyPrint PDF.** Renders HTML+CSS to a real PDF. We build one HTML
template from an `AnalysisReport` — both summaries, a colour-coded findings
table, the urgency badge, the acknowledged-tests section, confidence, and the
mandatory disclaimer — and WeasyPrint prints it. HTML is easy to test (assert on
the string) before it ever becomes a PDF.

**4. The evaluation pass.** Before shipping a medical tool we measure it, not
just "it runs": extraction accuracy (did we parse what we should?), a
hallucination check (are AI outputs grounded / does the guardrail catch
overreach?), and confidence sanity (degraded inputs score lower). Honest
numbers, written into the docs.

**5. Deploy.** A Hugging Face Space is a git repo with an `app.py` entry point
and a dependency spec. We push, it builds, it serves. Two deploy-specific
gotchas we already flagged: the persisted RAG index cache path (#034) needs a
WRITABLE location on the Space, and secrets must come from Space settings, never
the repo.

---

## The safety spine (unchanged — presentation must not weaken it)

- **#006 stays absolute.** The UI and PDF only RENDER what `analyze_document`
  decided. They never re-compute severity/urgency and never call AI directly.
- **#010 (no PHI) extends to the new surfaces.** Uploaded files live in the
  secure temp dir and are cleared; logs stay metrics-only; the PDF is handed to
  the user, never stored server-side; the public demo processes nothing it
  retains.
- **The disclaimer is unremovable** (schema default) and appears on both the UI
  and the PDF by construction.
- **Degrades gracefully.** Demo mode (no AI) still produces a full report — the
  deterministic verdict is the product; AI is the polish.

---

## Tasks

### 8.1 — Kickoff + confirm deploy decisions — OWNER: pair (~1h)

**What:** Concept session on packaging/Gradio/WeasyPrint/deploy; lock the four
open questions above. **Why:** deploy choices (secrets, PDF engine, cache path)
shape every later task. **Done when:** the four forks are decided and written
down.

### 8.2 — Package the KB + built-wheel test (#019) — OWNER: Rohit core + Claude test (~1.5h)

**What:** Declare `knowledge_base/**/*.json` as package data in `pyproject.toml`;
add a test that builds the wheel (`uv build`) and asserts the JSON is inside it.
**Why:** a deployed install with an empty KB would silently lose all grounding +
fallback ranges. **Safety note:** this is the difference between "works on my
machine" and "works when shipped". **Done when:** the built wheel contains every
KB file and a fresh install can load ranges + snippets.

### 8.3 — WeasyPrint PDF report — OWNER: Rohit core + Claude scaffold (~3h)

**What:** `reports/` — render an `AnalysisReport` to a clinical PDF via an HTML
template: patient + doctor summaries, a colour-coded findings table (severity →
colour), the urgency badge, the acknowledged-tests section (shown, not graded),
confidence, MediScan branding, and the disclaimer. Split render-HTML from
render-PDF so the HTML is unit-testable. **Why:** the PDF is the takeaway
artifact. **Safety note:** the disclaimer is templated in unconditionally; the
PDF is generated in memory and returned, never written to a server path.
**Done when:** a sample report → a valid multi-section PDF; the acknowledged
bucket and disclaimer are present.

### 8.4 — PDF/HTML render tests — OWNER: Claude (~1.5h)

**What:** assert the rendered HTML contains every required section (both
summaries, urgency level, each assessed finding with its severity class, the
acknowledged tests, the disclaimer) and NO dosage/diagnosis text; a smoke test
that WeasyPrint produces non-empty PDF bytes (skipped where system libs
absent). **Done when:** green; the disclaimer/■coverage sections can't silently
vanish.

### 8.5 — Gradio app skeleton — OWNER: pair (~2.5h)

**What:** `ui/` — a Gradio app: upload → progress → `analyze_document` → results.
One `analyze(file, demo_mode) -> (rendered, pdf_path)` function is the seam.
**Why:** the milestone's "a stranger can use it". **Safety note:** uploads go
through the existing `validate_upload` + `SecureUploadDir` front door; the temp
file is cleaned up. **Done when:** `uv run` launches locally; a synthetic PDF →
colour-coded results + urgency badge + a PDF download.

### 8.6 — Result rendering (colour-coded, badged) — OWNER: Rohit core + Claude review (~2h)

**What:** map severity → colour, urgency level → a prominent badge; render the
assessed findings, the acknowledged bucket (clearly "shown, not graded"),
confidence, and the disclaimer; wire the PDF download button. **Why:** clarity
is a safety feature — a scary value must read as scary, an out-of-scope test
must read as "see a doctor". **Done when:** a full report renders legibly for a
non-technical user.

### 8.7 — Demo mode + deploy config — OWNER: pair (~1.5h)

**What:** a `demo_mode` that runs `providers=[]` (no keys) so a public Space is
safe and free; env-based secrets for a keyed run; point the persisted RAG index
cache (#034) at a writable Space path. **Why:** ship publicly without leaking
keys or paying per click. **Safety note:** demo mode still returns a complete
deterministic report — the safe default. **Done when:** the app runs both with
and without AI keys, and the index cache works on a read-only-repo Space.

### 8.8 — Application-level E2E test — OWNER: Claude (~2h)

**What:** drive the UI's `analyze(...)` seam end to end on a synthetic file →
assert a rendered report + a generated PDF; deterministic path (no AI, no net).
**Why:** proves the whole stranger-facing path, not just the engine.
**Done when:** green and offline (heavy OCR gated as before).

### 8.9 — Evaluation pass — OWNER: pair (~3h)

**What:** an eval harness producing honest metrics: extraction accuracy on
synthetic fixtures (parsed vs expected), a hallucination check (every AI output
grounded or guardrailed; zero dosage/diagnosis leakage), and confidence sanity
(degraded input scores lower). Real-report accuracy runs LOCALLY on Rohit's Mac
(#010), synthetic runs in CI. **Why:** you don't ship a medical tool on "it
runs". **Done when:** metrics are recorded in docs; no un-guardrailed
hallucination on the eval set.

### 8.10 — Deploy to Hugging Face Spaces — OWNER: pair (~2h)

**What:** Space repo (`app.py` entry, uv/requirements, system libs for
WeasyPrint, writable cache path, secrets in Space settings, demo mode on).
**Why:** the RC1 milestone — a public URL. **Safety note:** the public Space
retains no uploads and exposes no keys. **Done when:** RC1 is LIVE; a stranger
uploads a synthetic report and gets analysis + PDF at a URL.

### 8.11 — Tests throughout + coverage ratchet — OWNER: split (~1.5h)

**What:** fill gaps across reports/ and ui/; raise the CI coverage floor toward
the new baseline (never down). **Done when:** fast suite green + gate reflects
reality.

### 8.12 — Sprint close + RC1 retro — OWNER: Rohit (~1.5h)

**What:** log decisions (#035 PDF rendering split; #036 Gradio demo-mode default;
#037 packaging + HF-Spaces deploy); roadmap Sprint 8 ✅ → **RC1 LIVE**;
architecture banner → shipped; README (live URL + a screenshot); Sprint 8 +
whole-RC1 reflection; `project-status.md`; confirm CI green. **Done when:** docs
match the shipped reality and the live URL is in the README.

---

## Cross-cutting: security, privacy, production-readiness

- **Privacy:** uploads validated + temp-only + cleared; PDF returned, never
  stored; public demo retains nothing; logs stay metrics-only (#010).
- **Secrets:** only via Space settings / local `.env` — never the repo (the
  gitleaks hook + CI job stay the backstop).
- **Reliability:** demo mode guarantees a working public app independent of AI
  provider uptime or quota.
- **Deploy gotchas already flagged:** WeasyPrint system libs; writable RAG
  cache path (#034); package-data in the wheel (#019/8.2).

## Appendix — Decisions locked at 8.1 (2026-07-15)

All four forks were confirmed on the recommended path. These are binding for
Sprint 8 and will be formalized as decisions #035–#037 at 8.12.

| # | Fork | Decision | What it binds |
|---|---|---|---|
| 1 | Deploy target | **Hugging Face Spaces** | 8.10 targets a public Space: `app.py` entry + dependency spec + `packages.txt` for system libs. RC1 milestone stays "a stranger opens a URL". |
| 2 | Public-demo secrets | **Deterministic demo mode by default** | The public Space runs `providers=[]` — no API keys exist on the Space at all. The report is fully deterministic (engine verdict + template explanations). Keyed AI is opt-in for local/private runs via `.env` / Space secrets on a private Space. Zero abuse/cost surface. |
| 3 | Evaluation set | **Synthetic in CI + real local** | 8.9's eval harness runs on synthetic fixtures in CI, forever repeatable. The real Tata/Lal/Labsmart accuracy check runs per release, LOCALLY on Rohit's Mac, and only aggregate numbers (no report text) enter the docs — #010 fully honored. |
| 4 | PDF engine | **WeasyPrint** | 8.3 renders HTML → PDF via WeasyPrint; pango/cairo declared in the Space's `packages.txt`. Escape hatch stands: if the Space build fights it, ship print-friendly HTML and log the swap. |

**Consequences carried into later tasks:** 8.7 builds `demo_mode` around
decision 2 (the default for the public Space); 8.9 splits its harness per
decision 3; 8.10 needs `packages.txt` (decision 4) + a writable RAG cache path
(#034) + no secrets in the Space repo (decision 2).

## Explicitly deferred (RC2, not this sprint)

- Django + PostgreSQL + auth/accounts + saved history (#003).
- Native async provider SDK for true timeout cancellation (#032); per-finding
  explanation chains (#032).
- Age-specific ranges (#029); qualitative urine/micro results (#027);
  non-English reports.
- Re-ranking / score thresholds in RAG (#028); a hosted/shared vector store (#034).
- The full scanner-pipeline parser rewrite if a new format demands it (#033).
