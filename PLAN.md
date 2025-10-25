# Reflow OCR Roadmap

## Phase 0. Infrastructure (Apache-2.0 already in repo)
- Init monorepo layout: `frontend/` (Electron + React + Vite), `backend/` (Python + FastAPI).
- Add tooling: Poetry/uv for backend, pnpm/yarn for frontend, shared `scripts/` or Makefile for bootstrap/test/package.
- Define common session schema (JSON AST) and folder conventions for models/cache under `%LOCALAPPDATA%/ReflowOCR` (and platform equivalents).

## Phase 1. Backend Core
- Implement session manager with CRUD, autosave (interval + on-change), `.reflow-session` archive format (zip with `session.json` + `pages/`).
- Expose FastAPI endpoints: `/sessions`, `/sessions/{id}/pages`, `/sessions/{id}/recognize`, `/sessions/{id}/export`.
- Add progress streaming via SSE/WebSocket and in-process async worker with cancellation support.

## Phase 2. OCR Pipeline
- Preprocessing module (OpenCV/imgaug): deskew, denoise, crop, auto-contrast; configurable profiles.
- Layout detection integration: PaddleOCR PP-Structure v3 as primary, LayoutParser + Detectron2 fallback.
- Dual OCR adapters: PaddleOCR (ru+en) + Tesseract 5 (ru+en), confidence fusion and discrepancy logging.
- Post-processing: Jamspell/pymorphy2 for Russian, wordfreq for English, punctuation normalization, list/table heuristics.
- AST builder: Document/Page/Block/Span hierarchy with bboxes, style info, language tags, diff-friendly patching.

## Phase 3. Exporters
- DOCX exporter via python-docx with style templates (default to source-like fonts, allow custom templates).
- PDF exporter via HTML + WeasyPrint (text layer preserved) or borb for precise positioning with embedded fonts.
- Markdown exporter mapping AST to markdown elements and linking embedded images.
- Unified export settings flow between UI and backend (format, fonts, metadata).

## Phase 4. GUI (Electron)
- Scaffold Electron main + React renderer (Vite), global state via Zustand/Redux, IPC bridge to backend.
- Session workspace: page list with thumbnails, drag/drop ordering, clipboard ingest, rotate/delete controls.
- Viewer: canvas/WebGL overlay (Konva) with original vs recognized mode, diff toggles, zoom/pan.
- Editor panel: block metadata, inline text edits, style adjustments synced back to backend via patches.
- Export dialog: select format/template/location, monitor progress, surface logs/errors.

## Phase 5. Quality Controls
- Issues panel: highlight low-confidence words, OCR disagreements, malformed tables.
- Proofreading mode: side-by-side image strip + recognized text for fast validation.
- Undo/redo log per session, autosave every N seconds/actions, history viewer.
- Performance metrics logging (timings, memory) for profiling and diagnostics.

## Phase 6. Tests & Data
- Curate reference datasets (ru/en/mixed) under `tests/data`.
- Unit tests for preprocessing, OCR adapters, AST builder, exporters; golden samples for DOCX/PDF/MD.
- Visual regression pipeline: exported PDF -> PNG -> SSIM comparison.
- End-to-end tests (Playwright/Electron) covering session flow, OCR invocation, export completion.

## Phase 7. Packaging & Platforms
- Windows: electron-builder (NSIS), bundle Python env and model downloader/init scripts.
- macOS: DMG + notarization, align storage paths with `~/Library/Application Support/ReflowOCR`.
- Linux: AppImage/Snap, ensure WeasyPrint/GTK deps packaged.
- Auto-update strategy (Squirrel/NSIS) and session schema migrations.

## Phase 8. Iterative Roadmap
- MVP: session management, OCR pipeline, overlay viewer, DOCX/PDF export, basic edits.
- Iteration 2: Markdown export, diff overlay enhancements, autosave polish, batch import.
- Iteration 3: Advanced table handling, custom font templates, proofing workflow, issues dashboard.
- Iteration 4: macOS/Linux releases, GPU acceleration toggles, optional free cloud OCR fallback.
