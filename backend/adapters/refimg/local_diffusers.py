"""Local reference image generator using diffusers (Stable Diffusion / FLUX).

Zero API keys. Runs on CPU (slow) or CUDA (fast). Uses diffusers + torch.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.adapters.protocols import ReferenceImageGenerator

logger = logging.getLogger(__name__)


class LocalDiffusersAdapter:
    """Generate reference images locally via diffusers pipeline.

    Default model: stabilityai/stable-diffusion-xl-base-1.0 (4.3GB)
    Lightweight option: runwayml/stable-diffusion-v1-5 (2.3GB)
    Best quality local: black-forest-labs/FLUX.1-schnell (23GB, needs 16GB+ VRAM)
    """

    def __init__(self, model_id: str = "stabilityai/stable-diffusion-xl-base-1.0") -> None:
        self.provider_id = "local.diffusers"
        self.is_local = True
        self._model_id = model_id
        self._pipe: Any | None = None
        self._device = "cpu"

    def _load(self) -> Any:
        if self._pipe is not None:
            return self._pipe
        try:
            import torch
            from diffusers import StableDiffusionXLPipeline, DiffusionPipeline
            logger.info("Loading local diffusers model: %s", self._model_id)
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            if "xl" in self._model_id.lower():
                self._pipe = StableDiffusionXLPipeline.from_pretrained(
                    self._model_id,
                    torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
                    use_safetensors=True,
                )
            else:
                self._pipe = DiffusionPipeline.from_pretrained(
                    self._model_id,
                    torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
                    use_safetensors=True,
                )
            self._pipe = self._pipe.to(self._device)
            logger.info("Loaded on %s", self._device)
            return self._pipe
        except ImportError:
            raise RuntimeError(
                "diffusers and torch required for local reference image generation. "
                "Install: pip install diffusers torch accelerate"
            )

    async def generate(self, prompt: str, refs: list[Path] = []) -> Path:
        pipe = self._load()
        import torch
        generator = torch.Generator(self._device).manual_seed(42)
        image = pipe(
            prompt=prompt,
            num_inference_steps=20 if self._device == "cuda" else 50,
            guidance_scale=7.5,
            generator=generator,
        ).images[0]
        out = Path.home() / ".cineforge" / "cache" / f"refimg_{hash(prompt) % 100000:05d}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        image.save(out)
        logger.info("Saved reference image: %s", out)
        return out
