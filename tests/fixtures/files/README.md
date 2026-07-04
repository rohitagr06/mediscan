# Synthetic test documents

All files here are FABRICATED by `tests/fixtures/generate.py` (decision
#010: no real medical documents in this repo, ever). Regenerate with:

    uv run python tests/fixtures/generate.py

| File | What it is | Expected behavior |
|---|---|---|
| cbc_report.pdf | 2-page TEXT PDF, fake CBC (Hb 9.8 L, TLC 11.2 H, Plt 250) | validated PDF_TEXT; extraction finds known values |
| scanned_report.pdf | PDF with NO text layer (drawings only) | validated PDF_TEXT; router reclassifies PDF_SCANNED |
| sample.png / sample.jpg | tiny valid images | validated IMAGE |
| spoofed.pdf | PNG bytes named .pdf | REJECTED: SpoofedFileTypeError |
| corrupt.pdf | real PDF truncated mid-body | passes validation, FAILS extraction (CorruptDocumentError) |
| report_photo.png | IMAGE of CBC text (pixels, no characters) | validated IMAGE; OCR must read the values out of it |
| scanned_cbc.pdf | that image embedded in a PDF page — a true synthetic scan | router: PDF_SCANNED; scanned-PDF path OCRs real content |
