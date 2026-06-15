# CineForge Pipeline Overview

Timestamp: 2026-06-12T20:00:00Z
Schema: cineforge.pipeline-overview.v1
Version: 0.2.0
Milestone: M6 — lookBOOK ingest bridge

Document-to-video studio: sources → treatment → storyboard → render → stitch → export.

## Product Shape

| Layer | Stack | Role |
|-------|-------|------|
| Desktop shell | Tauri 2.x (Rust) | Native app, file access, bundling |
| Frontend | SolidJS + Tailwind (`ui/`) | Project UI, storyboard, render controls |
| Backend | FastAPI + SQLAlchemy (`backend/`) | API, job orchestration, SQLite persistence |
| Video | Multi-adapter pipeline + FFmpeg | Veo, Kling, Fal, ComfyUI, MoviePy stitch |

Two entry paths share the same downstream render pipeline:
1. **Document path** — upload source → LLM treatment → storyboard → render
2. **lookBOOK path** — ingest `lookbook.shot_graph.v0.3` → treatment stub → shots (no LLM for structure)

## Module Ownership

| Module | Path | Owns |
|--------|------|------|
| API surface | `backend/app.py` | Routes, project lifecycle, render orchestration |
| lookBOOK ingest | `backend/ingest/lookbook.py` | Schema parse, shot mapping, treatment stub |
| Capabilities | `backend/capabilities/` | Provider detection, routing profiles |
| Adapters | `backend/adapters/` | Per-provider video generation |
| Database | `backend/database.py`, `alembic/` | Projects, shots, scenes, exports |
| UI | `ui/src/` | SolidJS views, Playwright e2e |
| Landing | `landing/` | Public beta page (GitHub Pages) |

## Pipeline Stages

| Stage | Endpoint / command | Input → Output | Status |
|-------|-------------------|----------------|--------|
| 1. Bootstrap | `POST /projects` | name + aspect → project record | production |
| 2. Sources | `POST /projects/{id}/sources` | PDF/MD/URL → parsed source | production |
| 3. Treatment | `POST /projects/{id}/treatment` | source → treatment JSON (LLM) | production |
| 4. lookBOOK ingest | `POST /projects/{id}/ingest/lookbook` | shot graph → treatment + shots | production (M6) |
| 5. Storyboard | `POST /projects/{id}/storyboard` | treatment → scene/shot plan | production |
| 6. Prompt forge | `POST /projects/{id}/prompts/forge` | shots → provider prompts | production |
| 7. Render | `POST /projects/{id}/render` | draft shots → generated clips | production |
| 8. B-roll | `POST /api/scenes/{id}/generate-broll` | scene → supplemental clips | production |
| 9. Stitch | `POST /projects/{id}/stitch` | clips → assembled timeline | production |
| 10. Narration | `POST /projects/{id}/narration` | script → TTS audio | production |
| 11. Export | `POST /api/projects/{id}/export` | timeline → deliverable file | production |
| 12. Trailer | `POST /api/projects/{id}/generate-trailer` | project → short preview | beta |

## Data Flow

```
Document path:
  sources → treatment (LLM) → storyboard → prompts → render → stitch → export

lookBOOK path (M6):
  shot_graph.json ──POST /ingest/lookbook──► treatment stub + shots ──► render → stitch → export
```

**lookBOOK contract:** accepts `lookbook.shot_graph.v0.3` via `backend/ingest/lookbook.py`.
Maps lookBOOK shots to CineForge shot records; `llm_model` tagged `lookbook.import`.

**Upstream file handoff:** lookBOOK writes `exports/cineforge/ingest.json`; operator POSTs body or uses `lookbook export-cineforge --push`.

## CLI / API Entry Points

**Dev backend:** `uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload` (or `make dev`)

**Dev UI:** `cd ui && npm run dev`

**Desktop:** `cargo tauri dev` / `cargo tauri build`

**Key ingest:**
```bash
curl -X POST http://127.0.0.1:8765/projects/{id}/ingest/lookbook \
  -H "Content-Type: application/json" \
  -d @exports/cineforge/ingest.json
```

## Setup / Run / Test Paths

| Action | Command |
|--------|---------|
| Install | `make install` |
| Unit tests | `pytest tests/unit -v` (96+ pass) |
| lookBOOK ingest tests | `pytest tests/unit/test_lookbook_ingest.py -v` |
| Integration | `pytest tests/integration -v` |
| E2E | `pytest tests/e2e -v` (Playwright + running backend) |
| Lint | `make lint` |

## Capability Gaps

- GitHub Release artifacts: tag `v0.2.0` drafted; unsigned beta OK
- Pages deploy at cineforge.app: DNS + Pages enable pending
- Live Kling/Luma API smoke: unverified in CI
- llama.cpp local script assist: optional, not wired (portfolio ⚠️)
- LangGraph multi-step orchestration: Phase 4 deferred

## Last Verified End-to-End Run

- **Unit:** `tests/unit/test_lookbook_ingest.py` — parse, convert, treatment stub
- **API:** `POST /projects/{id}/ingest/lookbook` documented in `docs/API.md`
- **Unverified:** Full lookBOOK export → CineForge render → stitch in one portfolio script

## Do Not Break

- `backend/ingest/lookbook.py` — shared schema with lookBOOK `ShotGraph`
- Shot/treatment persistence after ingest (`replace_existing_shots` flag)
- Capability-aware render routing in `backend/capabilities/`