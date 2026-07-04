# Sprint 2 Plan — Secure Ingestion & Text-PDF Extraction

*Mode: PAIR — Rohit writes the core logic (validators, storage, router),
Claude writes the supporting machinery (fixture generators, edge-case tests)
and reviews everything. Each task states its owner.*

**Milestone:** a synthetic lab-report PDF goes in → is validated as safe →
routed as "text PDF" → comes out as clean, structured extracted text.
All security cases tested. Zero real medical documents anywhere (#010).

---

## Learning goals (Rohit)

1. **Bytes vs strings** — files are bytes; text is an interpretation of bytes.
2. **Magic bytes** — real file types live in the first few bytes, not the
   filename. `report.pdf` renamed from `evil.exe` still starts with `MZ`.
3. **Custom exceptions** — designing an error hierarchy other code can catch.
4. **Context managers** (`with` blocks) — guaranteed cleanup, even on crashes.
5. **pathlib & tempfile** — safe, modern file handling.
6. **PyMuPDF** — opening PDFs, reading text page by page.
7. **Security thinking** — every input is hostile until proven otherwise.

## New dependencies

| Package | Type | Why |
|---|---|---|
| `pymupdf` | runtime | PDF text extraction |
| `reportlab` | dev only | GENERATING synthetic test PDFs (never ships to users) |

## The security threat model (what 2.x defends against)

| Threat | Defense (task) |
|---|---|
| Renamed executable (`evil.exe` → `report.pdf`) | magic-byte check (2.3) |
| Oversized file (memory exhaustion) | size cap BEFORE reading fully (2.3) |
| Unsupported/weird formats | strict allowlist: PDF, PNG, JPEG only (2.3) |
| Corrupt/truncated PDF crashing the pipeline | graceful CorruptDocumentError (2.6) |
| Temp files left on disk with patient data | context-managed cleanup, always (2.5) |
| PHI leaking via filenames/logs | random storage names; log sizes/types only (2.5) |

---

## Tasks

### 2.1 — Concept session: bytes & magic bytes — OWNER: Rohit (~1.5h)
Playground exploration: `open(path, "rb")`, read first 8 bytes of a real
PDF/PNG/JPEG, compare with published signatures (`%PDF-`, `\x89PNG`,
`\xff\xd8\xff`). Rename a file and prove the bytes don't change.

### 2.2 — `schemas/documents.py` — OWNER: Rohit (~1.5h)
New schemas (patterns you already own): `DocumentType` StrEnum (PDF_TEXT,
PDF_SCANNED, IMAGE) · `PageText` (page_number ≥ 1, text, char_count ≥ 0) ·
`ExtractedDocument` (doc_type, pages list, full_text, extraction_method,
ocr_confidence Score | None). Inherits MediScanModel, descriptions everywhere,
plus tests.

### 2.3 — `ingestion/validators.py` — OWNER: Rohit, THE core task (~3h)
- `ingestion/exceptions.py`: `UploadValidationError(Exception)` base +
  `FileTooLargeError`, `UnsupportedFileTypeError`, `SpoofedFileTypeError`.
  Error messages must state limits and detected values (f-string habit).
- `validate_upload(path) -> DocumentType`: size cap (default 20 MB, from
  config) checked via `stat()` BEFORE reading; extension allowlist
  (.pdf/.png/.jpg/.jpeg); magic-byte verification; extension/bytes
  mismatch ⇒ SpoofedFileTypeError.
Claude reviews + writes adversarial tests against it.

### 2.4 — `ingestion/storage.py` — OWNER: Rohit with Claude template (~2h)
`SecureUploadDir` context manager: private temp dir (`tempfile.mkdtemp`),
random UUID filenames (never the user's filename — PHI!), guaranteed
recursive cleanup in `__exit__` even when exceptions fly. Teaching moment:
`__enter__`/`__exit__` protocol.

### 2.5 — Synthetic fixture generator — OWNER: Claude (~2h)
`tests/fixtures/generate.py` (reportlab): a realistic text lab-report PDF
(CBC panel matching our Sprint 1 fixture data), an image-only "scanned"
PDF, a tiny PNG and JPEG, a fake-PDF (wrong magic bytes), a corrupt PDF
(truncated), plus README explaining each. Committed outputs are small and
synthetic. Rohit reviews and runs the generator.

### 2.6 — `ocr/pymupdf_engine.py` — OWNER: pair (~2.5h)
Claude scaffolds the class + docstrings + `CorruptDocumentError` handling;
Rohit implements `extract(path) -> ExtractedDocument` per-page loop guided
by TODOs. Text PDFs get ocr_confidence=None (it's not OCR — honesty in
metadata).

### 2.7 — `ocr/router.py` — OWNER: Rohit (~1.5h)
`detect_document_type(path) -> DocumentType`: open with PyMuPDF, count
extractable characters per page; below threshold ⇒ PDF_SCANNED (Sprint 3
will OCR those), else PDF_TEXT. Threshold in config, not hardcoded.

### 2.8 — Test suite — OWNER: split (~3h)
Rohit: happy-path validator tests + storage cleanup test (assert temp dir
GONE after the `with` block, even after a raised exception).
Claude: adversarial suite — spoofed file, oversize (generated on the fly,
not committed!), corrupt PDF, empty file, router edge cases.

### 2.9 — Integration test — OWNER: pair (~1h)
`tests/integration/test_ingest_to_text.py`: synthetic lab PDF → validate →
store → route → extract → assert known lab values appear in the text.
First test that exercises a real multi-stage flow.

### 2.10 — Sprint close — OWNER: Rohit (~1h)
Docs update (architecture doc gains "implemented" marks), decision-log
entries if any arose, README status line, retro note in 06-reflections.md.

## Exercises

- **Try Yourself:** add BMP-file rejection + its test without any spec from me.
- **Debugging Exercise:** I hand you a PDF that passes validation but makes
  the engine raise — find why using the error message + PyMuPDF docs.
- **Optimization Challenge:** router currently reads ALL pages to decide;
  make it stop early once it has enough evidence (big PDFs get faster).
- **Architecture Reflection:** why does the router live in `ocr/`, not
  `ingestion/`? Could you defend moving it? (5 sentences.)

## Definition of done

- [x] All 2.x tasks merged, CI green (94 tests)
- [x] Adversarial suite: every threat-model row has ≥1 test
- [x] Integration test passes end-to-end
- [x] No real PHI anywhere; fixtures documented (tests/fixtures/files/README.md)
- [x] Retro written (docs/06-reflections.md); Sprint 3 (OCR) unblocked
