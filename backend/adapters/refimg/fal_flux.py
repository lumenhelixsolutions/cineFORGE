"""Fal.ai FLUX reference image generator adapter."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

from backend.adapters.protocols import ReferenceImageGenerator

logger = logging.getLogger(__name__)


class FalFluxAdapter:
    """Generate reference images via fal.ai FLUX endpoint."""

    def __init__(self) -> None:
        self.provider_id = "fal.flux"
        self.is_local = False
        self._api_key = os.getenv("FAL_KEY", "")
        self._base_url = "https://queue.fal.run"

    async def generate(self, prompt: str, refs: list[Path] = []) -> Path:
        if not self._api_key:
            raise RuntimeError("FAL_KEY environment variable not set")

        headers = {"Authorization": f"Key {self._api_key}", "Content-Type": "application/json"}
        payload = {
            "prompt": prompt,
            "image_size": "landscape_4_3",
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/fal-ai/flux/dev",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            image_url = data.get("images", [{}])[0].get("url")
            if not image_url:
                raise RuntimeError("No image URL in fal response")

            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            out_path = Path("/tmp") / f"fal_flux_{os.urandom(4).hex()}.png"
            out_path.write_bytes(img_resp.content)
            return out_path
