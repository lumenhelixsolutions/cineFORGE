# Cloud Adapter Validation & Fallbacks

Last reviewed: 2026-06-11

## Primary cloud adapters (beta validation target)

| Adapter | Provider ID | Env key | Status | Notes |
|---------|-------------|---------|--------|-------|
| Veo 3.1 | `vertex.veo-3.1` | `GOOGLE_APPLICATION_CREDENTIALS` | ✅ Primary hero | Default in `hybrid` routing profile |
| Veo 3.1 Fast | `vertex.veo-3.1-fast` | same | ✅ Standard tier | Lower latency variant |
| Kling 3.0 | `fal.kling-3` | `FAL_KEY` | ✅ Validate live | fal.ai hosted |
| Luma | `fal.luma-dream-machine` | `FAL_KEY` | ✅ Validate live | Image/text → video |
| Sora 2 | `openai.sora` | `OPENAI_API_KEY` | ⚠️ Uncertain | Consumer app shut down Mar 2026; platform API may still work |

## Sora fallback policy

When `openai.sora` is unavailable or returns errors:

1. **Hero shots** → `vertex.veo-3.1`
2. **Standard shots** → `vertex.veo-3.1-fast` or `fal.kling-3`
3. **B-roll** → `wan2gp.wan-2.2-14b-gguf` (local) or `fal.hailuo-02`

Configure in `routing.yaml` under the `hybrid` profile — Sora is never the only path.

## Validation checklist (manual, with live keys)

```powershell
cd D:\projects\cineforge
pytest tests/unit/test_adapters.py -q -k "mock"
# Live smoke (requires keys):
# 1. Create project → treatment → storyboard with routing_profile=cloud_premium
# 2. Render one 4s hero shot per adapter under test
# 3. Confirm clip_path written and duration matches capability envelope
```

| Step | Pass criteria |
|------|---------------|
| Veo hero render | MP4 exists, no 5xx from Vertex |
| Kling via fal | Job completes within adapter timeout |
| Luma via fal | Returns clip URL or local download |
| Sora attempt | On failure, router selects Veo/Kling without crash |

## Local adapters (no cloud keys)

| Adapter | Use case |
|---------|----------|
| `wan2gp.*` | Preview, b-roll, title cards |
| `comfyui.local` | Custom node workflows |
| `framepack.local` | Next-frame prediction |
| `cogvideox.local` | Short clips on 8GB VRAM |

## Related

- [PUBLIC_BETA_RELEASE.md](./PUBLIC_BETA_RELEASE.md)
- `backend/adapters/video/sora_adapter.py` — documents API uncertainty in module docstring