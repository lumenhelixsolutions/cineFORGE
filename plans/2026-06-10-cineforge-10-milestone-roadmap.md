# CineForge Phase 2: 10-Milestone Evolution Roadmap (v0.3 to v1.0)

> **Date:** June 10, 2026  
> **Status:** Draft / Strategic Intent  
> **Author:** Gemini Code CLI Agent  
> **Reference File:** `MILESTONES.md` (Updated to version v0.3 - v1.0)

---

## Executive Summary
Following the successful shipment of CineForge v0.2 (Milestones 1–5), which established the core local-first video generation pipeline, interactive SolidJS UI, and comprehensive testing framework, we present the Phase 2 roadmap. This roadmap maps out **10 consecutive milestones (Milestones 6 to 15)** designed to take CineForge from a functional beta prototype to a bulletproof, production-grade, highly integrated v1.0 platform.

These milestones tackle remaining gaps, open issues, and integration possibilities across the broader project portfolio, ensuring that CineForge serves as a premier video-generation node in the collective developer OS ecosystem.

---

## The 10 Milestones (Phase 2)

```
       [Milestone 6] ──> Playwright E2E & Full Pipeline Simulation
             │
       [Milestone 7] ──> Advanced Multi-Track Audio & Auto-Ducking
             │
       [Milestone 8] ──> Live Cloud Adapters (Sora 2, Kling 3.0, Luma DM)
             │
       [Milestone 9] ──> Local Inference Optimization (CUDA/DirectML & Quantization)
             │
       [Milestone 10] ──> Portfolio Bridges (lookBOOK & NOTEtoolsLM Ingest)
             │
       [Milestone 11] ──> EV Code-Signing & Signed Multi-OS Installers
             │
       [Milestone 12] ──> Distributed Cloud Sync & S3 Asset Backup
             │
       [Milestone 13] ──> Collaborative Real-Time Editing & Sync
             │
       [Milestone 14] ──> Dark-Themed Landing Page & Showcase Assets
             │
       [Milestone 15] ──> Public Beta, Telemetry Analysis & v1.0 Launch
```

---

### Milestone 6: Playwright E2E Testing Framework & Pipeline Simulation
**Goal:** Establish absolute pipeline reliability by building out a complete end-to-end simulation framework.

*   **Rationale:** The initial v0.1 Playwright scaffold is currently unimplemented. To prevent regression during rapid feature additions, we need to mock out video adapters and run simulated E2E runs covering the entire app lifecycle.
*   **Tasks:**
    1. Implement a complete Mock Adapter Test Harness within `tests/` that simulates long-running video generation and audio stitching without making external API calls.
    2. Write Playwright test suites (located under `ui/tests/`) mapping out typical user flows: project creation, source document uploading, storyboard generation, manual prompt override, and simulated export.
    3. Validate cross-route persistence and keyboard shortcuts in the UI during browser interactions.
    4. Connect the E2E suite to `.github/workflows/ci.yml` so it runs headlessly on every pull request.
*   **Verification:** `npm run test:e2e` runs successfully in CI; zero-flake execution with full HTML reporting.

---

### Milestone 7: Advanced Multi-Track Audio Mixing & Ducking Engine
**Goal:** Enable cinematic audio output by moving from single-track narration overlay to professional multi-track mixing with automatic volume ducking.

*   **Rationale:** Creators need background music beds and environmental soundscapes (SFX) that gracefully yield to voice-over narration. Doing this manually is tedious; automating this in FFmpeg makes it a push-button feature.
*   **Tasks:**
    1. Refactor `backend/postprocess/stitcher.py` (and the underlying FFmpeg wrapper) to support concurrent audio streams: Voice/Narration, Music, and Ambient SFX.
    2. Implement dynamic sidechain ducking via FFmpeg complex filters (`[narration]asplit[n1][n2];[music][n1]sidechaincompress=threshold=0.15:ratio=4[music_ducked];[music_ducked][n2]amix`).
    3. Add a per-project `Audio Inspector` in the UI to upload background music, set master volume levels, and choose pre-set ducking curves (Gentle, Dramatic, None).
    4. Write comprehensive unit tests verifying multiple overlapping audio clips and track alignment.
*   **Verification:** Output videos generated contain layered audio with flawless ducking curves; `pytest tests/unit/test_stitcher.py` verifies correct FFmpeg command assembly.

---

### Milestone 8: Native Cloud Video Adapters (Sora 2, Kling 3.0, Luma Dream Machine)
**Goal:** Promote existing API stubs to fully working, production-ready cloud connectors.

*   **Rationale:** While local inference is cost-effective, premium cloud generators represent the high-fidelity vanguard. Replacing mock stubs with live APIs enables production-ready, commercial-grade rendering.
*   **Tasks:**
    1. Implement real API connectors in `backend/adapters/` using official SDKs or raw HTTP clients for Sora 2, Kling 3.0, and Luma DM.
    2. Design an asynchronous polling manager using SQLite to track progress, handling long render times (1–5 minutes) without blocking Python or Tauri threads.
    3. Build secure local credential handling inside `config/` (never committing keys, loading from `key-vault.js` / environment variables).
    4. Integrate rate-limit retry logic with exponential backoff and error handlers for transient network issues.
*   **Verification:** Integration tests with mocked server responses pass cleanly; credentials successfully validate, poll, and fetch completed video files on live endpoints.

---

### Milestone 9: Deep Local Inference Optimization (CUDA & DirectML Integration)
**Goal:** Maximize performance of local open-weights generators on consumer-tier Windows hardware.

*   **Rationale:** Running Wan 2.2, LTX-Video, or HunyuanVideo locally is highly desirable but severely VRAM-constrained. Optimizing memory offloading and quantization allows creators to utilize 8GB or even 6GB GPUs.
*   **Tasks:**
    1. Integrate automated system hardware profiling in `backend/preflight.py` to auto-detect Nvidia (CUDA) and AMD (DirectML) hardware capabilities.
    2. Support 4-bit and 8-bit weights loading via `diffusers` or custom `llama.cpp`-style loaders, adjusting model parameters based on free VRAM.
    3. Wire the GPU-accelerated versions of RIFE (frame interpolation) and Real-ESRGAN (super-resolution upscaling) into the local post-processing export pipe.
    4. Write a dynamic memory-purging supervisor that unloads LLM weights before launching the diffusion models to prevent out-of-memory (OOM) errors.
*   **Verification:** Running the local profile successfully offloads models, runs under 8GB VRAM limit, and completes interpolation and upscaling steps without crashing the backend thread.

---

### Milestone 10: Multi-Project Shared Portfolio Integration (lookBOOK & NOTEtoolsLM)
**Goal:** Establish CineForge as the ultimate rendering destination for the wider AI tool portfolio.

*   **Rationale:** The project directory includes lookBOOK (a book-to-animation compiler) and NOTEtoolsLM-v2 (a notebook deep-dive engine). Creating native ingestion bridges saves creative context and automates cross-app production.
*   **Tasks:**
    1. Create an ingest wrapper in `backend/ingest/` that accepts lookBOOK shot JSON files, converting panel/motion meta into CineForge storyboard cards.
    2. Build a treatment parser that takes NOTEtoolsLM briefing/explainer markdown files and automatically maps them into structured, multi-scene video outlines.
    3. Implement unified Pydantic validation schemas to guarantee data contract alignment across the tools.
    4. Add dedicated import buttons/drag-zones in the SolidJS UI for lookBOOK and NOTEtoolsLM payload outputs.
*   **Verification:** Ingesting a lookBOOK JSON or NOTEtoolsLM artifact creates a perfectly structured CineForge project; unit tests verify schema compatibility.

---

### Milestone 11: Enterprise Security, Code-Signing & Production Installers
**Goal:** Deliver secure, signed binaries that install seamlessly on Windows and macOS without gatekeeper errors.

*   **Rationale:** Unsigned applications trigger aggressive OS security warnings ("Unknown Publisher" on Windows, "Damaged App" on macOS) which damage credibility and user adoption.
*   **Tasks:**
    1. Configure Windows Authenticode EV Code-Signing using Signtool in the Tauri release configuration (`tauri.conf.json`).
    2. Configure Apple Developer ID code-signing and notarization via standard CLI tools (`gon` or Apple notarization service integration).
    3. Securely parameterize signing certificates and private key passwords in GitHub Secrets for CI compilation.
    4. Refactor `.github/workflows/release.yml` to trigger full packaging, signing, and verification on git tags.
*   **Verification:** Compilation triggers in CI produce signed `.msi`, `.dmg`, and `.AppImage` files; testing installation on fresh OS environments shows zero warnings.

---

### Milestone 12: Distributed Cloud Sync & S3-Compatible Asset Storage
**Goal:** Enable creators to back up their high-volume assets and sync project states to cloud object storage.

*   **Rationale:** Raw render steps, high-resolution textures, and audio assets can quickly consume gigabytes. A local-first application needs a low-friction option to offload older projects to personal S3/R2 cloud storage.
*   **Tasks:**
    1. Implement an asynchronous remote file sync engine in `backend/bundle.py` that streams project bundles in chunks to S3-compatible endpoints (AWS, Cloudflare R2, MinIO).
    2. Build a delta-sync mechanism that compares local file hashes against remote hashes, only uploading modified or newly generated video shots.
    3. Design an options pane in the UI Settings screen for configuring S3 credentials, custom endpoint URLs, and default backup schedules.
    4. Implement secure credential encryption before persisting keys in the local SQLite config database.
*   **Verification:** Triggering a cloud backup uploads project resources to the specified bucket; remote assets can be restored to a clean workspace with 100% integrity.

---

### Milestone 13: Collaborative Real-Time Editing & Multi-Seat State Sync
**Goal:** Move from single-user desktop software to a collaborative hub for creative teams.

*   **Rationale:** Modern media production requires collaborative review where a director and writer can view storyboards and suggest edits concurrently.
*   **Tasks:**
    1. Design a lightweight WebRTC-based local sync engine or standard WebSocket state-sharing server.
    2. Implement visual presence cues showing which shot or panel another user is currently actively reviewing or editing.
    3. Build a lease-based locking mechanism in the SQLite database layer to prevent write-conflicts when two users edit the same prompt block.
    4. Add a visual connection status indicator and active participant drawer in the UI header.
*   **Verification:** Opening multiple browser or desktop clients pointing to the same workspace updates text and timeline positions simultaneously; active edits cleanly lock out concurrent attempts.

---

### Milestone 14: Dynamic Visual Brand Assets & Marketing Landing Page
**Goal:** Establish a compelling public presence with an interactive, beautiful product landing page and embedded media assets.

*   **Rationale:** A great tool needs an equally compelling storefront to convert interest into active users and beta testers.
*   **Tasks:**
    1. Author a fully responsive, dark-themed static website inside the `landing/` directory featuring smooth transitions and beautiful typography.
    2. Create mock interactive storyboard players showing CineForge's actual timeline, allowing users to "test" changing prompts and seeing simulated renders in real-time.
    3. Generate a library of high-fidelity showcase videos using CineForge and embed them on the page.
    4. Automate static file compilation and deployment to GitHub Pages or Vercel on pushes to the master branch.
*   **Verification:** Visual assets render beautifully across all screen resolutions; the deployed landing page runs fast, scoring >95 on Lighthouse audits.

---

### Milestone 15: Public Beta Release, Telemetry Analysis & v1.0 Launch
**Goal:** Execute the final public beta test, collect metrics, polish outstanding friction points, and officially launch v1.0.

*   **Rationale:** The final push to 1.0 requires grounding our assumptions in real-world telemetry, tracking failure rates of video adapters, and providing comprehensive onboarding paths.
*   **Tasks:**
    1. Expand `backend/telemetry.py` to aggregate anonymized render success rates, average generation times, and system error crash logs.
    2. Establish a simple monitoring dashboard to visualize active beta metrics and isolate breaking APIs/adapters.
    3. Perform intensive performance tuning of the SQLite WAL mode under concurrent operations and file-system read speeds.
    4. Formulate the official v1.0 release announcement, complete user manual, and API catalog.
*   **Verification:** Release builds demonstrate zero open critical bugs; telemetry dashboard receives and processes client statistics; CineForge v1.0 is successfully published.
