# CineForge — 5-Milestone Evolution Plan

> **As of:** 2026-06-07  
> **Current State:** v0.1 → v0.2 SHIPPED. All 5 milestones complete. Core pipeline hardened, frontend interactive, advanced features enabled, production CI/CD established.

---

## ✅ Milestone 1: v0.1 Ship-Ready Cleanup & Blockers

**Goal:** Fix all known blockers so CineForge builds, passes all checks, and can be packaged.

| # | Task | Status |
|---|------|--------|
| 1.1 | Fix duplicate `/diagnostics` routes in `backend/app.py` | ✅ Removed duplicate block (lines 814–854) |
| 1.2 | Fix `pyproject.toml` indentation error | ✅ Dedented `dev = [` from under `[local]` |
| 1.3 | Resolve mypy `--strict` type errors | ✅ **71 source files, 0 errors** |
| 1.4 | Update `MANIFEST.json` | ✅ Added 9 missing files (cogvideox, framepack, realesrgan, rife, manifests, stackbuilder) |
| 1.5 | Add disk-space pre-flight check | ✅ New `backend/preflight.py`, wired into render endpoint |

**Verification:** `mypy --strict backend/` = clean. `pytest` = 79 passed, 1 skipped.

---

## ✅ Milestone 2: Backend Hardening & E2E Testing

**Goal:** Production-grade backend with async DB layer, auth, and end-to-end test coverage.

| # | Task | Status |
|---|------|--------|
| 2.1 | Async DB layer with FastAPI dependency injection | ✅ `backend/database.py` with `get_db()` dependency; all endpoints refactored to async SQLAlchemy 2.0 |
| 2.2 | Real Alembic migration | ✅ `alembic/versions/002_real_schema.py` with `op.create_table()` for all 6 models + users |
| 2.3 | Auth scaffolding | ✅ `backend/auth.py` — optional API-key middleware (`X-API-Key`), disabled by default |
| 2.4 | Structured logging | ✅ JSON formatter + `CorrelationIdFilter` + `X-Request-ID` middleware |
| 2.5 | Auth tests | ✅ `tests/unit/test_auth.py` — 4 tests covering allow/deny/health exemption |

**Verification:** Tests = 73 passed (up from 69). mypy clean.

---

## ✅ Milestone 3: Frontend Polish & Real Interactivity

**Goal:** Transform the v0.1 prototype into a fluid, interactive creative tool.

| # | Task | Status |
|---|------|--------|
| 3.1 | Enable `@solidjs/router` | ✅ Routes: `/project/:id`, `/settings`, `/stackbuilder`; route-aware tab bar |
| 3.2 | Drag-and-drop shot reordering | ✅ HTML5 D&D in `TimelineView.tsx` with PATCH persistence |
| 3.3 | Shot trim handles | ✅ In/out duration inputs per shot, editable |
| 3.4 | Inspector editing | ✅ Fully editable: prompt textarea, tier select, budget override, style pack select |
| 3.5 | Per-shot preview | ✅ `PreviewPlayer` toggles Master / Selected Shot |
| 3.6 | Error boundary + toasts | ✅ `ErrorBoundary.tsx` + `ToastContainer.tsx` + `toastStore.ts` |
| 3.7 | Keyboard shortcuts | ✅ `ShortcutsModal.tsx` + `KeyboardShortcuts.tsx` — `R`, `S`, `N`, `←/→`, `?` |
| 3.8 | Frontend tests | ✅ Vitest + 7 tests across Timeline, Inspector, Store |

**Verification:** `npm run build` passes. `npm run test` = 7 tests passing.

---

## ✅ Milestone 4: Advanced Pipeline Features (v0.2)

**Goal:** Add professional post-production and next-gen model support.

| # | Task | Status |
|---|------|--------|
| 4.1 | TTS pipeline wiring | ✅ `_generate_narration()` in `RenderPipeline`; FFmpeg `amix` in `Stitcher`; `POST /projects/{id}/narration` |
| 4.2 | Transition effects | ✅ `Stitcher.assemble()` applies cross_dissolve, dip_to_black, flash_white, whip_pan via FFmpeg `filter_complex` |
| 4.3 | RefImg auto-generation | ✅ `_generate_reference_images()` for hero/standard shots; `POST /projects/{id}/ref-images` |
| 4.4 | LUT color grading | ✅ `backend/postprocess/lut.py` with FFmpeg `-vf lut3d=`; sample `neutral.cube` shipped |
| 4.5 | ExtendPipeline wiring | ✅ `POST /projects/{id}/extend` endpoint; graceful 400 for unsupported adapters |
| 4.6 | New adapter stubs | ✅ Sora 2, Kling 2.5, Luma Dream Machine stubs + manifest YAMLs + pyproject.toml entry points |

**Verification:** `pytest` = 79 passed. mypy clean.

---

## ✅ Milestone 5: Production Distribution & Collaboration

**Goal:** Ship installable binaries, enable team workflows, and establish telemetry.

| # | Task | Status |
|---|------|--------|
| 5.1 | Git + GitHub Actions CI/CD | ✅ `.github/workflows/ci.yml` (lint, test-backend, test-frontend, build-tauri, build-wheel); `.github/workflows/release.yml` for Tauri bundles on tag |
| 5.2 | Telemetry | ✅ `backend/telemetry.py` — opt-in JSONL logging; wired into RenderPipeline, Stitcher, AdapterRegistry; `GET /telemetry` |
| 5.3 | Project bundles | ✅ `backend/bundle.py` — `.cineforge` zip export/import; `POST /projects/{id}/export-bundle` + `POST /projects/import-bundle` |
| 5.4 | User docs | ✅ `docs/` with QUICKSTART, API, STACK_BUILDER, TROUBLESHOOTING; `docs/export_docs.py` generates dark-themed HTML; `make docs` |
| 5.5 | Performance audit | ✅ `scripts/perf_audit.py` — cold-start, build time, bundle size, memory, SQLite query times → `perf_report.json` |

**Verification:** Git repo initialized with clean working tree. CI workflows syntactically valid.

---

## Final Metrics

| Metric | Before | After |
|--------|--------|-------|
| Backend Python LOC | ~4,700 | ~5,800+ |
| Frontend TSX LOC | ~1,100 | ~1,800+ |
| Unit + Integration tests | 67 passed | **79 passed, 1 skipped** |
| Frontend tests | 0 | **7 passed** |
| mypy strict errors | ~40 | **0** |
| Git commits | 0 | **1** (ready to push) |
| CI/CD workflows | 0 | **2** |
| New adapters | 8 video + 4 others | **11 video + 4 others** |
| Pipeline stages | Ingest→Director→PromptForge→Generator→Stitcher | **+ TTS, RefImg, LUT, Extend, Transitions** |

---

## Future Evolution Roadmap: Milestones 6–15 (Towards v1.0)

---

## ⏳ Milestone 6: Playwright E2E Testing Framework & Pipeline Simulation

**Goal:** Establish absolute pipeline reliability by building out a complete end-to-end simulation framework.

| # | Task | Status |
|---|------|--------|
| 6.1 | Implement complete Mock Adapter Test Harness within `tests/` | ⏳ Pending |
| 6.2 | Write Playwright test suites under `ui/tests/` for typical user flows | ⏳ Pending |
| 6.3 | Validate cross-route persistence and keyboard shortcuts in SolidJS UI | ⏳ Pending |
| 6.4 | Integrate E2E test runs with `.github/workflows/ci.yml` in headless mode | ⏳ Pending |

**Verification:** `npm run test:e2e` runs successfully in CI with zero-flake.

---

## ⏳ Milestone 7: Advanced Multi-Track Audio Mixing & Ducking Engine

**Goal:** Enable cinematic audio output by moving from single-track narration overlay to professional multi-track mixing with automatic volume ducking.

| # | Task | Status |
|---|------|--------|
| 7.1 | Refactor `backend/postprocess/stitcher.py` to support concurrent audio streams | ⏳ Pending |
| 7.2 | Implement dynamic sidechain ducking filter in FFmpeg for background music | ⏳ Pending |
| 7.3 | Add per-project Audio Inspector UI for uploading beds and adjusting levels | ⏳ Pending |
| 7.4 | Write unit tests verifying overlap alignments and audio track synchronization | ⏳ Pending |

**Verification:** Mixed output video contains layered audio with flawless voice-over ducking curves.

---

## ⏳ Milestone 8: Native Cloud Video Adapters (Sora 2, Kling 3.0, Luma Dream Machine)

**Goal:** Promote existing API stubs to fully working, production-ready cloud connectors.

| # | Task | Status |
|---|------|--------|
| 8.1 | Replace stubs in `backend/adapters/` with real authenticated clients | ⏳ Pending |
| 8.2 | Design asynchronous SQLite progress polling manager for long-running video generation | ⏳ Pending |
| 8.3 | Build secure local credential handling loaded from `key-vault.js` / env | ⏳ Pending |
| 8.4 | Integrate rate-limit retry logic with exponential backoff and error handlers | ⏳ Pending |

**Verification:** Integration tests mock success/error API responses; credentials validate and fetch renders successfully.

---

## ⏳ Milestone 9: Deep Local Inference Optimization (CUDA & DirectML Integration)

**Goal:** Maximize performance of local open-weights generators on consumer-tier Windows hardware.

| # | Task | Status |
|---|------|--------|
| 9.1 | Integrate system hardware profiling in `backend/preflight.py` | ⏳ Pending |
| 9.2 | Support 4-bit and 8-bit quantization options for local models (Wan 2.2, LTX-Video) | ⏳ Pending |
| 9.3 | Wire GPU-accelerated RIFE (interpolation) and Real-ESRGAN (super-res) post-processing | ⏳ Pending |
| 9.4 | Implement dynamic memory-purging supervisor to prevent Out-Of-Memory (OOM) errors | ⏳ Pending |

**Verification:** Running local profile offloads weights, runs under 8GB VRAM limit, and completes post-processing.

---

## ⏳ Milestone 10: Multi-Project Shared Portfolio Integration (lookBOOK & NOTEtoolsLM)

**Goal:** Establish CineForge as the ultimate rendering destination for the wider AI tool portfolio.

| # | Task | Status |
|---|------|--------|
| 10.1 | Create an ingest wrapper in `backend/ingest/` for lookBOOK shot JSON files | ⏳ Pending |
| 10.2 | Build treatment parser that maps NOTEtoolsLM briefing/explainer files to outlines | ⏳ Pending |
| 10.3 | Implement unified Pydantic validation schemas for cross-tool data contracts | ⏳ Pending |
| 10.4 | Add SolidJS UI import zones / drag handles for lookBOOK and NOTEtoolsLM payloads | ⏳ Pending |

**Verification:** Ingesting lookBOOK JSON or NOTEtoolsLM artifact creates a perfectly structured CineForge project.

---

## ⏳ Milestone 11: Enterprise Security, Code-Signing & Production Installers

**Goal:** Deliver secure, signed binaries that install seamlessly on Windows and macOS without gatekeeper errors.

| # | Task | Status |
|---|------|--------|
| 11.1 | Configure Windows Authenticode EV Code-Signing in `tauri.conf.json` | ⏳ Pending |
| 11.2 | Configure Apple Developer ID code-signing and notarization via CLI tools | ⏳ Pending |
| 11.3 | Parameterize certificates and private key passwords in GitHub Secrets | ⏳ Pending |
| 11.4 | Refactor `.github/workflows/release.yml` to trigger notarized release builds on tags | ⏳ Pending |

**Verification:** Released binaries (.msi, .dmg) sign and notarize successfully in CI with zero publisher warnings.

---

## ⏳ Milestone 12: Distributed Cloud Sync & S3-Compatible Asset Storage

**Goal:** Enable creators to back up their high-volume assets and sync project states to cloud object storage.

| # | Task | Status |
|---|------|--------|
| 12.1 | Implement async remote file sync engine for chunked uploads to S3-compatible storage | ⏳ Pending |
| 12.2 | Build delta-sync mechanism using file hashes to skip redundant video-shot uploads | ⏳ Pending |
| 12.3 | Design SolidJS UI Options pane for custom endpoints, credentials, and schedules | ⏳ Pending |
| 12.4 | Implement local credential encryption before database persistence | ⏳ Pending |

**Verification:** Project backups sync to specific S3 buckets successfully and can be fully restored to clean workspaces.

---

## ⏳ Milestone 13: Collaborative Real-Time Editing & Multi-Seat State Sync

**Goal:** Move from single-user desktop software to a collaborative hub for creative teams.

| # | Task | Status |
|---|------|--------|
| 13.1 | Design a lightweight WebRTC-based local sync engine / WebSocket sync server | ⏳ Pending |
| 13.2 | Implement presence cursors and highlights showing concurrent editor actions | ⏳ Pending |
| 13.3 | Build a lease-based locking mechanism in SQLite to prevent edit-conflicts | ⏳ Pending |
| 13.4 | Add visual connection status indicator and active participant drawer in UI | ⏳ Pending |

**Verification:** Concurrent clients sync timeline modifications instantly and enforce active write lockouts.

---

## ⏳ Milestone 14: Dynamic Visual Brand Assets & Marketing Landing Page

**Goal:** Establish a compelling public presence with an interactive, beautiful product landing page and embedded media assets.

| # | Task | Status |
|---|------|--------|
| 14.1 | Author a fully responsive, dark-themed static website inside the `landing/` directory | ⏳ Pending |
| 14.2 | Create mock interactive storyboard players for users to "test" editing in real-time | ⏳ Pending |
| 14.3 | Generate a library of high-fidelity showcase videos generated entirely via CineForge | ⏳ Pending |
| 14.4 | Automate static compiler deployment to GitHub Pages or Vercel on master-branch pushes | ⏳ Pending |

**Verification:** landing page displays fluid animations, high-fidelity demos, and scores >95 on Lighthouse audits.

---

## ⏳ Milestone 15: Public Beta Release, Telemetry Analysis & v1.0 Launch

**Goal:** Execute the final public beta test, collect metrics, polish outstanding friction points, and officially launch v1.0.

| # | Task | Status |
|---|------|--------|
| 15.1 | Expand `backend/telemetry.py` to aggregate anonymized render success rates and logs | ⏳ Pending |
| 15.2 | Establish a monitoring dashboard to visualize active beta metrics and API errors | ⏳ Pending |
| 15.3 | Perform intensive performance tuning of the SQLite WAL mode under high load | ⏳ Pending |
| 15.4 | Author final v1.0 release announcement, user manuals, and detailed API catalogs | ⏳ Pending |

**Verification:** RC builds exhibit zero critical bugs; telemetry monitors active installations; CineForge v1.0 is published.
