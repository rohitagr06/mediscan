# Reflections & Sprint Retros

*One honest entry per sprint: what was built, what broke, what it taught.
Facts by the pair; personal notes marked (Rohit) are his to extend.*

---

## Sprint 0 — Foundations (retro)

**Built:** uv project, src/ layout, Ruff+Black+pytest, pre-commit, CI.

**What it taught:** pinning everything (lockfile, hook revs, action
versions) is one philosophy applied in four places — machines only agree
when nothing is left to interpretation. The pre-commit rejection loop
(fail → auto-fix → re-stage → pass) felt like friction on day one and
like a seatbelt by day three.

## Sprint 1 — The Master Schema (retro)

**Built:** the full AnalysisReport schema family; 54 tests; security
hardening (MediScanModel).

**What broke, on purpose:** probing found six silent-acceptance holes
(NaN lab values, hallucinated extra fields ignored, whitespace names,
1 MB strings, bool→1.0). All closed at the base-model level, all frozen
as regression tests.

**Decisions born here:** #011 (no optimistic confidence defaults —
raised by Rohit), #012 (hardened base model), #013 (validated mutation;
frozen=True evaluated and consciously deferred — raised by Rohit).

**The keeper lesson:** the schema guarantees SHAPE, not TRUTH — and
"unknown must never masquerade as fine" appeared three separate times
(severity=None, absent ConfidenceBreakdown, no default scores).

## Sprint 2 — Secure Ingestion & Text Extraction (retro)

**Built:** validators (magic bytes, allowlist, spoof cross-check, size
caps), custom exception family, SecureUploadDir, synthetic fixture
factory, PyMuPDF engine, text-vs-scan router with early exit,
integration suite. 94 tests total.

**Best bug of the project so far:** the off-by-one that became decision
#014. The engine counted page text INCLUDING a trailing newline; the
base model's whitespace stripping (a #012 security feature) removed it
during validation; the schema's own consistency check caught the
disagreement. Two correct components, one wrong combination — a true
integration bug, found by Rohit's first real extraction run. Fix:
char_count became a computed field. Principle: derived values are
measured, never remembered.

**Process lesson (the phantom files):** three times, delivered files
were silently reverted to older versions. Mechanism: Cursor tabs held
stale buffers, and a later Cmd+S overwrote newer on-disk content.
Countermeasure now in use: close/revert tabs after files change on
disk, and read `git status` before every commit.

**Architecture Reflection — why does the router live in ocr/, not
ingestion/?** The case for ocr/: the router's question ("does this need
OCR?") and its tools (PyMuPDF, text counting) belong to the
document-reading domain; ingestion's domain is safety, and it should
end when the file is proven safe and stored. The case for moving it:
the router runs immediately after ingestion in the pipeline, so
proximity-in-time argues for proximity-in-code. We kept it in ocr/
because modules should group by RESPONSIBILITY, not by execution order
— execution order changes (RC2 adds queues), responsibilities don't.
(Rohit: add your own take here after sitting with it.)

**Carried forward to Sprint 3:** the corrupt-open try/except pattern now
exists twice (engine, router). Third occurrence triggers the refactor
into a shared helper — twice is coincidence, three times is a refactor.

## Sprint 3 — OCR for Scans & Photos (retro)

**Built:** the OcrEngine contract (an abstract base class), the PaddleOCR
image engine with honest per-line confidence, image preprocessing, the
scanned-PDF path (render → clean → recognize), and a DocumentType→engine
factory. MediScan can now read pixels, not just text.

**The PaddleOCR bet paid off (#015):** decision #008 hedged that Paddle
might not install on Apple Silicon, with Tesseract as an escape hatch.
The timeboxed experiment (3.1) installed cleanly on the first try — so
the escape hatch stays designed but unused, and the OcrEngine contract
that would have made the swap painless now just makes future engines
easy to add.

**Three decisions, three flavours:** #015 was an EXPERIMENT resolving an
old bet; #016 was a MEASUREMENT (preprocessing kept because it bought
+0.08 confidence on a degraded photo, not because it "felt right"); #017
was a PLAN ADAPTATION (the factory keyed by DocumentType, not backend,
because reality — one backend — made the planned design premature
abstraction). Good engineering replaces "obviously" with evidence.

**Best lesson — OCR is guessy:** even at 0.98 confidence, the scanned
CBC read "DipsAl" for "DipsAI" (an I as a lowercase L) and truncated a
row. Seeing this firsthand is exactly why Sprint 4's parser must be
TOLERANT — it cannot demand perfect spelling, it must find lab values
amid OCR noise.

**Security audit (mid-sprint):** a whole-codebase review surfaced real
hardening gaps that synthetic fixtures never exercise — image
decompression bombs (a tiny file that decodes to gigapixels), unbounded
config knobs (MEDISCAN_RENDER_DPI=100000 → OOM), no page cap on scanned
PDFs (a 5000-page PDF as a DoS), and the corrupt-open try/except
duplicated a third time (the retro tripwire, tripped → extracted into a
shared open_pdf helper). All fixed, all tested. Lesson: "works on my
fixtures" and "safe against hostile input" are two different bars.

**Process — the file-bridge phantom, again:** the device bridge served
stale copies of some files during the audit, so we shifted to a
findings-report-then-patch flow and used `git diff` (against the real
committed state) as the reliable review surface. When a tool is
unreliable, route around it with one you trust.

**Carried forward:** observability is still entirely absent — the
architecture note now says so explicitly, so no one assumes logging
exists. It arrives in Sprint 7.

## Sprint 4 — Extraction, Normalization & the Deterministic Medical Engine (retro)

**What we built:** the safety-critical core. A tolerant line parser
(text → `LabResult`s, unreadable lines preserved, never a crash),
name/unit normalization as data, report-first/KB-fallback range
resolution, hybrid severity banding (Option B fraction-toward-critical
where the KB has sourced thresholds, Option A percentage-from-boundary
capped at HIGH where it does not — #020), a pure `assess_lab_result`
that never mutates its input (#021), and a conservative urgency roll-up
where the worst finding wins and one Critical forces Seek Immediate Care
(#022). An end-to-end integration test now turns the CBC fixture into a
Consult-Soon verdict with zero AI involved.

**Parse vs. judge, kept honest:** the biggest design win was refusing to
let judging logic leak into the parser. The parser reports what it read;
the engine decides what it means. Because the engine is pure functions,
the truth-table tests are exhaustive and trivial — every band, both
directions, every boundary value, all pinned.

**Two safety instincts that paid off:** (1) config cutoffs get a
cross-field validator so an inverted `.env` can't silently under-report
severity; (2) "unknown never masquerades as fine" shows up twice — an
un-assessable value floors urgency at Consult Soon, and the review caught
that an all-mild report must not say "within normal limits".

**An emergent safety gap found in review — and fixed (#023):** because the
parser only accepts rows that print their own range (#018) and resolution
is report-first, the KB's *critical* thresholds were never consulted in the
real text→verdict flow — so a critically low value in a report that prints
a normal range banded as HIGH, not CRITICAL. No component was buggy; three
individually-correct decisions interacted badly, which no unit test could
catch. Decision #023 fixes it: the report keeps its normal range, but KB
critical thresholds are MERGED in when they sit strictly outside that range
(a conflicting threshold is dropped — the report wins). Criticals now live
in a `CriticalThresholds` value object with a derived source, and the
engine stays 100% deterministic. A regression test proves `Hb 3.0` in a
printed 13-17 range now reaches CRITICAL → Seek Immediate Care.

**Process:** the file-bridge stale-copy problem returned hard — half the
staged files were outdated. We routed around it by bundling the live tree
into a single fresh file on disk and staging that, then verifying every
file against its live checksum before reviewing. Trust, but checksum.

**Carried forward:** KB numbers are still STARTER values pending sourced
review before any clinical use (#019); observability still absent until
Sprint 7. #023's derived `critical_source` assumes criticals are KB-only —
revisit if reports ever print their own.

## Sprint 5 — The AI Explanation Layer (retro)

**What we built:** the AI *platform*, not just AI features. One
medicine-blind `LLMClient` contract; ONE `OpenAICompatibleProvider` class
that is all three rungs of the #004 chain (Gemini, GPT-4.1-mini, Phi-4) as
configs; versioned `PromptTemplate` objects whose `build()` fences facts
against prompt injection; `generate_structured` with exactly one
repair-retry; a resilient chain with exponential backoff; deterministic
templates as the no-AI floor; a regex guardrail that blocks
dosage/prescription/diagnosis language and falls back to those templates;
and `ExplanationProvenance` on every output. Verified live end to end.

**The best design move was Rohit's:** collapsing two SDKs into one. The
original plan had `google-genai` for Gemini and `openai` for GitHub
Models; Rohit spotted that both endpoints speak the OpenAI API, so the
whole provider layer became one class + three builder functions (#024).
Fewer dependencies, one place for timeouts/secrets/errors.

**A real 429 proved the design early:** Gemini's free tier rate-limited us
on the very first live call (limit 0 for that model id). The provider
normalized it to a clean `LLMError` with no key and no content leaked —
and it made the case for the chain + deterministic floor better than any
argument could.

**Testing lesson:** the first adversarial suite draft was slow (43s) and
had one failure — the chain was really sleeping through backoff in tests,
and a one-shape fake couldn't serve four prompts. Fixes: an autouse
fixture zeroing retries (never sleep in tests) and a shape-aware fake.
Mock-first now runs in 0.08s with no keys and no network.

**Carried forward:** grounding facts are hand-fed this sprint; Sprint 6
(RAG) changes only where they come from. Honor a 429's `retryDelay` in
the chain (RC2). Wire `ReportExplanations` into `AnalysisReport` during
Sprint 7 orchestration. KB sourcing homework (#019) still open.
## Sprint 6 — RAG & the Knowledge Base (retro)

**What we built:** the open-book. A curated, *sourced* knowledge base (the
5 CBC tests, every statement cited) validated at load; a chunker that splits
each entry into individually-retrievable snippets; local BGE-small embeddings
behind an INJECTABLE seam (real model in production, a deterministic
word-overlap fake in tests — zero download, zero network); an in-memory
ChromaDB index rebuilt from the JSON each run; a bounded retriever; grounding
wired into the existing Sprint-5 FACTS block so the AI now answers from
sourced notes, not memory; and `grounding_sources` recorded on every AI
explanation (#028). The #006 safety boundary is now MACHINE-CHECKED — a test
parses every module under `medical/` and fails if one ever imports `rag/`.

**The payoff moment:** the real model retrieved by MEANING, not words — a
"feeling tired and weak" query that shares almost no vocabulary with the KB
surfaced the hemoglobin/anemia snippets. The fake embedder can't do that
(it's word-overlap), which is exactly why the slow real-BGE test exists: it
guards the one thing the fast fake cannot prove.

**Two bugs the tests caught, both about process not medicine:** (1)
`EphemeralClient()` does not isolate — it shares one in-process backend, so a
fixed collection name collided ("already exists") the moment a second index
built in one run; fixed with a unique name per build (production, being
`@cache`d, never noticed). (2) ChromaDB's base `EmbeddingFunction.__init__`
is a warning-only stub, so "silencing" the warning by CALLING `super()`
actually re-triggered it — the fix was to override and NOT call super. Same
lesson twice: a library's defaults encode assumptions you only learn by
running against the real thing.

**Design win carried from Sprint 5:** because the FACTS seam already existed,
grounding was an ENRICHMENT, not a rewrite — the prompts already said "use
only these facts"; we just gave them better facts. Building the prompt seam a
sprint early paid for itself.

**Carried forward:** the KB is still only CBC and its ranges are STARTER
values pending sourced review (#019); Sprint 6.5 expands the deterministic
engine to the full-body panels and grows the KB — the RAG layer absorbs it
with no code change, which was the whole point. Retrieval is top-K with no
re-ranking or score threshold yet; revisit if quality needs it.

## Sprint 6.5 — Full-Panel Scope Expansion (retro)

**The sprint's real product was a boundary, not a feature.** Widening from
CBC to a full-body checkup sounded like "add more tests", but the hard part
was deciding what happens to a test we HAVEN'T vetted. The answer —
acknowledge-don't-skip (#030) — came from Rohit: a user's out-of-scope result
must be shown, never silently dropped and never graded as if we understood it.
That reframed the whole sprint around a `CoverageResult` (assessed /
acknowledged / unparsed) and an assessment POLICY kept deliberately SEPARATE
from the medical KB. Keeping "what we grade" (product policy) apart from "what
a value means" (medical fact) is the decision I expect to age best: scope now
grows by adding a policy row, not by editing medicine.

**The safety win is a test that asserts nothing happens.** The sharpest test
of the sprint puts a PSA at 50× its limit next to a normal haemoglobin and
demands the verdict stay ROUTINE. It's the #006 boundary stated as an
adversary: an alarming ACKNOWLEDGED value cannot move urgency, because grading
is gated by an allowlist, not by whether a number looks scary. Writing the
test that proves a scary input is *inert* felt more valuable than any of the
tests that prove abnormal inputs escalate.

**Sex-awareness matters less than it looks — and that's the point (#029).**
Because resolution is report-first (#023) and real reports print sex-correct
ranges, the patient's sex almost never changes a graded verdict; it only
steers the KB FALLBACK. The end-to-end fixture makes this concrete and honest:
the same 12.5 haemoglobin bands LOW for the male variant and NORMAL for the
female one *because the printed ranges differ*, while the unit tests prove the
fallback picks the right block (and unions both for unknown sex). Building the
union-for-unknown as the conservative default means an absent range can never
manufacture a false abnormal.

**The parser's growing pains confirmed a deferred decision.** Getting one
real Tata/Lal/Labsmart report after another to parse cleanly meant piling
special cases onto the regex grammar (thousands-commas, trailing method
columns, pre-flags, wrap artifacts). Each fix was justified, but the
accumulation is exactly the signal that the composable-recognizer refactor
parked for Sprint 7 is the right call — the grammar is near the edge of what
one regex should carry.

**A process bug worth remembering:** I reasoned about task numbering and the
plan from a STALE sandbox copy of docs/14 and told Rohit the numbering had
drifted when it hadn't — he corrected me. The fix (and the standing rule from
Sprint 6) is the same: read the LIVE file on the Mac before reasoning about
its contents, never a cached stage. Cheap to avoid, embarrassing to hit twice.

**Carried forward:** several later-wave tests (HDL/glucose/thyroid values not
in the sample reports) still lean on standards rather than a real printed
range; Free T3/T4 sourcing is the softest (assay-dependent); Hemoglobin's
critical thresholds are still example-sourced. The KB integrity checks now
make any policy↔KB drift a loud failure, which is the safety net that lets the
KB keep growing without silent holes.

## Sprint 7 — Confidence, Orchestration & Explainability (retro)

**The orchestrator was the smallest file in the sprint — because the design
earned that.** Wiring seven stages into `analyze_document` took barely 70
lines, and it owns NO medical logic: it just calls each stage and hands the
typed object to the next. That only worked because every stage was already a
pure, contract-bound unit (OcrEngine, LLMClient, pure `assess_lab_result`,
injectable retriever). The conductor being trivial is the dividend of six
sprints of boundaries — the best evidence the architecture was right.

**Async without rewriting the world.** The report-level design meant the
concurrency unit was the four OUTPUTS, not per-finding chains. Rather than
rewrite the whole AI layer to a native async SDK, I ran the existing SYNC
chain in a thread executor under `asyncio.gather` + `wait_for` (#032). That
bought real concurrency, per-output timeouts, and graceful fallback for ~30
lines — and the honest cost (executor threads aren't force-killed on timeout)
is documented, not hidden. Sync-first then async also kept two lessons apart:
get the pipeline correct, *then* make it fast.

**Confidence is a blend precisely so it can be honest.** One number would hide
WHY trust is low. Splitting it into ocr/extraction/validation/grounding with a
fallback penalty (#031) means a low score points at the stage that caused it —
and a startup weight-sum check makes a mistyped weight crash rather than
silently emit a >1 "confidence." Determinism here is the whole point: no AI
gets to grade its own trustworthiness.

**Two bugs my cloud sandbox structurally could not catch.** Ruff (`B905`
`zip(strict=)`, `S110` try/except/pass) and the ChromaDB corrupt-cache
recovery (`'RustBindingsAPI' has no attribute 'bindings'`) all slipped past me
because the sandbox has neither `ruff` nor `chromadb`. Rohit's pre-commit hooks
and Mac test run caught every one. The lesson is a workflow one, not a code
one: when the authoring environment can't run part of the toolchain, the local
gate IS the test — and the fix for the corrupt-cache bug (clear ChromaDB's
in-process system cache before rebuilding) was a genuine correctness
improvement the gated test forced out.

**The parser refactor proved a restraint principle.** The review said "refactor
the accreting parser"; the disciplined move was to decompose (one tokenizer +
named recognizers, #033) rather than rewrite the matching strategy, so the
three real reports could not regress. Retiring a smell is not the same as
rewriting the thing that works — and behaviour-preservation was provable (35
tests unchanged).

**Carried forward:** RC1 explanations are report-level; per-finding chains are
an RC2 enhancement (needs a schema change). Executor threads survive a timeout
in the background — a native async SDK would fix that (RC2). The persisted
index cache path will need revisiting for Hugging Face deployment (Sprint 8).
The #019 KB sourcing review remains the one clinical-use gate. Next stop:
Sprint 8 — the UI, the PDF, and shipping RC1.
