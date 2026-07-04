# Sprint 3 Plan — OCR for Scans & Photos

*Mode: PAIR, same split as Sprint 2 — Rohit writes the core concepts
(the engine contract, preprocessing, the factory), Claude writes heavy
scaffolding, OCR-able fixtures, and adversarial tests. Every task below
says who owns it and what concept it teaches.*

**Milestone:** a photo (or scanned PDF) of a lab report goes in → real
extracted text with an HONEST confidence score comes out — through the
same validate → store → route flow as Sprint 2, with the router's
PDF_SCANNED branch finally connected to something.

**The gating experiment:** task 3.1 attempts PaddleOCR installation on
Apple Silicon. Its outcome resolves decision #008 and selects the
primary engine for RC1 development. The plan works either way — that is
what the OcrEngine contract is FOR.

---

## Concepts this sprint teaches (in order of appearance)

1. **OCR itself** — recognizing characters in pixels; why output is
   probabilistic (per-word confidence) and input quality dominates.
2. **Abstract base classes (ABCs)** — a contract with no implementation;
   `@abstractmethod`; why callers depend on contracts, not engines.
3. **Image preprocessing** — grayscale, contrast, scaling with Pillow;
   measuring (not assuming) that cleanup improves OCR accuracy.
4. **Rendering PDFs to images** — pymupdf's `get_pixmap()`: a scanned
   PDF is OCR'd by first turning each page back into a picture.
5. **Confidence aggregation** — per-word scores → page score → document
   score; why we take the MEAN but also keep the MINIMUM in mind
   (one unreadable critical value matters more than a good average —
   this tension feeds Sprint 7's scoring design).
6. **Conditional testing** — tests that skip when an engine is absent
   (importorskip), and `@pytest.mark.slow` for heavyweight OCR tests so
   the fast suite stays fast.

## New dependencies

| Package | Type | Why |
|---|---|---|
| paddleocr + paddlepaddle | runtime (attempt) | primary OCR engine (decision #008) |
| pytesseract | runtime (fallback) | Tesseract Python wrapper — escape hatch |
| Tesseract binary | system (brew) | the actual fallback engine |
| pillow | runtime (promote from dev) | preprocessing needs it at runtime now |

## Tasks

### 3.1 — The experiment: install PaddleOCR — OWNER: Rohit (~1-2h, timeboxed!)
`uv add paddleocr paddlepaddle`, then a 5-line playground script OCRs
tests/fixtures/files/sample.png. STRICT TIMEBOX: if installation or
first run fights for more than ~90 minutes total, STOP — that is not
failure, that is the experiment returning its answer. Either outcome
gets a decision-log row resolving #008 (engine chosen + evidence).
Fallback path: `brew install tesseract` + `uv add pytesseract` (usually
< 10 minutes).

### 3.2 — `ocr/base.py`: the OcrEngine contract — OWNER: Rohit (~1.5h)
The sprint's concept centerpiece. An ABC with one abstractmethod
`extract(path: Path) -> ExtractedDocument` and a `method_name: str`
attribute; docstrings state the contract's promises (blank pages
represented, ocr_confidence required for OCR engines, CorruptDocument
handling). Then make PyMuPdfEngine formally inherit it — proof that a
contract can be retrofitted onto code that already honored it.

### 3.3 — OCR-able fixtures — OWNER: Claude (~1.5h)
generate.py grows: `report_photo.png` (a PIL-drawn IMAGE of CBC text —
pixels, not characters, so OCR has something real to read) and
`scanned_cbc.pdf` (that image embedded in a PDF page — a true synthetic
scan). Current scanned_report.pdf stays: it tests "no text at all";
the new ones test "text as pixels".

### 3.4 — The OCR engine — OWNER: pair (~2.5h)
Claude scaffolds (engine init, corrupt-image handling, the confidence
plumbing); Rohit implements the recognition loop: run engine on image,
collect (text, confidence) per word/line, build PageText + aggregate
document confidence. Whichever engine won 3.1; the loser's file can be
added later behind the same contract without touching callers.

### 3.5 — Preprocessing — OWNER: Rohit (~2h)
`ocr/preprocessing.py`: `prepare_image(path) -> Path` using Pillow —
grayscale → autocontrast → upscale-if-small. Then the science part:
a playground comparison of OCR confidence WITH vs WITHOUT preprocessing
on the same fixture — we keep preprocessing only if the numbers say it
earns its place (measure, don't assume).

### 3.6 — Scanned-PDF path — OWNER: pair (~2h)
pymupdf `get_pixmap()` renders each PDF page to an image → preprocess →
OCR each → assemble multi-page ExtractedDocument (doc_type=PDF_SCANNED,
real ocr_confidence). This finally makes the router's PDF_SCANNED branch
lead somewhere.

### 3.7 — Engine factory + config — OWNER: Rohit (~1h)
`settings.ocr_engine: str = "auto"` and a factory function that returns
the configured engine (auto = whichever is importable, preferring the
3.1 winner). Callers ask the factory, never import engines directly —
the contract pattern completed.

### 3.8 — Tests — OWNER: split (~2.5h)
Rohit: contract tests (every engine returns valid ExtractedDocument
with confidence present; blank-image behavior) + preprocessing tests.
Claude: adversarial (corrupt image bytes, huge image, zero-size render)
+ the slow-marked end-to-end: photo fixture → validate → store → route →
OCR → assert "Hemoglobin" and "9.8" appear (OCR text may be imperfect —
the test asserts KEY tokens, teaching tolerance-aware assertions).

### 3.9 — Sprint close — OWNER: Rohit (~1h)
Decision-log row resolving #008 with evidence; README + roadmap +
reflections updates; CI consideration: slow marker excluded from the
default run, full suite weekly or on demand.

## Exercises

- **Try Yourself:** photograph a HANDWRITTEN fake lab value with your
  phone, run it through the pipeline, and study what OCR does to it.
- **Debugging Exercise:** Claude hands you an image that OCRs to garbage;
  diagnose why (resolution? contrast? rotation?) using preprocessing
  experiments rather than reading the answer.
- **Optimization Challenge:** the scanned-PDF path renders pages at a
  DPI you choose. Find the lowest DPI where confidence stays high —
  rendering cost vs accuracy, measured.
- **Architecture Reflection:** the OcrEngine ABC could have been a
  Protocol (structural typing) instead. After using the ABC, read about
  Protocols and write 5 sentences on when you'd choose each.

## Definition of done

- [ ] Decision #008 resolved with a logged outcome and evidence
- [ ] OcrEngine contract exists; BOTH PyMuPdfEngine and the OCR engine honor it
- [ ] Photo fixture → text with real confidence, end to end, test-proven
- [ ] Scanned-PDF branch of the router leads to working OCR
- [ ] Preprocessing kept or cut based on MEASURED confidence delta
- [ ] Fast suite stays fast (slow tests marked); CI green
