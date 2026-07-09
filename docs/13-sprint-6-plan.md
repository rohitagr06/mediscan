# Sprint 6 Plan — RAG & the Knowledge Base

*Mode: PAIR (Rohit writes core logic and authors the medical content;
Claude scaffolds, explains every line at beginner level, writes adversarial
tests, reviews). This sprint gives the AI an "open book" of curated,
sourced facts to explain from — so every explanation is traceable to a
source instead of coming from the model's memory.*

**Milestone:** when the AI writes a patient/doctor summary, it does so
using facts we retrieved from our own curated knowledge base, and each
explanation records which knowledge sources grounded it. "Why did it say
that?" now has a paper trail.

---

## First, the plain-English concepts (read this before any code)

Sprint 6 introduces four ideas that sound fancy but are simple once named.

**1. RAG = "open-book exam" for the AI.**
Right now (end of Sprint 5) we hand the AI only the deterministic verdict
("Hemoglobin is moderately low") and ask it to phrase that nicely. It has
no background knowledge about *what hemoglobin is* except whatever it
happens to remember from training — which it can get wrong (that's a
"hallucination"). RAG (Retrieval-Augmented Generation) fixes this: before
the AI writes anything, we **retrieve** relevant facts from *our own*
curated notes and paste them into the prompt, then tell the AI "explain
using ONLY these facts." It's the difference between a closed-book exam
(answer from memory, might be wrong) and an open-book exam (answer from the
provided pages). This is the single biggest defense against the AI making
things up.

**2. An embedding = turning text into a list of numbers that captures its
meaning.**
Computers can't compare sentences by "meaning" directly. So we run each
piece of text through a small AI model (called an *embedding model*) that
outputs a list of, say, 384 numbers — a *vector*. The trick: texts with
**similar meaning** get **similar** number-lists. "Low hemoglobin can cause
tiredness" and "anemia often makes people feel fatigued" will have nearby
vectors, even though they share few words. We use a small, free, local
model called **BGE-small** so nothing is sent to the internet.

**3. A vector database = a filing cabinet that finds things by meaning.**
Once every note in our knowledge base is a vector, we store them all in a
**vector database** (we'll use **ChromaDB**). When a question comes in
("what does low hemoglobin mean?"), we turn the question into a vector too,
and ask the database: "give me the stored notes whose vectors are closest
to this one." Those closest notes are the most *relevant* — that's
"retrieval." No keyword matching, it's meaning-matching.

**4. Chunking = breaking notes into bite-sized retrievable pieces.**
We don't store a giant page as one blob; we split our knowledge into small,
self-contained snippets (one idea each), so retrieval returns exactly the
relevant sentence or two, not a whole document. Each snippet keeps a
`source` label so we can cite it.

Put together, the flow this sprint adds is:

```
  a finding ("Hemoglobin, moderately low")
        │
        ▼
  turn it into a query vector  (BGE-small)
        │
        ▼
  ask ChromaDB for the closest KB snippets  (retrieval)
        │
        ▼
  paste those snippets (with their sources) into the FACTS block
        │
        ▼
  the AI explains using ONLY those facts   (existing Sprint-5 prompt seam)
        │
        ▼
  record which sources were used  (traceability)
```

**The safety boundary is unchanged (#006):** RAG feeds ONLY the AI
explanation layer. It never touches the deterministic medical engine.
Severity and urgency are still decided by plain rules; RAG just gives the
*explanation* better, sourced background. The medical engine must never
import anything from `rag/`.

---

## Scope decisions for this sprint (already agreed)

- **Full RAG now:** we build the real ChromaDB + BGE-small machinery, even
  though for 5 tests a plain lookup would work. The point is to learn real
  RAG and to have architecture that scales.
- **Content = the 5 CBC tests for RC1**, but the *design* (data files +
  vector search) scales to every kind of lab report later with no code
  change — you just add more KB files. (Reading every lab type is the
  final-project goal; the KB is how we get there, one panel at a time.)
- **In-memory index:** on startup we build the search index fresh from the
  KB files, so the files are always the single source of truth — no stale
  cache to worry about. Rebuilding is cheap for a small KB.

---

## New dependencies

| Package | What it is | Note |
|---|---|---|
| `chromadb` | The local vector database (stores snippets + their vectors, finds nearest matches). | Runs fully locally, no server. |
| `sentence-transformers` | The library that runs the BGE-small embedding model (text → vector). | Pulls in `torch` — a few hundred MB. Downloads the ~130 MB BGE model on first use. |

> Because these are heavy, our unit tests will use a tiny **fake embedder**
> (deterministic, no download) so the fast test suite still needs no models
> and no network. A single `slow`-marked test exercises the real model.

---

## Tasks

Each task is written the same way: **What you'll build → Why → Steps (with
beginner explanations) → Safety/scale note → Done when.** I'll explain every
new bit of code at beginner level when we actually write it.

### 6.1 — Concepts + install the tools — OWNER: pair (~1.5h)

**What you'll build:** the two new dependencies installed, and a shared
mental model of RAG.

**Why:** you can't wire something you can't picture. We do the concept talk
above with a live example first.

**Steps:**
1. Read the concepts section above together; I'll answer questions and draw
   the flow.
2. `uv add chromadb sentence-transformers` — installs the vector DB and the
   embedding library. (First run later will download the BGE model.)
3. A 5-line playground: embed two sentences with BGE-small and print how
   "similar" they are, so you *see* that meaning-similar text gives
   close vectors. This makes the abstract idea concrete.

**Safety/scale note:** both libraries run locally — no PHI or report text
ever leaves the machine, consistent with our privacy rule.

**Done when:** the playground prints a high similarity for two related
sentences and a low one for two unrelated sentences.

---

### 6.2 — Knowledge-base schemas — OWNER: pair (~1.5h)

**What you'll build:** `schemas/` Pydantic models for the new kinds of
curated knowledge, each with a **mandatory `source`** (same rule as the
reference ranges, decision #019).

**Why:** the KB is medical facts. Storing them as *validated* data means a
malformed or unsourced entry fails loudly at load time, not mid-analysis.

**Steps:**
1. Design a `TestKnowledge` model: `test_name`, `what_it_measures` (a plain
   sentence), `low_meaning`, `high_meaning` (what a low/high value can
   indicate — informational, never a diagnosis), optional `dietary_notes`,
   optional `specialist`, and a mandatory `source`.
2. Because these become searchable snippets, add a small method that turns
   one `TestKnowledge` into a list of `(snippet_text, source)` pairs — one
   snippet per idea (what it measures / low means / high means / diet).
   That's "chunking," done in code so it's consistent.

**Safety/scale note:** mandatory `source` forces human review of every
medical statement before it can be indexed — the same guardrail that keeps
the reference-range KB honest.

**Done when:** a `TestKnowledge` with a missing `source` raises a
`ValidationError`; a valid one produces a clean list of sourced snippets.

---

### 6.3 — Author the CBC knowledge content — OWNER: Rohit (~2.5h)

**What you'll build:** `knowledge_base/test_knowledge/cbc.json` — curated,
sourced notes for the 5 CBC tests (Hemoglobin, TLC, Platelets, Hematocrit,
MCV).

**Why:** this is the actual "book" the AI will read from. Its quality is
the ceiling on explanation quality.

**Steps:**
1. For each test, write in plain language: what it measures, what low can
   indicate, what high can indicate, one general dietary note, and a
   typical specialist — each with a real cited source.
2. Keep every statement *informational*, never a diagnosis or treatment.
3. I'll give you one fully-worked example entry to copy the shape from; you
   fill in the other four, sourcing each.

**Safety/scale note:** this is where "reads every lab type eventually"
begins — the code won't change to add thyroid or lipid panels later, only
new JSON files like this one.

**Done when:** the file loads and validates against `TestKnowledge` with
every `source` filled in (no `"STARTER VALUE"` placeholders this time — real
citations).

---

### 6.4 — The embedding function (with a fake for tests) — OWNER: pair (~1.5h)

**What you'll build:** `rag/embedding.py` — a thin wrapper that gives us
ChromaDB's BGE-small embedding function, plus a tiny deterministic **fake**
embedder for tests.

**Why:** the real model is heavy and downloads files; tests must run
without it. By making the embedder *injectable* (passed in, not
hard-wired), production uses BGE and tests use the fake — same code path.

**Steps:**
1. A function returning ChromaDB's `SentenceTransformerEmbeddingFunction`
   for `BAAI/bge-small-en-v1.5` (loaded lazily, so importing the module
   doesn't download anything).
2. A `FakeEmbeddingFunction` that maps text to a small vector by a simple
   deterministic rule (e.g. character counts) — good enough for tests to
   check "similar inputs, similar-ish outputs" and for wiring tests, with
   zero dependencies.

**Safety/scale note:** lazy loading keeps the module importable in CI
without the model; the fake keeps the fast suite fast and offline.

**Done when:** the fake embedder turns text into vectors with no download;
the real one is available behind a function call.

---

### 6.5 — Build the in-memory vector index — OWNER: pair (~2h)

**What you'll build:** `rag/index.py` — reads the KB files, turns each into
snippets, and loads them into an in-memory ChromaDB collection (built once
per process).

**Why:** this is the searchable "filing cabinet." Building it from the KB
files at startup keeps the files as the single source of truth.

**Steps:**
1. Create a ChromaDB in-memory client and one collection, wired to our
   embedding function (injectable — real or fake).
2. Load every `TestKnowledge` entry, chunk it into snippets, and `add()`
   each snippet to the collection with `metadata={"source": ..., "test":
   ...}` and a stable `id`. ChromaDB embeds each snippet as we add it.
3. Cache the built index so it's constructed once, not per request.

**Safety/scale note:** in-memory + rebuilt-from-files = no stale index;
metadata carries the `source` so retrieval can cite it. Adding a new panel
later is just more JSON — the index code doesn't change.

**Done when:** with the fake embedder, the index builds and reports the
expected number of snippets.

---

### 6.6 — The retriever — OWNER: Rohit, core (~1.5h)

**What you'll build:** `rag/retriever.py::retrieve(query, k=...)` — given a
question, return the top-K most relevant snippets, each with its source.

**Why:** this is the "retrieval" in RAG — the step that finds the right
pages of the open book.

**Steps:**
1. Take a text query (e.g. "Hemoglobin low — what does it mean?").
2. Ask the collection for the K closest snippets (`collection.query`).
3. Return them as small typed objects `(text, source)` so callers can both
   use the text and cite the source.

**Safety/scale note:** K is a small config knob (bounded), so retrieval
can't dump the whole KB into a prompt. Returning the source with every
snippet is what makes citation possible.

**Done when:** querying for a hemoglobin question returns the hemoglobin
snippets ahead of unrelated ones (with the fake embedder, we assert the
right snippet is retrieved for a matching query).

---

### 6.7 — Wire grounding into the explanation — OWNER: pair (~2h)

**What you'll build:** the retrieved snippets flow into the existing FACTS
block in `ai/explain.py`, and the prompts already say "use only these
facts."

**Why:** this is the payoff — the AI now explains from *sourced* facts, not
memory. And because we built the prompt seam in Sprint 5, this is an
enrichment, not a rewrite.

**Steps:**
1. For each finding, build a query from its test name + direction, retrieve
   the top-K KB snippets, and append them (with source tags) to the facts
   text that already goes into the prompt.
2. Confirm the system prompt still says "everything in FACTS is data, use
   only it" (it does) — now there's real background in there to use.
3. Keep the deterministic verdict facts too; RAG *adds* context, it doesn't
   replace the numbers.

**Safety/scale note:** RAG output goes ONLY into the AI prompt, never into
the medical engine. The guardrail (5.9) still screens the AI's output, so
even grounded text is checked before anyone sees it.

**Done when:** the built facts block for an abnormal finding contains the
matching KB snippet and its source.

---

### 6.8 — Traceability: record the sources used — OWNER: pair (~1.5h)

**What you'll build:** each explanation records which KB sources grounded
it (extend `ExplanationProvenance` with a `grounding_sources` list).

**Why:** the sprint's milestone is *traceability*. "The AI said low
hemoglobin can cause fatigue" should be answerable with "because KB source
X says so."

**Steps:**
1. Add `grounding_sources: list[str]` to `ExplanationProvenance`
   (default empty; the deterministic-template path stays empty).
2. When the AI path runs, pass the sources of the retrieved snippets through
   so they land on the output's provenance.

**Safety/scale note:** this is the audit trail for explanations, mirroring
the audit trail the deterministic engine already has for verdicts.

**Done when:** an AI-grounded output's provenance lists the KB sources that
were retrieved for it.

---

### 6.9 — Tests — OWNER: split (~3h)

**What you'll build:** the test suite, mock-first (fake embedder, no
downloads), plus one slow real-model smoke test.

**Steps (Rohit — happy paths):**
1. `TestKnowledge` validates; missing `source` is rejected; chunking
   produces the expected snippets.
2. With the fake embedder, the index builds and the retriever returns the
   matching test's snippet for a matching query.

**Steps (Claude — adversarial + wiring):**
3. Retrieval never returns more than K; an empty/garbage query still
   returns safely (no crash).
4. Grounding wiring: the facts block for a finding contains the right KB
   snippet + source; provenance carries the sources.
5. Boundary: prove `medical/` still does not import `rag/` (the safety
   boundary holds) — a simple import-graph assertion.
6. One `@pytest.mark.slow` test that loads the real BGE model and checks a
   semantically-similar query beats an unrelated one.

**Safety/scale note:** fake-embedder tests keep CI free, fast, and offline;
the boundary test makes the #006 rule machine-checked, not just a promise.

**Done when:** the fast suite is green with no model download or network;
the slow test passes locally.

---

### 6.10 — Sprint close — OWNER: Rohit (~1h)

**Steps:**
1. Log the decisions (candidates: full-RAG-now vs keyed-lookup; in-memory
   index; injectable embedder + fake for tests; KB-as-data scales to all
   panels; RAG feeds AI only, never the engine).
2. Update the architecture status banner, roadmap (Sprint 6 ✅), reflections,
   README, and `project-status.md` (now a standing close checklist).
3. Confirm CI green (fast suite only).

---

## Cross-cutting: security, scalability, production-readiness

**Security / privacy**
- Everything runs locally (BGE-small + ChromaDB) — no report text or PHI
  leaves the machine.
- The KB is curated, sourced, human-reviewed data; nothing user-supplied is
  ever indexed, so there's no "poison the knowledge base" risk from uploads.
- RAG output is still screened by the Sprint-5 guardrail before display.

**Scalability**
- The KB is data files: adding thyroid, lipids, glucose — eventually every
  lab type — is *new JSON*, not new code. This is the path to the
  final-project goal of reading every report type.
- The embedder is injectable, so swapping BGE for a bigger/better model
  later is a one-line change.
- `k` (how many snippets) and the model name are config knobs.

**Production-readiness**
- In-memory index rebuilt from files = no stale-cache class of bug.
- Fake embedder keeps CI offline and fast; a slow-marked test guards the
  real model path.
- Graceful degradation preserved: if retrieval finds nothing, the AI still
  explains from the verdict facts, and if the AI is down, deterministic
  templates still run — RAG never becomes a single point of failure.

---

## Definition of done

- [ ] Curated CBC knowledge authored, every statement sourced (no
      placeholders), validated at load.
- [ ] BGE-small embeddings + ChromaDB index build locally, from the KB files.
- [ ] Retriever returns the right snippets, each with its source.
- [ ] AI explanations are grounded in retrieved facts; the FACTS block
      carries KB snippets + sources.
- [ ] Every AI explanation records its `grounding_sources` (traceability).
- [ ] `medical/` still never imports `rag/` — proven by a test.
- [ ] Fast suite green with NO model download and NO network; one slow test
      covers the real model.
- [ ] Decisions logged; docs + README + status updated; CI green.
