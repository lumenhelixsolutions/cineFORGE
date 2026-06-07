# CineForge Hybrid Prefab Setups

Based on research into the current state of local video AI (FramePack, CogVideoX, RIFE, Real-ESRGAN), these are the recommended hybrid configurations for different hardware and budget constraints.

## Quick Comparison

| Profile | GPU VRAM | Cost/Min | Best For | LLM | Video | Post-Process |
|---------|----------|----------|----------|-----|-------|--------------|
| **cloud_premium** | None (cloud) | ~$8–12 | Production quality, fast turnaround | Claude Sonnet | Veo 3.1 | Native |
| **hybrid** | 6GB+ | ~$3–5 | Cost-conscious with local previews | Claude Sonnet | Veo finals + Wan2GP previews | None |
| **framepack_hybrid** | 6GB+ | ~$2–4 | **Long-form video on limited hardware** | Claude Sonnet | FramePack F1 | RIFE + Real-ESRGAN |
| **cogvideo_hybrid** | 4GB+ | ~$2–3 | **Ultra-lightweight, laptop GPUs** | Claude Sonnet | CogVideoX 5B | RIFE |
| **local_two_stage** | 8GB+ | $0 | Full local, no API keys | Ollama | Wan2GP | None |
| **budget_local** | 6GB+ | $0 | **100% free, maximum quality/VRAM ratio** | Ollama | FramePack + CogVideoX | RIFE + Real-ESRGAN |

---

## Profile 1: `framepack_hybrid` — Long-Form on 6GB

**Thesis:** FramePack-F1 is the only open model that generates 60-second clips on 6GB VRAM. Pair it with cloud LLM for treatment quality, then post-process with RIFE (smooth motion) and Real-ESRGAN (upscale to 1080p).

**Hardware:** NVIDIA RTX 3060/4060 (6–8GB) or better. CPU-only will not work for video generation.

**Install:**
```bash
# 1. Install FramePack
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
git clone https://github.com/lllyasviel/FramePack.git
cd FramePack
pip install -r requirements.txt
python demo_gradio.py  # Runs on localhost:7860

# 2. Install RIFE (optional but recommended)
pip install vsrife
python -m vsrife  # Downloads models

# 3. Install Real-ESRGAN (optional)
pip install realesrgan

# 4. Install CineForge with local deps
pip install -e ".[local]"
```

**`.env`:**
```env
ANTHROPIC_API_KEY=sk-ant-...
LITELLM_PROVIDER=anthropic/claude-sonnet-4-6
CINEFORGE_PORT=8765
```

**Routing:** Select `framepack_hybrid` in UI.

**Pipeline flow:**
1. **Treatment/Storyboard:** Claude Sonnet (cloud, ~$0.50)
2. **Preview:** FramePack F1 13B at 480p (local, free, ~8 min for 60s clip on RTX 3060)
3. **Hero shots:** FramePack F1 13B at 720p (local, free, ~15 min for 60s clip)
4. **B-roll:** CogVideoX-2B for quick fill (local, free, ~2 min for 6s clip)
5. **Post-process:** RIFE 2x interpolation → Real-ESRGAN x2 upscale (local, free, ~1 min per clip)

**Style pack:** `framepack_cinematic`
**Grammar:** `framepack_longform`

**Expected output:** 3–5 minute cinematic video, 720p→1080p via SR, 30fps native + 60fps interpolated, total cost ~$2–4 in LLM tokens.

---

## Profile 2: `cogvideo_hybrid` — Laptop GPU (4GB)

**Thesis:** CogVideoX-5B runs on ~4.4GB VRAM. It only produces 4–6 second clips, but with RIFE interpolation and cloud LLM direction, you can assemble compelling short-form content on a laptop GPU.

**Hardware:** NVIDIA GTX 1650/RTX 3050 laptop (4GB) or better. RTX 3060 laptop (6GB) recommended.

**Install:**
```bash
# 1. Install CogVideoX
git clone https://github.com/THUDM/CogVideo.git
cd CogVideo
pip install -r requirements.txt
# Start inference server on localhost:7860
```

**`.env`:**
```env
ANTHROPIC_API_KEY=sk-ant-...
LITELLM_PROVIDER=anthropic/claude-sonnet-4-6
CINEFORGE_PORT=8765
```

**Routing:** Select `cogvideo_hybrid` in UI.

**Pipeline flow:**
1. **Treatment/Storyboard:** Claude Sonnet (cloud)
2. **All shots:** CogVideoX-5B at 720p, 6s max per shot (local)
3. **Post-process:** RIFE 2x interpolation to smooth the short clips
4. **Assembly:** Hard cuts between 6s segments (CogVideoX has no frame conditioning)

**Style pack:** `low_vram_documentary`
**Grammar:** `cogvideo_shortform`

**Expected output:** 30–60 second video, 720p at 60fps (interpolated), composed of 6s micro-shots. Total cost ~$2–3 in LLM tokens.

---

## Profile 3: `budget_local` — 100% Free, Zero API Keys

**Thesis:** Ollama for LLM + FramePack/CogVideoX for video + RIFE + Real-ESRGAN + Piper TTS + BGE-small embedder. Not a single API call. Runs entirely on your hardware.

**Hardware:** NVIDIA RTX 3060 (12GB) ideal. RTX 4060 laptop (8GB) works with CogVideoX primarily. CPU-only possible for LLM only (video requires GPU).

**Install:**
```bash
# 1. Install Ollama (from ollama.com)
ollama pull qwen3:32b
ollama pull qwen3:7b

# 2. Install FramePack (see framepack_hybrid section)
# 3. Install CogVideoX (see cogvideo_hybrid section)
# 4. Install RIFE
pip install vsrife
# 5. Install Real-ESRGAN
pip install realesrgan
# 6. Install Piper TTS (download binary from GitHub releases)
# 7. Install CineForge
pip install -e ".[local]"
```

**`.env`:**
```env
# No API keys. Zero cloud dependencies.
LITELLM_PROVIDER=ollama/qwen3:32b
CINEFORGE_PORT=8765
CINEFORGE_DATA_DIR=~/.cineforge
```

**Routing:** Select `budget_local` in UI.

**Pipeline flow:**
1. **Treatment/Storyboard:** Qwen3-32B via Ollama (local, free, ~2–5 min for treatment)
2. **Preview:** CogVideoX-2B (fastest, ~1 min per 6s clip)
3. **Hero shots:** FramePack F1 13B (best quality, ~15 min per 60s clip)
4. **Standard/B-roll:** CogVideoX-5B (balanced, ~3 min per 6s clip)
5. **Post-process:** RIFE 2x + Real-ESRGAN x2
6. **TTS:** Piper (CPU, free)
7. **Ref Images:** Local Diffusers / SDXL (auto-downloads on first use)

**Style pack:** `framepack_cinematic` or `low_vram_documentary`
**Grammar:** `framepack_longform` or `post_process_pipeline`

**Expected output:** Full cinematic video, 100% free. Tradeoff: slower generation (hours vs. minutes). But zero cost and full privacy.

---

## Profile 4: `hybrid` — Original Cost-Conscious Default

**Thesis:** Use local previews (Wan2GP LTX-Video) for iteration, then promote winners to cloud (Veo 3.1) for final quality. This is the original v0.1 default and remains the best balance of speed and quality if you have API budget.

**Hardware:** 6GB+ GPU for previews. No GPU needed for finals (cloud).

**`.env`:**
```env
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
CINEFORGE_PORT=8765
```

**Routing:** Select `hybrid` in UI.

**Pipeline flow:**
1. **Preview mode ON:** All shots → Wan2GP LTX-Video (local, free, ~30 sec per clip)
2. **Iterate:** Review storyboard flow, edit prompts
3. **Preview mode OFF:** Hero shots → Veo 3.1 (cloud, ~$0.05/sec). Standard → Veo 3.1 Fast. B-roll → Wan2GP.

**Expected output:** Fast iteration + best-in-class final quality. Cost ~$3–5 per 60s video.

---

## Post-Processing Explained

### RIFE Frame Interpolation
- **What it does:** Doubles (or triples) frame rate by synthesizing intermediate frames
- **VRAM:** ~0.5GB
- **Speed:** Real-time on RTX 3060
- **Best for:** Smoothing motion in action sequences, making 30fps source feel like 60fps
- **Limitation:** Struggles with extreme motion blur or scene cuts

### Real-ESRGAN Super-Resolution
- **What it does:** Upscales frames 2x or 4x using AI restoration
- **VRAM:** 2–4GB depending on input size and tile settings
- **Speed:** ~15–30fps for 1080p→4K on RTX 3080
- **Best for:** Taking 480p/720p local model output to 1080p/4K delivery
- **Limitation:** Amplifies noise/grain; source should be clean

### When to use post-processing
| Scenario | Use RIFE? | Use Real-ESRGAN? |
|----------|-----------|------------------|
| Action/motion shots | Yes | Optional |
| Static talking head | No | Yes (if upscaling) |
| Text/diagram shots | No | Yes (preserves sharpness) |
| Already 1080p source | Optional | No |

---

## Model License Summary

| Model | License | Commercial Use |
|-------|---------|----------------|
| FramePack-F1 | Apache-2.0 | Yes |
| CogVideoX-2B | Apache-2.0 | Yes |
| CogVideoX-5B | Non-commercial | No |
| RIFE (vsrife) | MIT | Yes |
| Real-ESRGAN | MIT | Yes |
| BasicVSR++ | Apache-2.0 | Yes |
| Wan2GP | Various (model-dependent) | Check model |
| Veo 3.1 | Google Cloud Terms | Yes (paid) |

**Note:** CogVideoX-5B is non-commercial. If you need commercial use with 4GB-class hardware, use CogVideoX-2B or FramePack-F1 instead.

---

## Performance Cheat Sheet

| GPU | Profile | 60s Video Time | Cost |
|-----|---------|-----------------|------|
| RTX 4090 (24GB) | framepack_hybrid | ~20 min | ~$2 |
| RTX 4060 (8GB) | cogvideo_hybrid | ~45 min | ~$2 |
| RTX 3060 (12GB) | budget_local | ~2 hrs | $0 |
| RTX 3060 (6GB) | framepack_hybrid | ~3 hrs | ~$2 |
| No GPU | cloud_premium | ~5 min | ~$10 |
| CPU only | N/A (video impossible) | — | — |

---

## Switching Profiles

In the CineForge UI:
1. Open project settings (top-right)
2. Select **Routing Profile** dropdown
3. Choose profile
4. Click **Apply**

The Director automatically re-evaluates bridge strategies against the new capabilities. Shots with changed requirements show a "Re-render needed" badge.

Or edit `~/.cineforge/routing.yaml` directly and click **Reload** in the UI.
