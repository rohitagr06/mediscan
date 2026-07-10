# Sprint 6.5 Plan — Full-Panel Scope Expansion

*Mode: PAIR (Rohit writes core logic and authors + sources the medical
content; Claude scaffolds, explains every line at beginner level, writes
adversarial tests, reviews). This sprint grows MediScan from "reads a CBC"
to "reads a standard full-body health checkup" — for BOTH sexes — without
weakening a single safety guarantee.*

**Milestone:** MediScan takes a real full-body checkup report (CBC + liver +
kidney + lipids + electrolytes + glucose/HbA1c + thyroid + vitamins + iron +
numeric urine), reads the patient's sex from the report, applies the right
reference ranges, and produces a flagged, severity-ranked, urgency-assessed,
grounded explanation — while ACCOUNTING FOR every other test in the report
(never silently skipped), still with zero AI in the deciding, and still able
to run when every AI model is down.

---

## Why this sprint exists (decision #027)

Back in Sprint 0 we scoped RC1 as "CBC only" (#005). That was a
miscommunication — MediScan was always meant to read a standard full-body
checkup. Decision #027 corrected the scope. Sprint 6 deliberately built RAG
on the small CBC knowledge base *first*, precisely because the RAG layer is
**panel-agnostic**: the knowledge base is data, so growing it later needs no
RAG code change. This sprint is the other half — teaching the deterministic
engine (the part that actually decides severity and urgency) to handle the
rest of a checkup.

**The important reframing:** most of this sprint is *data* (authoring and
sourcing reference ranges + knowledge for many tests), and only a little is
*code* (a few focused engine upgrades). That ratio is the whole point of the
architecture we built.

---

## First, the plain-English concepts (read this before any code)

Three new ideas, each simple once named.

**1. One-sided reference ranges.**
A CBC prints ranges with two ends: Hemoglobin `13.0 - 17.0`. But a lot of a
checkup prints ranges with only ONE end:

- LDL cholesterol: `< 100` (only an upper limit — lower is fine)
- Triglycerides: `< 150` (upper limit only)
- HDL cholesterol: `> 40` (only a lower limit — higher is fine)
- HbA1c: `< 5.7 %` (upper limit, and note the `%` unit)

Our parser today (decision #018) only recognizes a row when it sees a
two-sided range like `13.0 - 17.0`. So it literally cannot read an LDL line.
Teaching it one-sided ranges is the single biggest parser change this sprint.
Our `ReferenceRange` schema is *already* ready for this — it allows `low` OR
`high` to be missing, requiring only that at least one exists — so this is a
parser change, not a schema change.

**2. One-sided ranges change what "abnormal" means (a safety subtlety).**
If a range is `LDL < 100`, then a value of `60` is NORMAL, not "low." There
is no "too-low LDL" in this model — only "too-high." So the severity engine
must learn: **only band on the side that has a bound.** For an upper-bound-only
test, a value under the bound is normal and a value over it is graded; the
"low" direction simply doesn't exist. Getting this right matters — flagging a
healthy low LDL as "abnormal" would be a false alarm, and inventing a
severity for an unbounded side would be making up medicine (violates #006).

**3. Sex-aware reference ranges.**
Some tests have *different* normal ranges for males and females — Hemoglobin
(men run higher), Creatinine, and especially Ferritin (men's normal floor is
far higher than women's). To band these correctly we need the patient's sex,
and we read it **from the report** (reports print "Sex: Male" / "Gender: F").
Two consequences:
- A tiny new step that extracts the patient's sex from the report text.
- The reference-range knowledge base entries gain optional male/female
  variants; when the report itself prints a range we still trust that (it's
  already sex-correct), so sex mainly affects the KB *fallback* ranges.
- When the report doesn't state sex, we fall back conservatively (details in
  the tasks — this is a real decision we'll make deliberately).

---

## ⚠️ Scope: filtering the "master list" (the most important section)

Rohit gathered an excellent, comprehensive pathologist's master list of
checkup tests. It is far broader than MediScan should *act on*. **A core
discipline of this project (#006) is that MediScan only auto-ASSESSES a test
when a number-out-of-range has a safe, meaningful, patient-appropriate
interpretation.** (Note: "not assessed" does NOT mean "ignored" — see the next
section. Every test is still surfaced.) Many tests fail the assessment bar —
not because they're unimportant, but because a deterministic tool telling a
patient "this is urgent" from a raw number would be misleading or harmful. We
sort every test into three tiers.

### The inclusion rule (memorize this)

A test is ASSESSED by MediScan's deterministic engine ONLY if ALL are true:
1. It yields a **numeric** value with a **defined reference range**.
2. Being out of range has a **reasonably monotonic, interpretable** meaning
   we can band (higher and/or lower maps to "more concerning").
3. Explaining it to a layperson without a clinician present is **safe** and
   not needlessly alarming.
4. It fits the #027 checkup panels.

### Tier A — ASSESSED in RC1 (build this sprint)

Numeric, safely bandable, patient-appropriate, in #027. This is our target.

| Panel | Tests |
|---|---|
| **CBC (extend)** | already have Hemoglobin, TLC, Platelets, Hematocrit, MCV; **add** MCH, MCHC, RDW, RBC count, and the differential % (Neutrophils, Lymphocytes, Monocytes, Eosinophils, Basophils), plus ESR |
| **Liver (LFT)** | Total/Direct/Indirect Bilirubin, AST (SGOT), ALT (SGPT), ALP, GGT, Total Protein, Albumin, Globulin, A:G ratio |
| **Kidney (KFT)** | Creatinine (sex-aware), Urea, BUN, Uric Acid; eGFR treated as a reported value if present |
| **Electrolytes/minerals** | Sodium, Potassium, Chloride, Bicarbonate, Calcium, Ionic Calcium, Phosphorus, Magnesium |
| **Glycemic** | Fasting Glucose, Post-Prandial Glucose, HbA1c |
| **Lipid** | Total Cholesterol, Triglycerides, HDL, LDL, VLDL, Non-HDL (mostly one-sided ranges) |
| **Thyroid** | TSH, Free T3, Free T4 |
| **Vitamins** | Vitamin D (25-OH), Vitamin B12 |
| **Iron studies (COMMON — both sexes)** | Serum Iron, TIBC, Transferrin saturation %, Ferritin (strongly sex-aware) |
| **Urine (numeric only)** | Urine Microalbumin/Creatinine ratio (ACR); numeric urine chemistry where numeric |

> **Correction to the source list:** iron studies belong in the COMMON panel
> (both sexes get them). Ferritin's normal floor is just very different by sex,
> which is exactly what sex-aware ranges handle — it is not a female-only test.

### Tier B — DEFER (numeric, but advanced / needs extra care)

Real numbers, but each needs nuance (risk-stratification context, calculated
inputs, or timing) that RC1 shouldn't shortcut. **Acknowledged, not assessed**
(see next section). Park the *assessment* for after RC1.

- Advanced cardiac markers: hs-CRP, Homocysteine, Lp(a), Apo-A1, Apo-B, NT-proBNP
- HOMA-IR (a *calculated* value) and Fasting Insulin (its input)
- Coagulation: PT/INR, aPTT
- Basal hormones with timing rules: Cortisol (8 AM draw)

### Tier C — NEVER ASSESSED in RC1 (safety) — but still acknowledged

These must never receive a MediScan severity/urgency from a raw number. They
are still surfaced to the user (see next section), just not graded.

- **Tumor markers** (CEA, AFP, CA 19-9, PSA/Free PSA, CA-125, HE4, CA 15-3):
  elevated values have high false-positive rates and only mean something in an
  oncology workup; a "severity/urgent" label here would frighten or mislead.
- **Infectious-disease serology** (HIV, HBsAg, Anti-HCV, VDRL/TPHA, malaria,
  dengue): results are reactive/non-reactive and life-alteringly sensitive —
  auto-explaining a reactive result to a patient is unacceptable.
- **Reproductive hormones** (FSH, LH, Estradiol, Prolactin, Testosterone,
  SHBG): meaning depends on menstrual-cycle phase / time-of-day / clinical
  context, so a fixed range would mislead.
- **Qualitative results** (urine colour/turbidity, protein "Trace/Present",
  peripheral smear, stool ova & parasites, stool FIT, ANA pattern/titre):
  deferred by #027; no numeric band applies.

> **Why spell this out?** Deciding what NOT to grade is senior engineering.
> This tiering is a decision we'll log (candidate **#029**): *MediScan
> auto-assesses only numeric tests with safe, monotonic, patient-appropriate
> interpretations; oncology, serology, and hormone panels are excluded from
> deterministic assessment in RC1 — but never dropped from the report.*

> **MediScan is an analyzer, not a recommender.** The master list's age/sex
> "matrix" (who should get which test at which age) belongs to a *screening
> recommendation* engine. MediScan reads a report that already has results; it
> interprets whatever appears, regardless of age. So the age matrix is out of
> scope by product definition, and age-specific ranges stay parked (#027).

> **Parked (not tests):** the pre-analytical notes (12-hour fasting, morning
> draws, biotin interference) describe *sample collection*, not our engine.
> Good future material for disclaimers or a confidence signal — parked.

---

## Never skip a test: ASSESS Tier A, ACKNOWLEDGE the rest (safety requirement)

*Raised by Rohit: a real report will contain tests outside RC1 the day we
ship. The tool must not silently skip them — it must still surface them.*

Silently dropping a test the user can see on their own report is unsafe: the
absence reads as "fine," violating "unknown never masquerades as fine" (#011).
But "don't skip" does **not** mean "grade everything" — grading a tumor marker
or an HIV screen is the exact harm Tier C exists to prevent (#006). So we
account for **every** test, in one of three honest buckets, dropping nothing
and fabricating nothing:

1. **Assessed (Tier A):** full deterministic verdict (severity + urgency) and
   a grounded explanation. Only these feed the overall urgency roll-up.
2. **Acknowledged, not assessed (Tier B, Tier C, and any test we don't curate
   yet):** the value is READ and SHOWN — never dropped — but MediScan assigns
   NO severity/urgency and it does NOT affect the overall verdict. Two honesty
   levels:
   - *Numeric / unknown* (hs-CRP, PT/INR, a test we haven't curated): show the
     value and the report's own printed range, with — "MediScan doesn't
     clinically grade this one; here's what your report shows. Discuss it with
     your doctor."
   - *Sensitive* (tumor markers, serology, hormones): show only that the test
     is present, with — "This result needs a doctor's interpretation; MediScan
     doesn't assess it." **No** in/out-of-range verdict — even that can mislead.
3. **Unreadable lines:** already preserved (`unparsed_lines`); surfaced as
   "N lines couldn't be read," so nothing vanishes silently.

**The mechanism — a safety allowlist (key engine change).** After 6.5 a
`PSA 5.2 ng/mL < 4.0` line will *parse* (it has a one-sided range) — so without
a guard the severity engine would grade it. Therefore: **parse everything, but
only ASSESS tests on the curated allowlist** (a test with a Tier-A knowledge
entry we've vetted safe); every other parsed test is routed to "acknowledged,"
carrying a *sensitive* vs *numeric* label so the UI can word it correctly. A
test becomes assessable the moment we author + source its KB entry — a graceful
growth path.

**Where it lands:** the safety GATE + the assessed/acknowledged classification
are 6.5 engine work (task 6.5.6). Actually *displaying* the acknowledged bucket
is the final report/UI (Sprint 7–8), but the classification data is produced
now, so nothing is ever lost in between.

---

## What changes in CODE vs what's just DATA

**Code (the focused engineering — small):**
1. Parser learns one-sided ranges (`< 200`, `> 40`, `< 5.7 %`).
2. A tiny report-metadata extractor reads the patient's sex.
3. Reference-range resolution + severity banding become sex-aware and
   one-sided-aware.
4. A safety allowlist gates assessment; a coverage step buckets every test
   into assessed / acknowledged (numeric | sensitive) / unreadable.
5. Normalization gains the new test-name/unit synonyms (SGPT=ALT, etc.).

**Data (the bulk — authoring + sourcing):**
6. `knowledge_base/reference_ranges/*.json` — sourced ranges for all Tier-A
   panels, sex-aware where needed.
7. `knowledge_base/test_knowledge/*.json` — sourced explanation content for
   the same tests (so RAG can ground them). The RAG layer absorbs these with
   **zero code change** — that was the Sprint 6 payoff.

---

## Schema & module changes (small, additive)

- **`PatientContext`** (new, in its OWN module `schemas/patient.py`): `sex`
  (`MALE`/`FEMALE`/`UNKNOWN`) + optional `age`. Its own home because it WILL
  grow (pregnancy, fasting state, collection time, menstrual phase, sample
  type). `UNKNOWN` is first-class (never guessed).
- **`ReferenceRangeEntry`** (extend): allow a `null` bound (one-sided) and
  optional per-sex blocks (`male`/`female`) beside the shared range.
  Backward-compatible; CBC entries unchanged.
- **`CoverageResult`** (new schema): `assessed` / `acknowledged` / `unparsed`
  as one explicit object, not three loose lists — easier to evolve.
- **`AssessmentPolicy`** (new, MINIMAL for RC1 — DATA, not code): a table keyed
  by canonical name -> `{assessable, classification, tier}`, kept SEPARATE from
  the medical KB (KB = facts; policy = product behavior). The sensitivity
  classification lives HERE, not in the knowledge files. Full object model = RC2.
- No change to `ReferenceRange` (already one-sided-ready).

---

## Tasks

Same format as Sprint 6 (What -> Why -> Steps -> Safety/scale -> Done when).
**Order updated per review:** normalization now precedes resolution/severity,
since resolution, the allowlist, and KB lookup all key on canonical names.

### 6.5.1 - Scope lock + concept session - OWNER: pair (~1h) [DECIDED]

Tiers, union fallback, split-by-sensitivity, and the first-wave cut are locked
in "Decisions locked" below. Decision #029 drafted.

### 6.5.2 - Parser: one-sided ranges - OWNER: Rohit core + Claude tests (~2.5h)

Read `< X`, `> X`, `<= X`, `>= X` (and a trailing `%`) besides `LOW - HIGH`,
building a one-sided `ReferenceRange`. **Do this by extracting range
recognition into its own small, testable function** - the seed of the
composable-recognizer split that comes in Sprint 7 (we don't build that
framework now, we just stop the ONE regex from growing further). Keep the
tolerant "unknown line -> unparsed, never crash" contract. **Done when:**
`LDL 82 mg/dL < 100` parses one-sided; noise still unparsed.

### 6.5.3 - Patient metadata (own module) - OWNER: pair (~1.5h)

`schemas/patient.py::PatientContext` (`sex`, optional `age`) + an
`extraction/metadata.py` that reads sex from the report ("Sex: Male"),
returning `UNKNOWN` when absent. **Safety:** unknown is explicit (#011).
**Done when:** sex read from a header; UNKNOWN when silent.

### 6.5.4 - Normalization: new synonyms & units - OWNER: Rohit (~1.5h)

Grow the synonym/unit maps for all first-wave tests (SGPT<->ALT, SGOT<->AST,
name + unit variants). **Moved early** because resolution, the allowlist, and
KB lookup all key on canonical names. Data-only. **Done when:**
"SGPT"/"ALT"/"Alanine Aminotransferase" canonicalize to one name.

### 6.5.5 - Sex-aware + one-sided range resolution - OWNER: Rohit core + Claude tests (~2.5h)

Thread `PatientContext` into `resolve_reference_range`; extend
`ReferenceRangeEntry` (null bound + per-sex blocks); prefer the report's
printed range, else the sex-specific KB range, else (sex unknown) the UNION of
both sexes' ranges with reduced confidence. **Safety:** report-first unchanged
(#023). **Done when:** male vs female Creatinine with no printed range resolve
differently; UNKNOWN unions.

### 6.5.6 - Severity banding for one-sided ranges - OWNER: Rohit core + Claude tests (~2h)

Band only the bounded side(s); a `None` bound means that direction cannot be
abnormal - no invented direction, no invented CRITICAL (#006/#020). **Done
when:** `LDL 60` (`< 100`) is NORMAL; `LDL 190` is HIGH-side only.

### 6.5.7 - Assessment policy + coverage - OWNER: Rohit core + Claude tests (~2.5h)

Introduce a MINIMAL `AssessmentPolicy` (data, keyed by canonical name ->
`{assessable, classification, tier}`), SEPARATE from the medical KB, plus a
`CoverageResult { assessed, acknowledged, unparsed }` schema. Gate the engine:
assess only `assessable` tests; route the rest to `acknowledged` with their
`classification` (sensitive | numeric); acknowledged tests NEVER touch urgency.
This is the guard that stops a parsed `PSA < 4.0` line from ever getting a
severity. **Done when:** Hemoglobin (assessed) + PSA (acknowledged-sensitive) +
an unknown numeric (acknowledged-numeric) -> one graded finding, two
acknowledged, urgency from Hemoglobin only.

### 6.5.8 - Author the first-wave reference-range KB - OWNER: Rohit, content (~4h)

`reference_ranges/` for Lipids, Glucose/HbA1c, Thyroid, KFT - cited, sex-aware
where needed (Creatinine, Uric Acid), one-sided where needed. Every `source`
real (#019). **Done when:** files load + validate, no placeholders.

### 6.5.9 - Author the first-wave explanation KB - OWNER: Rohit, content (~4h)

`test_knowledge/` for the same first-wave tests (measures / low / high / diet /
specialist, each cited). Zero RAG code change (#028). **Done when:** the index
builds and a lipid/thyroid query retrieves the right sourced snippet.

### 6.5.10 - KB integrity checks - OWNER: pair (~2h)  [NEW, from review]

Extend load-time validation beyond per-entry schema: duplicate canonical names
across panels, unit consistency between a test's range + knowledge entries,
impossible critical thresholds (critical inside the normal range / low >= high),
and orphans (a policy-assessable test missing a range or knowledge entry, or a
KB entry with no policy row). Run as a test (and later in CI). **Done when:** a
deliberately-broken KB entry fails the check with a clear message.

### 6.5.11 - Fixtures + end-to-end integration - OWNER: pair (~2h)

Synthetic full-wave report (male + female, including an out-of-scope test to
prove acknowledgment) -> correct grounded verdict end to end. **Done when:** the
pipeline flags the right tests with the right severities; out-of-scope
acknowledged not graded.

### 6.5.12 - Tests throughout - OWNER: split (~3h)

Happy (Rohit): parser one-sided, sex extraction, normalization, sex-aware
resolution, banding, allowlist. Adversarial (Claude): no invented direction;
UNKNOWN-sex union; Tier-C acknowledged never graded / never in urgency; KB
integrity catches breakage; #006 boundary holds. **Done when:** fast suite
green + offline.

### 6.5.13 - Sprint close - OWNER: Rohit (~1h)

Log #029 (scope tiers + acknowledge) and #030 (review refinements); update
roadmap (6.5 done), architecture, reflections, README, project-status; CI green.

---

## Cross-cutting: security, scalability, production-readiness

**Security / privacy** — unchanged: everything local; the report's sex/age are
PHI, so they live only in-process and never in logs or the repo (synthetic
fixtures only, #010).

**Scalability** — new panels are mostly new JSON (ranges + knowledge), not new
code. The engine upgrades (one-sided parse, sex-awareness, one-sided banding,
the allowlist gate) are one-time; after that every future test that fits Tier A
is data-only, and the allowlist grows as its KB entry is authored.

**Production-readiness** — the safety envelope is preserved and extended:
deterministic-only deciding (#006), report-first ranges (#023), no invented
CRITICAL (#020), conservative urgency roll-up (#022), unknown-never-fine (#011),
and now *nothing silently skipped* — every test is assessed, acknowledged, or
flagged unreadable.

---

## Decisions locked (6.5.1) — to be logged with #029

1. **Sex-unknown fallback = UNION of both sexes' ranges.** When a sex-dependent
   test has no printed range and the patient's sex is unknown, use the widest
   normal band (both sexes combined) and flag reduced confidence — we don't
   raise a false alarm, and we still give the user an answer. (Rare in practice:
   most reports print their own range, which is trusted first.)
2. **Unassessed tests = SPLIT by sensitivity.** *Sensitive* (tumor / serology /
   hormone) is shown as "present — needs a doctor's interpretation, not
   assessed," with NO in/out-of-range verdict. *Numeric / unknown* shows the
   report's own printed range neutrally, "not clinically graded by MediScan."
3. **RC1 ships a FIRST WAVE, then expands.** First wave = **Lipids +
   Glucose/HbA1c + Thyroid + KFT**. The remaining Tier-A panels (LFT,
   electrolytes/minerals, iron studies, vitamins, CBC-extend, urine ACR) follow
   immediately after — same machinery, data-only. This validates the
   sex-aware/one-sided engine on a smaller sourced set first.

---

## Refinements adopted from Rohit's review (to log as #030)

Rohit's architecture review of this plan. Adopted into the tasks above:
1. **Policy != knowledge.** A minimal `AssessmentPolicy` (assessable /
   classification / tier), separate from the KB, lands in RC1 - because the
   "split by sensitivity" behavior needs a home that ISN'T the medical facts.
   Full policy object = RC2.
2. **`PatientContext` gets its own module** - it will grow.
3. **Parser:** extract range-parsing into its own testable function now; the
   full composable-recognizer refactor is **Sprint 7**, not now.
4. **`CoverageResult`** becomes an explicit schema, not three loose lists.
5. **KB integrity checks** (new task 6.5.10): duplicate canonical names, unit
   consistency, impossible criticals, orphan entries.
6. **Order:** normalization moves BEFORE resolution/severity.

Deferred (revisit triggers, not built now):
- Panel-first KB folder layout (`knowledge_base/lipid/...`) once the KB reaches
  hundreds of entries - **[OPEN: Rohit to decide reorg-now vs later]**.
- Full `AssessmentPolicy` object model - RC2.
- Composable parser recognizers - Sprint 7.

Foundations Rohit flagged as solid and we will NOT touch: report-first ranges,
deterministic engine, RAG architecture, severity/urgency algorithms, provider &
PromptTemplate abstractions.

---

## Definition of done

- [ ] Parser reads one-sided ranges; noise still unparsed.
- [ ] Patient sex read from the report; UNKNOWN handled explicitly.
- [ ] Reference-range resolution + severity banding are sex-aware and
      one-sided-aware; no invented direction or CRITICAL.
- [ ] Every test is accounted for: assessed (Tier A), acknowledged
      (numeric | sensitive), or flagged unreadable — nothing silently skipped.
- [ ] Assessment is gated on the curated allowlist; a parsed Tier-C test is
      never graded and never touches urgency.
- [ ] Normalization covers all Tier-A test names/units.
- [ ] Sourced reference-range KB + explanation KB authored for Tier-A (no
      placeholder sources); loads and validates.
- [ ] RAG grounds the new tests with NO rag/ code change.
- [ ] Full-panel synthetic fixtures (both sexes) pass end to end.
- [ ] Fast suite green + offline; #006 boundary test holds.
- [ ] Decisions (#029 + sex/one-sided/acknowledge) logged; docs/README/status
      updated; CI green.
