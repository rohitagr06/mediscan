# Sprint 4 Plan — Structured Extraction & the Deterministic Medical Engine

*Mode: PAIR (same split). This is the SAFETY-CRITICAL sprint: it decides
what MediScan calls abnormal and how urgently it tells a person to see a
doctor. Per decision #006, every severity and urgency verdict is computed
by plain, auditable Python — NO AI touches these numbers. The AI (Sprint
5) will only ever *explain* what these rules already decided.*

**Milestone:** OCR/PDF text goes in → a list of `LabResult` objects, each
with a resolved reference range, a severity band, and a direction → plus
one conservative `UrgencyAssessment` for the whole report. Zero AI. Every
verdict traceable to the rule and the numbers that produced it.

**The governing principle — parse vs. judge:** two completely separate
jobs, kept in separate modules. PARSING turns text into raw facts
(name, value, unit, range) and is allowed to be imperfect — it just
reports what it could and couldn't read. JUDGING takes those facts and
applies medical rules to assign severity/urgency, and must be perfectly
auditable. Never let judging logic leak into the parser or vice versa.

---

## Concepts this sprint teaches (in order)

1. **Regular expressions (regex)** — the core tool for pulling
   `Hemoglobin 9.8 g/dL (13.0 - 17.0) L` apart into fields. Taught from
   zero; you'll build the pattern piece by piece.
2. **Tolerant parsing** — OCR text is noisy ("DipsAl" for "DipsAI"). A
   good parser extracts what it can, records what it can't, and NEVER
   crashes or guesses. Unparsed lines become a confidence signal.
3. **A knowledge base as data** — reference ranges and severity rules
   live in reviewable JSON files (knowledge_base/), not buried in code,
   so a clinician could audit them without reading Python.
4. **Reference-range resolution** — report-range-first, KB-fallback
   (decision from the architecture doc): trust the lab's own range when
   present, fall back to generalized adult ranges only when it's missing.
5. **Deterministic severity banding** — turning "how far outside range"
   into Normal/Mild/Moderate/High/Critical by explicit rule, plus
   optional per-test absolute critical thresholds from the KB.
6. **Conservative roll-up** — one Critical finding forces the whole
   report to at least Urgent; urgency is never softer than its worst
   finding. Medical caution encoded as a rule.
7. **Testing pure functions** — the engine is all pure functions
   (inputs → outputs, no side effects), the easiest and most important
   thing to test exhaustively. This sprint has the heaviest test load.

## New dependencies

None expected — this sprint is pure Python (regex, json from the standard
library). That is itself the point: the safety-critical core has zero
external moving parts.

## Tasks

### 4.1 — Concept: regex + parse-vs-judge — OWNER: Rohit (~1.5h)
Playground: build a regex for one CBC line step by step; feel how groups
capture fields. Understand why parsing and judging are separate modules.

### 4.2 — `schemas` for extraction output — OWNER: Rohit (~1h)
A small `ParseOutcome` (or similar): `results: list[LabResult]` (severity
still None — not yet judged!) + `unparsed_lines: list[str]` (what the
parser couldn't read — feeds confidence & explainability). Tests.

### 4.3 — The deterministic line parser — OWNER: Rohit, core (~3h)
`extraction/parser.py`: text → ParseOutcome. Line-by-line regex pulling
test_name, value, unit, reference range, and any printed flag. Tolerant:
a line that doesn't match goes to `unparsed_lines`, never crashes. Claude
writes adversarial tests (OCR noise, missing units, weird spacing).

### 4.4 — Normalization — OWNER: Rohit (~2h)
`extraction/normalization.py`: a synonym map ("Hb"/"HGB"/"Haemoglobin" →
"Hemoglobin") and unit canonicalization, so the engine compares like with
like. Map lives as data. Tests for each synonym.

### 4.5 — The knowledge base + loader — OWNER: pair (~2h)
`knowledge_base/reference_ranges/*.json`: generalized adult ranges +
optional per-test critical thresholds, for the CBC panel + a few common
tests. Claude scaffolds the loader + schema; Rohit authors the KB data
(reviewing each number). Every KB fact is sourced/commented.

### 4.6 — Reference-range resolution — OWNER: Rohit (~1.5h)
`medical/ranges.py`: if the LabResult already has a report range, use it;
else look up the KB range by (normalized) test name; else leave None and
mark the value un-assessable. Report-first, KB-fallback, explicit.

### 4.7 — Severity engine (THE safety task) — OWNER: pair (~3h)
`medical/severity.py`: deterministic banding. We'll DESIGN the rule
together at the top of this task (a real decision, logged): distance
outside the range relative to range width, combined conservatively with
any KB absolute critical thresholds — the MORE severe signal wins. Pure
functions, exhaustively tested, every branch explained.

### 4.8 — Urgency engine — OWNER: Rohit (~2h)
`medical/urgency.py`: conservative roll-up of all severities into one
UrgencyLevel, with human-readable reasons (schema requires ≥1) and the
contributing test names. One Critical ⇒ at least Urgent, never softer.

### 4.9 — Test suite — OWNER: split (~3h)
Rohit: happy-path parser + normalization + range-resolution tests, and
severity/urgency truth-table tests (known value → known band). Claude:
adversarial parser tests + boundary tests (value exactly on a range edge,
missing ranges, contradictory flags).

### 4.10 — Integration — OWNER: pair (~1.5h)
`tests/integration/`: OCR/text of the CBC fixture → parse → normalize →
resolve ranges → severity → urgency, asserting the KNOWN result (Hb 9.8
flagged low/moderate, TLC high, platelets normal, overall Consult Soon).
The first test where a document becomes a medical assessment end to end.

### 4.11 — Sprint close — OWNER: Rohit (~1h)
Decision-log rows (severity rule, any others), README/roadmap/reflections,
architecture status, CI green.

## Exercises

- **Try Yourself:** add one new test (e.g. "Random Blood Sugar") to the KB
  and a fixture line, and watch it flow through with no code change.
- **Debugging Exercise:** Claude hands you an OCR line the parser gets
  subtly wrong; find whether the bug is in the regex or the normalization.
- **Optimization Challenge:** the parser compiles its regex on every call
  — hoist the compile to module load and measure the difference.
- **Architecture Reflection:** why must severity be deterministic and not
  AI-computed, even though an LLM could "read" the report? (5 sentences —
  this is decision #006 in your own words.)

## Definition of done

- [ ] Text → LabResult list → severity/urgency, entirely without AI
- [ ] Every KB number reviewed and sourced; KB is data, not code
- [ ] Parser is tolerant: bad lines recorded, never crash
- [ ] Severity rule logged as a decision, exhaustively tested
- [ ] Urgency is conservative (never softer than worst finding), tested
- [ ] Integration test: CBC fixture → correct medical assessment
- [ ] Fast suite stays fast; CI green
