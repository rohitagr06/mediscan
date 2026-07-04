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
