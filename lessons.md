# CineForge Build Lessons

`YYYY-MM-DD | rule | because <one-sentence rationale>`

2026-05-17 | Protocols before implementations | because concrete adapters rot fast; the abstraction boundary is the only stable surface.
2026-05-17 | SQLite WAL mode for single-file projects | because it eliminates write-lock contention between the FastAPI worker and any external reader.
2026-05-17 | FFmpeg wrapper module, never shell=True | because subprocess injection is a silent security failure and typed wrappers are self-documenting.
2026-05-17 | Routing.yaml is the single source of truth | because hard-coded provider selection becomes technical debt the moment a new model ships.
2026-05-17 | Chain of Draft beats Chain of Thought at 7.6% tokens | because token cost is a first-class constraint for local-first apps.
2026-05-17 | Every adapter declares capabilities in code, not docs | because the UI must query capabilities at startup to avoid silent failures.
2026-05-17 | Preview mode is not a feature, it is a workflow | because iterating on LTX-Video before promoting to Veo 3.1 is the only sane cost model.

2026-05-18 | FramePack-F1 is the only 6GB-viable long-form T2V | because next-frame prediction with compressed temporal context fixes the VRAM-scaling problem of standard diffusion.
2026-05-18 | CogVideoX-5B is non-commercial | because Zhipu AI restricted the 5B license; use 2B or FramePack for commercial work.
2026-05-18 | Post-processing (RIFE + Real-ESRGAN) is a force multiplier | because local models output at lower res/FPS, and lightweight post-processors can restore quality without cloud cost.
2026-05-18 | Routing profiles must expose post_interpolate and post_upscale | because the pipeline should treat RIFE/SR as composable stages, not separate adapters the user manually invokes.
2026-05-18 | Ollama Qwen3-32B matches Claude Sonnet on treatment tasks | because structured output with Chain of Draft constrains the model enough that open-weights perform comparably.
