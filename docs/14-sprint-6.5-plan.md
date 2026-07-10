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

## Schema changes (small, additive)

- **`PatientContext`** (new): a tiny model holding `sex: Sex` (an enum
  `MALE` / `FEMALE` / `UNKNOWN`) and optionally `age`. Read from the report;
  `UNKNOWN` is a first-class value (never guessed).
- **`ReferenceRangeEntry`** (extend): allow optional per-sex variants
  alongside the existing shared range. Backward-compatible — CBC's current
  entries keep working unchanged.
- **A coverage/result structure** that carries the two buckets (assessed vs
  acknowledged) plus the acknowledged label (`numeric` | `sensitive`), so
  nothing read from the report is ever lost between engine and report.
- No change needed to `ReferenceRange` (already supports one-sided).

---

## Tasks

Same format as Sprint 6: **What → Why → Steps (beginner explanations) →
Safety/scale note → Done when.** Every new line of code gets a beginner
walkthrough when we write it.

### 6.5.1 — Scope lock + concept session — OWNER: pair (~1h)

**What:** agree the Tier A/B/C list and the "acknowledge, don't skip" behavior
before touching code. **Why:** scope is a safety decision; we lock it, then
build. **Steps:** walk the tiers together; Rohit confirms the Tier-A cut, the
sex-unknown fallback (6.5.4), and the sensitive-vs-numeric acknowledged wording
(6.5.6). **Done when:** the tier list + acknowledge behavior are confirmed and
decision #029 is drafted.

### 6.5.2 — Parser: one-sided ranges — OWNER: Rohit core + Claude tests (~2.5h)

**What:** extend `parser.py` to recognize `< X`, `> X`, `<= X`, `>= X` (and a
trailing `%` unit) in addition to `LOW - HIGH`. **Why:** the parser is the
gate — it can't read a lipid/HbA1c line today. **Steps:** add pattern(s) for
one-sided ranges that build a `ReferenceRange(low=None, high=X)` or
`(low=X, high=None)`; keep the tolerant "unrecognized line becomes unparsed,
never a crash" contract; update decision #018's note. **Safety/scale note:**
still anchored on a printed range shape, so headers/noise stay unparsed.
**Done when:** an `LDL 82 mg/dL < 100` style line parses into a one-sided
`ReferenceRange`; garbage lines still land in `unparsed_lines`.

### 6.5.3 — Read patient sex from the report — OWNER: pair (~1.5h)

**What:** `extraction/metadata.py` → a function that scans report text for a
sex/gender line and returns a `PatientContext`. **Why:** sex-aware ranges need
the patient's sex, and the report is the honest source. **Steps:** a small,
tolerant regex for "Sex: Male", "Gender: F", etc.; return `Sex.UNKNOWN` when
absent (never guess). **Safety/scale note:** unknown is explicit (#011).
**Done when:** the extractor reads M/F from a header and returns UNKNOWN when
the report is silent.

### 6.5.4 — Sex-aware + one-sided range resolution — OWNER: Rohit core + Claude tests (~2.5h)

**What:** thread `PatientContext` into `resolve_reference_range`, and pick the
sex-specific KB range when the report doesn't print its own. **Why:** correct
banding for Hemoglobin/Creatinine/Ferritin depends on sex. **Steps:** extend
`ReferenceRangeEntry` with optional per-sex ranges; prefer the report's printed
range (already sex-correct), else pick the KB range for the patient's sex; when
sex is UNKNOWN apply the agreed fallback (recommended default: **union** of both
sexes' ranges for the normal band so we don't false-flag, noting reduced
confidence — confirm in 6.5.1). **Safety/scale note:** report-first is
unchanged (#023); sex only affects the KB fallback. **Done when:** a female vs
male Hemoglobin with no printed range resolves to different KB ranges; UNKNOWN
uses the fallback.

### 6.5.5 — Severity banding for one-sided ranges — OWNER: Rohit core + Claude tests (~2h)

**What:** teach `severity.py` to band only the bounded side(s). **Why:** a
value below an "upper-limit-only" range is NORMAL, not low — banding the
missing side would invent medicine. **Steps:** where a bound is `None`, that
direction cannot be abnormal; grade only the side with a bound
(percentage/Option-A, or Option-B fraction if a sourced critical exists on that
side, capped at HIGH per #020). **Safety/scale note:** upholds #006 — no
invented CRITICAL, no invented direction. **Done when:** `LDL 60` (range
`< 100`) is NORMAL; `LDL 190` is graded HIGH-side only; truth-table tests cover
both one-sided directions.

### 6.5.6 — Coverage classification + assessment allowlist — OWNER: Rohit core + Claude tests (~2h)

**What:** gate the engine so it ASSESSES only tests on the curated Tier-A
allowlist, and route every other parsed test into an "acknowledged, not
assessed" list carrying a `numeric` vs `sensitive` label. **Why:** a public
tool meets reports full of out-of-scope tests; skipping them is unsafe (#011),
grading them is unsafe (#006) — acknowledge instead. This is the guard that
stops a parsed `PSA` line from ever getting a severity. **Steps:** add an
"assessable" check keyed on curated KB membership; produce two buckets
(assessed / acknowledged) + the acknowledged label; ensure acknowledged tests
NEVER touch the urgency roll-up; unreadable lines stay surfaced separately.
**Safety/scale note:** the allowlist is DATA — a test becomes assessable when
its KB entry is authored, so growth is graceful and honest. **Done when:** a
report mixing Hemoglobin (assessed), PSA (acknowledged-sensitive), and an
unknown numeric test (acknowledged-numeric) yields one graded finding + two
acknowledged entries, and urgency reflects only the Hemoglobin.

### 6.5.7 — Normalization: new synonyms & units — OWNER: Rohit (~1.5h)

**What:** grow the normalization maps for all Tier-A tests (SGPT↔ALT,
SGOT↔AST, name variants, unit spellings). **Why:** reports name the same test
many ways; the engine must canonicalize before lookup. **Steps:** add entries
to the synonym/unit data; keep it data-driven (no logic change). **Done when:**
"SGPT", "ALT", "Alanine Aminotransferase" all normalize to one canonical name
matching the KB key.

### 6.5.8 — Author the sourced reference-range KB — OWNER: Rohit, content (~4h+)

**What:** `reference_ranges/*.json` for every Tier-A panel — real, cited
ranges and (where relevant) critical thresholds, sex-aware where needed.
**Why:** this is the medical backbone; the engine is only as correct as these
numbers. **Steps:** one JSON file per panel; every entry carries a mandatory
`source` (#019) — no "STARTER VALUE" this time; sex variants for
Hemoglobin/Creatinine/Ferritin/etc. **Safety/scale note:** validated at load.
**Done when:** all files load and validate; no placeholder sources.

### 6.5.9 — Author the sourced explanation KB (for RAG) — OWNER: Rohit, content (~4h+)

**What:** `test_knowledge/*.json` (the RAG "book") for the Tier-A tests — what
each measures, what low/high can indicate, a dietary note, a specialist, each
cited. **Why:** so the AI can *ground* explanations for the new tests.
**Safety/scale note:** **zero RAG code changes** — the "KB-as-data scales"
promise from Sprint 6 (#028) being cashed in. **Done when:** the index builds
over the enlarged KB and a lipid/thyroid query retrieves the right sourced
snippet.

### 6.5.10 — Fixtures + end-to-end integration test — OWNER: pair (~2h)

**What:** a synthetic full-body checkup fixture (a male and a female variant,
including an out-of-scope test to prove acknowledgment), driven end to end.
**Why:** proves the whole pipeline on a realistic multi-panel report. **Done
when:** a synthetic full-panel report → a correct, grounded verdict, both
sexes, with out-of-scope tests acknowledged not graded.

### 6.5.11 — Tests throughout — OWNER: split (~3h)

Happy paths (Rohit): parser one-sided cases, sex extraction, sex-aware
resolution, new-panel banding, allowlist assessment. Adversarial (Claude):
one-sided banding never invents a direction; UNKNOWN-sex fallback; a Tier-C
test in a report is acknowledged, NEVER graded, and never touches urgency;
parser still rejects noise; #006 boundary test still holds. **Done when:** fast
suite green, offline.

### 6.5.12 — Sprint close — OWNER: Rohit (~1h)

Log decisions (#029 scope tiers + acknowledge-don't-skip; sex-aware resolution;
one-sided banding rule); update roadmap (Sprint 6.5 ✅), architecture banner,
reflections, README, `project-status.md`; confirm CI green.

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

## Open questions to confirm before coding (6.5.1)

1. **Sex-unknown fallback:** union-of-both-ranges (fewer false alarms, my
   recommended default) vs narrower-intersection (flags more, "over-warn is
   safe")? We pick one and log it.
2. **Sensitive-test wording (mostly decided):** Rohit's requirement settles
   "don't skip" — confirm the *sensitive* category is shown as "present — needs
   a doctor's interpretation, not assessed" WITHOUT any in/out-of-range verdict
   (my recommendation), while *numeric/unknown* tests may show the report's own
   range neutrally.
3. **RC1 panel cut:** ship ALL Tier-A panels at once, or a first wave
   (lipids + glucose/HbA1c + thyroid + KFT) with the rest a fast follow?

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
