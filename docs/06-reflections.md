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

**A real gap found in review (open decision):** because the parser only
accepts rows that print their own range (#018) and resolution is
report-first, the KB's *critical* thresholds are never consulted in the
real text→verdict flow — so CRITICAL is currently unreachable end-to-end.
A critically low value in a report that prints a normal range would band
as HIGH, not CRITICAL. The fix (attach KB critical thresholds to
report-ranged values by canonical name, keeping the report's normal band)
is consistent with #020 and is the top candidate for the next decision.

**Process:** the file-bridge stale-copy problem returned hard — half the
staged files were outdated. We routed around it by bundling the live tree
into a single fresh file on disk and staging that, then verifying every
file against its live checksum before reviewing. Trust, but checksum.

**Carried forward:** the report-range/critical-threshold decision above;
KB numbers are still STARTER values pending sourced review before any
clinical use (#019); observability still absent until Sprint 7.
