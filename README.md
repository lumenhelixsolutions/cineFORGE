# cineFORGE

<p align="center">
  <a href="https://lumenhelix.com">
    <img src="docs/assets/lumenhelix-logo.svg" alt="LumenHelix Solutions" width="180">
  </a>
</p>

<h3 align="center">Turn documents into cinematic videos with full creative control</h3>

<p align="center">
  <a href="https://lumenhelixsolutions.github.io/cineFORGE/">
    <img src="https://img.shields.io/badge/Launch_Page-cineFORGE-00D4FF?style=flat-square&logo=githubpages&logoColor=white" alt="Launch Page">
  </a>
  <a href="https://lumenhelix.com">
    <img src="https://img.shields.io/badge/Built_by-LumenHelix-7C3AED?style=flat-square" alt="Built by LumenHelix">
  </a>
  <img src="https://img.shields.io/badge/license-MIT-8A95A8?style=flat-square" alt="License">
</p>

---

**cineFORGE** is part of the [LumenHelix Solutions](https://lumenhelix.com) portfolio — applied symbolic dynamics & reversible computation for deterministic, traceable AI systems.

cineFORGE is a local-first desktop application that turns source documents and outlines into coherent 30-second to 10-minute cinematic videos. It orchestrates an LLM director, multi-provider video adapters, and FFmpeg-based stitching so you control every seam: storyboard, style pack, per-shot prompt, transition, narration, and final cut.

## Why this exists

- **Own the pipeline.** From ingestion to final cut, every seam is editable and reversible.
- **Switch providers.** Use cloud quality, local privacy, or hybrid previews without rewriting workflows.
- **Stay local.** Projects live in SQLite + flat files — no required cloud, no lock-in.

## Quick start

Install and run cineFORGE in under two minutes.

### macOS / Linux

```bash
# Clone
git clone https://github.com/lumenhelixsolutions/cineFORGE.git
cd cineFORGE

# Install & run
# Create Python virtual environment
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e ".[vertex,fal,dev]"

# Install frontend dependencies
cd ui && npm install

# Start the desktop app
cd .. && cargo tauri dev
```

### Windows (PowerShell)

```powershell
# Clone
git clone https://github.com/lumenhelixsolutions/cineFORGE.git
Set-Location cineFORGE

# Install & run
# Create Python virtual environment
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -e ".[vertex,fal,dev]"

# Install frontend dependencies
cd ui
npm install

# Start the desktop app
cd ..
cargo tauri dev
```

### Windows (Git Bash / WSL)

```bash
git clone https://github.com/lumenhelixsolutions/cineFORGE.git
cd cineFORGE
# Create Python virtual environment
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e ".[vertex,fal,dev]"

# Install frontend dependencies
cd ui && npm install

# Start the desktop app
cd .. && cargo tauri dev
```

> **Device note:** cineFORGE is tested on Windows 11, macOS Sonoma, Ubuntu 22.04/24.04, and modern mobile browsers.

## Full documentation

Visit the launch page for architecture, API reference, and deployment guides:  
**https://lumenhelixsolutions.github.io/cineFORGE/**

## Features

| Feature | What it gives you |
|---------|-------------------|
| LLM Director | Auto-generate treatments, storyboards, per-shot prompts, and continuity bibles from any source document. |
| Multi-provider video | Route to Vertex Veo, fal.ai, Wan2GP, ComfyUI, Kling, Sora, and more from one capability-aware pipeline. |
| Local-first desktop | Tauri 2 shell + SolidJS UI + FastAPI backend keeps projects, media, and decisions on your machine. |
| Deterministic editing | MoviePy + FFmpeg stitching with routing profiles, transitions, narration, and versioned project bundles. |

## Architecture at a glance

```
cineFORGE/
├── backend/     Python 3.12 + FastAPI — adapters, director, stitcher
├── ui/          SolidJS + Tailwind — project editor and timeline
└── src-tauri/   Tauri 2.x (Rust) — desktop shell and system bridge
```

## Development

```bash
# Backend only
.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload

# Frontend only
cd ui && npm run dev

# Full Tauri desktop app
cargo tauri dev
```

## Roadmap

- [ ] ComfyUI node-editor integration for custom local workflows
- [ ] B-roll bulk generation via the MoneyPrinterTurbo bridge
- [ ] One-click export to MP4, ProRes, and versioned project bundles

## Support & consulting

Need deterministic AI systems with full traceability? LumenHelix builds reversible computation kernels, governance layers, and end-to-end AI integrations.

- **Website:** https://lumenhelix.com
- **Services:** AI diagnostics, B.Y.O. support packages, governance audits
- **Research:** TEN² kernel, R.U.B.I.C. boundary discipline, C.O.R.E. constraint lens

## License

Released under the MIT License. Style packs and shot grammars are CC-BY-4.0.

---

<p align="center">
  <sub>Engineered by <a href="https://lumenhelix.com">LumenHelix Solutions</a> — Applied Symbolic Dynamics & Reversible Computation.</sub>
</p>
