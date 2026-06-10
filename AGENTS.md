# CineForge — Agent Development Guide

## Project Overview

CineForge is a local-first desktop application that turns source documents (PDFs, Markdown, URLs) into long-form cinematic videos. It orchestrates video generation models (Veo, Kling, Sora, Wan2GP, ComfyUI), LLM directors, and FFmpeg-based stitching.

- **Shell**: Tauri 2.x (Rust)
- **Frontend**: SolidJS + Tailwind CSS
- **Backend**: Python 3.12 + FastAPI + SQLAlchemy (async SQLite)
- **Video**: Multi-adapter pipeline with capability-aware routing
- **Editing**: MoviePy 2.x + FFmpeg

## Optional UI integrations

| Tool | When | Doc |
|------|------|-----|
| assistant-ui | Chat/coach surfaces in React views | `D:\projects\docs\CHATBOT_STACK.md` |
| magic-mcp | Opt-in fast UI component generation | `D:\projects\docs\MAGIC_MCP.md` |

Not required for Tauri/SolidJS core. Enable per-developer in local MCP config.

## Build & Run

### Prerequisites
- Python 3.12+
- Node.js 20+
- Rust (for Tauri desktop builds)
- FFmpeg in PATH

### Install
```bash
make install
# or manually:
pip install -e ".[vertex,fal,dev]"
cd ui && npm install
```

### Dev Mode
```bash
# Backend only
make dev
# or
uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload

# Frontend only
cd ui && npm run dev

# Full Tauri desktop app
cargo tauri dev
```

### Build Release
```bash
# Tauri desktop bundles (MSI, DMG, AppImage)
cargo tauri build

# Python wheel
python -m build
```

## Testing

### Backend
```bash
# Unit tests
pytest tests/unit -v
make test

# Integration tests
pytest tests/integration -v
make test-integration

# End-to-end tests (requires Playwright + backend running)
pytest tests/e2e -v --browser chromium
make test-e2e

# Type checking
mypy backend/ --strict --ignore-missing-imports
make lint

# Linting
ruff check backend/ scripts/ docs/
ruff format --check backend/ scripts/ docs/
```

### Frontend
```bash
cd ui
npm run test        # vitest
npm run build       # production build + typecheck
```

### Diagnostics
```bash
# Backend health & system checks
curl http://127.0.0.1:8765/diagnostics

# Full preflight before render
python -c "from backend.preflight import run_all; ..."
```

## Code Conventions

### Python
- **Protocols before implementations.** Every external dependency is behind a Protocol in `backend/adapters/protocols.py`.
- **No concrete imports outside adapters.** Core code imports only from `protocols.py`.
- **Capability-aware planning.** The Director queries `VideoCapabilities` before writing storyboards.
- **Routing.yaml is the single source of truth.** No hard-coded provider selection.
- **Use timezone-aware UTC.** Replace `datetime.utcnow()` with `datetime.now(timezone.utc).replace(tzinfo=None)` for DB compatibility.
- Type hints required; `mypy --strict` must pass.
- No TODO comments in committed code. Use GitHub issues (see `OPEN_ISSUES.md`).

### TypeScript / SolidJS
- Use SolidJS reactivity primitives (`createSignal`, `createEffect`, `createMemo`).
- Avoid virtual DOM patterns — SolidJS compiles away the framework.
- Accessibility: every interactive element needs `aria-label` or visible text, focus-visible rings, and reduced-motion support.
- Tailwind utility classes; no custom CSS files except `index.css` for base layers.

### Git
- Write descriptive commit messages.
- Run tests before committing.
- Keep commits focused on a single concern.

## Architecture

```
backend/
  adapters/          # Protocols + provider implementations (video, LLM, TTS, embedder, refimg)
  director/          # Treatment + storyboard generation
  generator/         # Render pipeline + extend pipeline
  ingest/            # Document ingestion (PDF, MD, URL, TXT)
  models/            # SQLAlchemy models
  postprocess/       # LUT, upscaling, frame interpolation
  prefabs/           # Style packs, grammars, transitions
  promptforge/       # Prompt optimization + continuity bible
  stackbuilder/      # Intelligent profile recommendation
  stitcher/          # FFmpeg timeline assembly
  token_ledger/      # Semantic routing + cost tracking
  app.py             # FastAPI entry point
  auth.py            # Optional API-key middleware
  database.py        # Async session management
  diagnostics.py     # Built-in health checks
  preflight.py       # Render job pre-flight checks
  settings.py        # Pydantic settings + env config
  telemetry.py       # Opt-in session analytics
  bundle.py          # Project export/import (.cineforge ZIP)

ui/
  src/
    components/      # SolidJS components
    stores/          # Global state (projectStore, toastStore)
    lib/             # API client + helpers
    routes/          # Route definitions

src-tauri/
  src/               # Rust source (pybridge, main)
  Cargo.toml
  tauri.conf.json
```

## Subagent Boundaries

Decompose generously. One subagent per concern:
- **ingest** — document parsing, chunking, embedding
- **director** — treatment, storyboard, shot planning
- **promptforge** — prompt optimization, continuity, validators
- **generator** — render pipeline, extend, frame bridge
- **stitcher** — timeline assembly, transitions, audio sync
- **ledger** — routing, semantic search, cost tracking
- **UI** — components, stores, accessibility, visual polish

Each subagent owns its module and its tests.

## Verification Gates

Before marking any task done:
1. Run the relevant tests. If you didn't write any, that's your bug.
2. Diff the behavior change against the plan. If they don't match, the code is wrong.
3. Ask: "would a staff engineer approve this PR?" If no, fix it.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CINEFORGE_PORT` | `8765` | Backend HTTP port |
| `CINEFORGE_DATA_DIR` | `~/.cineforge` | Projects, DB, cache, prefabs |
| `CINEFORGE_MOCK_VIDEO` | `false` | Mock video adapters (testing) |
| `CINEFORGE_MOCK_LLM` | `false` | Mock LLM adapters (testing) |
| `CINEFORGE_TELEMETRY` | `0` | Write telemetry JSONL sessions |
| `CINEFORGE_API_KEY` | — | Optional API-key auth |

## Useful Commands

```bash
# Generate API docs HTML
python docs/export_docs.py

# Performance audit
python scripts/perf_audit.py

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Recovery script (Windows PowerShell)
.\cineforge-recovery.ps1
```

## What is Out of Scope

See `plans/` directory for active work. Do not invent features outside the current plan boundary. If a non-goal seems necessary, write the case in `plans/scope-change-<slug>.md` and stop.
