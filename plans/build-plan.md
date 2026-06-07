# CineForge v0.1 Build Plan

## Phase 1: Skeleton (DONE)
- [x] Repo structure
- [x] pyproject.toml, Cargo.toml, tauri.conf.json
- [x] CLAUDE.md, lessons.md, README.md
- [x] Rust shell (main.rs, pybridge.rs)

## Phase 2: Core Protocols (DONE)
- [x] Adapter protocols (VideoModel, LLMDirector, Embedder, TTS, RefImg)
- [x] Registry with lazy instantiation + entry points
- [x] Pydantic models for all boundaries

## Phase 3: Data Layer (DONE)
- [x] SQLAlchemy 2.x models (Project, SourceDoc, Treatment, Shot, StylePack, RenderJob)
- [x] Alembic migration setup

## Phase 4: Adapters (DONE)
- [x] LiteLLMDirector
- [x] LocalEmbedder (BGE-small)
- [x] PiperTTS
- [x] FalFluxAdapter
- [x] VertexVeoAdapter
- [x] FalAdapter + manifest
- [x] Wan2GPAdapter + manifest
- [x] ComfyUIAdapter + workflow JSON

## Phase 5: Pipeline Modules (DONE)
- [x] Ingest (PDF/MD/URL/TXT)
- [x] Director treatment (Chain of Draft, JSON schema strict)
- [x] Director storyboard (capability-aware)
- [x] PromptForge (template, continuity bible, validators)
- [x] Generator pipeline (render orchestration)
- [x] Extend pipeline
- [x] Frame bridge
- [x] Stitcher (FFmpeg wrapper, timeline JSON)

## Phase 6: Token Ledger (DONE)
- [x] Routing config (3 profiles: cloud_premium, local_two_stage, hybrid)
- [x] Prompt cache
- [x] Semantic cache (cosine similarity)
- [x] Token counter + budget enforcement

## Phase 7: Prefabs (DONE)
- [x] 6 style packs
- [x] 4 shot grammars
- [x] 7 transitions

## Phase 8: UI (DONE)
- [x] SolidJS + Tailwind + Vite setup
- [x] API client (typed fetch wrapper)
- [x] Project store (reactive state)
- [x] ProjectTree component
- [x] Storyboard card grid
- [x] Inspector panel (tokens, sources, routing, budget, queue)
- [x] Command palette (Cmd+K)
- [x] SourceUploader (drag & drop)
- [x] TreatmentView
- [x] TimelineView
- [x] PreviewPlayer
- [x] Tab navigation in App.tsx

## Phase 9: Tests (DONE)
- [x] Unit: protocols, director, promptforge, stitcher, token_ledger, leaky_imports
- [x] Integration: adapter_swap, plugin_discovery, capability_honesty
- [x] E2E: full pipeline (Playwright scaffold)

## Phase 10: Definition of Done Verification
- [ ] Run mypy --strict on backend/
- [ ] Run pytest unit tests
- [ ] Run integration tests
- [ ] Verify no TODO comments in committed code
- [ ] Verify lessons.md is non-empty
- [ ] Package with Tauri bundler
