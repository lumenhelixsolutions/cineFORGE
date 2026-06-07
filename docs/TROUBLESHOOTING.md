# Troubleshooting

## Backend won't start

**Symptom:** `python -m backend.app` crashes immediately.

- Check Python version: must be 3.12+
- Ensure `.env` exists or required env vars are set
- Run diagnostics: `GET /diagnostics` or check `cineforge-recovery.ps1`

## No adapters loaded

**Symptom:** `GET /capabilities` returns empty sections.

- Install the package in editable mode: `pip install -e ".[vertex,fal,dev]"`
- Verify entry points: `python -c "from backend.adapters.registry import get_registry; print(get_registry().all_capabilities())"`

## Render fails with "507 Insufficient Storage"

**Symptom:** Preflight error during render.

- Check disk space in `~/.cineforge/projects/`
- Ensure FFmpeg is in PATH
- Verify GPU drivers if using local adapters

## UI shows "Connection refused"

**Symptom:** Frontend cannot reach backend.

- Confirm backend is running on port 8765 (or your `CINEFORGE_PORT`)
- Check CORS headers: `GET /health` should include `Access-Control-Allow-Origin: *`
- Disable VPN or proxy that may block localhost

## Slow storyboard generation

**Symptom:** Treatment or storyboard takes >5 minutes.

- Use mock mode for testing: `CINEFORGE_MOCK_LLM=true`
- Switch to a faster LLM profile via StackBuilder
- Check internet connection for cloud providers

## High token usage / cost

**Symptom:** Budget exceeded unexpectedly.

- Enable preview mode on the project to generate cheaper drafts
- Review token usage in `GET /projects/{id}` response
- Use StackBuilder to find a cost-optimized profile

## Import bundle fails

**Symptom:** `POST /projects/import-bundle` returns 400.

- Ensure the file has `.cineforge` extension
- Verify the bundle contains `manifest.json`
- Check schema version matches current app version

## Telemetry not writing

**Symptom:** No session files in `~/.cineforge/telemetry/`.

- Telemetry is opt-in: set `CINEFORGE_TELEMETRY=1`
- Ensure `~/.cineforge` directory is writable
