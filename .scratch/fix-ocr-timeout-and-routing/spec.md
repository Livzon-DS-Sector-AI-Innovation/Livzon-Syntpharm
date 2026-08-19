---
title: "Fix OCR timeout and add intelligent engine routing for scanned PDF extraction"
status: ready-for-agent
labels:
  - ready-for-agent
  - bug
  - performance
  - registration
  - dossier-writer
created: 2026-08-19
blocked_by: []
---

# 15 — Fix OCR timeout and add intelligent engine routing for scanned PDF extraction

## Problem Statement

When a user uploads a scanned PDF (image-only, no extractable text) to the Dossier Writer module and triggers AI-based page splitting or field filling, the backend attempts OCR extraction via PaddleOCR. Two problems cause this to fail:

1. **Performance**: The current code passes the PDF file path directly to PP-StructureV3, which loads 12+ ML models (layout detection, table recognition, formula recognition, etc.) and processes each page through all of them. On CPU-only deployments, this takes 30–60 seconds per page. A 5-page scanned PDF exceeds the 180-second timeout and returns a 500 error.

2. **Concurrency bug**: When the OCR service is initializing (which takes ~60 seconds on first request), `_ensure_ocr_service()` sees `_ocr_initializing = True` and immediately returns `None` instead of waiting. The user gets a "service unavailable" error even though initialization would complete in moments.

The user-facing symptom: uploading a scanned PDF and clicking "AI 拆分预览" (AI Split Preview) results in a 500 error after 180 seconds, with no feedback about what's happening.

## Solution

Two changes:

1. **Hybrid OCR routing**: Pre-scan the PDF with pdfplumber to detect whether it contains tables, images, or complex layouts. Route simple scanned PDFs to PP-OCR (fast, 2 models, ~5–10s/page) and complex documents to PP-StructureV3 (structured output, 12+ models, ~30–60s/page). Convert PDF pages to images with pypdfium2 before passing to OCR, bypassing the slow PDF-to-image path inside PaddleOCR.

2. **Concurrency wait**: When `_ensure_ocr_service()` is called while initialization is in progress, wait up to 60 seconds (polling every 1 second) instead of returning `None` immediately.

## User Stories

1. As a registration specialist, I want scanned PDF documents to be processed without timeout errors, so that I can use AI-assisted field filling on regulatory submissions.
2. As a registration specialist, I want simple scanned PDFs (text-only images) to be processed quickly, so that I don't wait 5+ minutes for basic text extraction.
3. As a registration specialist, I want complex scanned PDFs (with tables, formulas, multi-column layouts) to be processed with structure preservation, so that table data is not mangled.
4. As a system, I want to automatically detect whether a scanned PDF needs fast or structured OCR, so that users don't have to manually choose.
5. As a system, I want to wait for OCR service initialization instead of failing immediately, so that the first request after a cold start succeeds.
6. As a system, I want to log which OCR engine was chosen and why (with pre-scan results), so that routing issues can be debugged in production.
7. As a system, I want to convert PDF pages to images before OCR, so that pypdfium2 handles the rendering (fast, reliable) instead of relying on PaddleOCR's internal PDF path.
8. As a system, I want generous timeouts (300s init, 600s extraction) to handle edge cases like slow CPUs, large PDFs, and model download delays.
9. As a frontend, I want a 20-minute request timeout for AI preview and confirm operations, so that long OCR + LLM processing doesn't get cancelled.
10. As a system, I want per-page progress logging during OCR extraction, so that operators can monitor processing status.
11. As a system, I want to return accurate `page_count` and `page_texts` from OCR extraction, so that downstream AI processing has correct per-page content (previously all content was returned as page 1).

## Implementation Decisions

### Module: `AssetTextExtractor` (backend/app/modules/registration/dossier_writer/asset_text_extractor.py)

**New method: `_should_use_structure(file_path: Path) -> bool`**

Uses pdfplumber to pre-scan the PDF and decide routing:
- Open PDF with pdfplumber
- For each page, check:
  - `page.find_tables()` — if any page has tables, return `True`
  - Count images per page — if any page has >1 large image, return `True`
  - Check text density — if text is present but sparse (<10% of page area), return `True`
- Default to `False` (use PP-OCR) if no complex signals detected
- Log detailed pre-scan results at INFO level: table count, image count, text density, routing decision

**Modified method: `_extract_pdf(file_path: Path)`**

After pdfplumber fails to extract text (scanned PDF):
1. Call `_should_use_structure(file_path)` to determine routing
2. Convert PDF pages to images using pypdfium2:
   - `pdfium.PdfDocument(file_path)`
   - For each page: `page.render(scale=2.0)` → `bitmap.to_pil()` → PIL Image
3. Route based on pre-scan result:
   - If `False`: use `ocr_service.extract_text(img)` (PP-OCR, fast)
   - If `True`: use `ocr_service.extract_markdown(img)` (PP-StructureV3, structured)
4. Process pages sequentially, logging progress: `OCR 处理进度: 第 X/N 页`
5. Track `pages_processed` count for error messages
6. Return accurate `page_count` and `page_texts` (one entry per page, not all content as page 1)

**Modified method: `_ensure_ocr_service(timeout: int = 300)`**

- Increase default timeout from 180s to 300s
- If `_ocr_initializing` is `True`:
  - Poll every 1 second, up to 60 seconds
  - Return service if init completes within 60s
  - Return `None` if 60s exceeded
- This replaces the current behavior of returning `None` immediately

**Timeout changes:**
- OCR init timeout: 180s → 300s
- OCR extraction timeout: 180s → 600s (10 minutes)
- Concurrency wait: 0s (immediate fail) → 60s (poll with timeout)

### Module: Frontend Server Actions (frontend/src/actions/dossier-writer.ts)

**Modified functions: `aiPreviewExtraction`, `aiConfirmAndFill`**

- Increase `AbortSignal.timeout` from 600000ms (10 min) to 1200000ms (20 min)
- This covers OCR init (300s) + OCR extraction (600s) + LLM processing

### Logging

All routing decisions logged at INFO level:
- Pre-scan results: table count, image count, text density per page
- Routing decision: "Using PP-OCR (fast)" or "Using PP-StructureV3 (structured)"
- Per-page progress: "OCR 处理进度: 第 X/N 页"
- Per-page completion: "第 X 页完成，提取 N 字符"

### Error messages

Timeout error message now includes pages processed:
- Old: "该 PDF 为扫描件，OCR 提取超时（180秒）。请上传可复制文本的 PDF、Word 或 Excel 文件。"
- New: "该 PDF 为扫描件，OCR 提取超时（600秒）。已处理 3/5 页。请上传可复制文本的 PDF、Word 或 Excel 文件，或考虑拆分 PDF 后分批处理。"

## Testing Decisions

### What makes a good test

Test external behavior, not implementation details. The routing logic should be tested via the public `extract()` method with fixture PDFs, not by mocking internal methods.

### Modules to test

1. **`AssetTextExtractor._should_use_structure()`**
   - Unit test with fixture PDFs:
     - Simple scanned PDF (1 image per page, no tables) → `False`
     - Complex scanned PDF (tables detected) → `True`
     - Mixed PDF (some pages with tables, some without) → `True`
   - Prior art: `backend/tests/modules/registration/dossier_writer/test_models.py`

2. **`AssetTextExtractor._extract_pdf()` routing**
   - Integration test with fixture PDFs:
     - Simple scanned PDF routes to PP-OCR
     - Complex scanned PDF routes to PP-StructureV3
   - Mock OCRService to verify which method was called (`extract_text` vs `extract_markdown`)
   - Verify `page_count` and `page_texts` are accurate (not all content as page 1)

3. **`AssetTextExtractor._ensure_ocr_service()` concurrency**
   - Unit test:
     - Start init in background thread
     - Call `_ensure_ocr_service()` while init is in progress
     - Verify it waits and returns the service (not `None`)
   - Unit test:
     - Simulate init that takes longer than 60s
     - Verify `_ensure_ocr_service()` returns `None` after 60s

### Fixture PDFs

Create minimal fixture PDFs in `backend/tests/fixtures/`:
- `simple_scanned.pdf` — 2 pages, each with 1 image, no text, no tables
- `complex_scanned.pdf` — 2 pages, each with 1 image + 1 table (use reportlab or similar to generate)

## Out of Scope

- **Fallback strategy**: If auto-detection picks PP-OCR and output is poor, there is no automatic retry with PP-StructureV3 in v1. Users can manually retry or upload a different format. Fallback can be added later if users report quality issues.
- **Progress bar in UI**: The backend logs per-page progress, but the frontend does not display a progress bar. The request is a single blocking POST. Real-time progress would require SSE/WebSocket, which is out of scope.
- **GPU support**: This spec assumes CPU-only deployment. GPU support would make PP-StructureV3 fast enough that routing is unnecessary, but requires hardware changes.
- **Alternative OCR engines**: RapidOCR, Marker, MinerU, etc. are not considered. PaddleOCR is the current engine, and this spec optimizes its usage, not replaces it.
- **Eager OCR init at startup**: The OCR service is still initialized lazily on first request. Eager init would eliminate the 60s wait for the first request, but requires changes to the app startup lifecycle.

## Further Notes

### Why hybrid routing?

PP-StructureV3 is the most capable open-source document parser available (tables, formulas, layout detection, markdown output), but it's too slow on CPU for simple text extraction. PP-OCR is 5–10x faster but loses structure. The hybrid approach gives us the best of both: fast processing for simple documents, structured output for complex ones.

### Why pypdfium2 for PDF-to-image?

PaddleOCR's internal PDF rendering path uses pypdfium2 as well, but the integration has issues (the `std::exception` error we observed). By converting PDF pages to images ourselves with pypdfium2, we:
1. Bypass the buggy internal path
2. Control the rendering parameters (DPI, scale)
3. Enable per-page progress tracking

### Why no fallback?

Fallback adds complexity (retry logic, quality scoring, user notification). In v1, we trust the auto-detection. If users report quality issues, we can add fallback in v2 with a "Retry with structure" button or automatic quality-based retry.

### Why 600s extraction timeout?

Observed timings on CPU:
- PP-OCR: 5–10s/page
- PP-StructureV3: 30–60s/page
- 10-page complex PDF: 300–600s

600s (10 minutes) handles a 10-page complex PDF with headroom. If users need to process longer documents, they should split the PDF.

### Why 60s concurrency wait?

Observed OCR init time: ~60s. If init takes longer than 60s, something is likely wrong (model download failure, resource exhaustion). Failing after 60s is better than waiting indefinitely.
