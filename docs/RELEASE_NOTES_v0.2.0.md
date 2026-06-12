# CineForge v0.2.0 — Public Beta

Local-first desktop studio for document → cinematic video.

## Highlights

- Full pipeline: ingest → director → storyboard → PromptForge → multi-model render → stitch
- lookBOOK shot JSON import (no LLM required for pre-built storyboards)
- Hybrid routing: cloud hero shots (Veo/Kling) + local preview/b-roll (Wan2GP, ComfyUI)
- 96 automated tests; Playwright E2E for mocked pipeline

## Downloads

| Platform | Artifact |
|----------|----------|
| Windows | `.msi` from GitHub Releases |
| macOS | `.dmg` from GitHub Releases |
| Linux | `.AppImage` from GitHub Releases |

**Note:** Beta installers are unsigned. Windows may show "Unknown publisher"; macOS may require right-click → Open. Signed builds planned in Milestone 11.

## Quick start

1. Install from [GitHub Releases](https://github.com/lumenhelixsolutions/cineFORGE/releases)
2. Optional: `pip install -e ".[vertex,fal]"` for cloud adapters
3. See [QUICKSTART.md](./QUICKSTART.md)

## Portfolio integrations

- **lookBOOK:** export `analysis/shot_graph.json` → CineForge ingest API
- **NOTEtoolsLM:** `POST /api/vault/export` with `format: cineforge`

## Cloud adapters

See [CLOUD_ADAPTERS.md](./CLOUD_ADAPTERS.md) for API keys and Sora fallback routing.