# CineForge

[![CI](https://github.com/lumenhelixsolutions/cineFORGE/actions/workflows/ci.yml/badge.svg)](https://github.com/lumenhelixsolutions/cineFORGE/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/lumenhelixsolutions/cineFORGE?include_prereleases&label=release)](https://github.com/lumenhelixsolutions/cineFORGE/releases)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Turn source documents or outlines into long-form cinematic videos. Own every seam: storyboard, style pack, per-shot prompt, transition, narration, and final cut.

## What it is

CineForge is a local-first desktop application that orchestrates Google Veo 3.1, an LLM director, and FFmpeg-based stitching to produce coherent 30-second to 10-minute cinematic videos from PDFs, Markdown, URLs, or hand-written treatments.

Think NotebookLM's Cinematic Video Overview, but you control every frame.

## Features

- **B-Roll Generation** — Auto-generate supplementary stock-footage clips for any shot via the MoneyPrinterTurbo bridge. Clips are tracked per-shot, support pagination, and can be downloaded individually or bulk-generated across an entire project.

## Architecture

- **Shell**: Tauri 2.x (Rust) — ~10 MB binary, native file dialogs, system tray
- **Frontend**: SolidJS + Tailwind — fine-grained reactivity, no virtual DOM overhead
- **Backend**: Python 3.12 + FastAPI — async-native, best-in-class video + LLM ecosystem
- **Video**: Veo 3.1 (cloud), Wan 2.2 / LTX-Video / HunyuanVideo (local), ComfyUI (maximalist local)
- **LLM**: LiteLLM gateway — one interface, ~100 providers, prompt caching + structured output
- **Editing**: MoviePy 2.x + FFmpeg (system binary) — scriptable, no licensing trap
- **Storage**: SQLite (WAL mode) + flat-file media — single-file project, zero server

## Quick start

```bash
# Install the backend
pip install -e ".[vertex,fal]"

# Install the frontend
cd ui && npm install

# Dev mode — Tauri launches the Python backend automatically
cd .. && cargo tauri dev

# Build release
cargo tauri build
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for the full step-by-step guide, including API usage.

## MoneyPrinterTurbo Integration

CineForge embeds [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) as a submodule under `tools/moneyprinter/` for short-form / stock-footage video generation.

### One-command setup

```bash
# Unix / macOS
./scripts/init-moneyprinter.sh

# Windows
scripts\init-moneyprinter.bat
```

### Configuration

Project-specific defaults live in `config/moneyprinter.toml`. Copy or symlink it to `tools/moneyprinter/config.toml` to activate.

### Using the bridge

```python
from tools.shared.mpt_bridge import get_bridge

bridge = get_bridge()
task = bridge.start_task(video_subject="A cinematic mountain sunrise")
print(task["task_id"])
```

Start the MPT API server locally:

```bash
cd tools/moneyprinter && python main.py
```

## Testing

```bash
# Backend unit + integration
pytest tests/unit tests/integration -q

# Frontend
npm run test --prefix ui

# Type check
mypy backend/ --strict --ignore-missing-imports

# Lint
ruff check backend/ scripts/ docs/
```

## Provider matrix (v0.1)

| Provider | Type | Models | Native audio | Frame conditioning | Extend |
|----------|------|--------|-------------|-------------------|--------|
| Google Vertex AI | Cloud | Veo 3.1, Veo 3.1 Fast, Veo 3 | Yes | First + last | Yes (to 148s) |
| fal.ai | Cloud aggregator | Veo 3.1, Sora 2, Kling 2.5, Hailuo 02, Runway Gen-4, etc. | Varies | Varies | Varies |
| Wan2GP (localhost) | Local, low-VRAM | Wan 2.2 (1.3B / 14B GGUF), HunyuanVideo 1.5, LTX-Video 2.3 | No (LTX-2 yes) | Partial | No |
| ComfyUI (localhost) | Local, maximalist | Any workflow JSON | Varies | Varies | Varies |

## Routing profiles

Ships with three named profiles in `routing.yaml`:

- **cloud_premium** — best quality, paid
- **local_two_stage** — fully local, recommended low-VRAM workflow
- **hybrid** — local previews, cloud finals (cost-conscious default)

Switch profiles without restarting. The Director re-evaluates bridge strategies against new capabilities automatically.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and architecture principles.  
Agent contributors should read [AGENTS.md](AGENTS.md) for build steps, test commands, and conventions.

## License

MIT. See [THIRD_PARTY.md](THIRD_PARTY.md) for dependency licenses.

Style packs and shot grammars are CC-BY-4.0.

## Credits

- Veo team (Google) for the video generation model
- Anthropic for Claude
- MoviePy (MIT), FFmpeg (LGPL), Tauri (MIT/Apache-2.0), SolidJS (MIT)
