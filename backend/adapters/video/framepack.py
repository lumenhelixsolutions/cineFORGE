"""FramePack-F1 adapter — most VRAM-efficient text-to-video (6GB+).

FramePack uses next-frame prediction with compressed temporal context,
so generation cost is fixed per frame regardless of video length.
13B model runs 60s@30fps on 6GB VRAM. Apache-2.0 license.

Source: https://github.com/lllyasviel/FramePack
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

import httpx

from backend.adapters.protocols import (
    VideoModel, VideoCapabilities, VideoGenRequest, VideoGenResult,
    ExtendRequest, CapabilityError
)

logger = logging.getLogger(__name__)
FRAMEPACK_BASE = "http://localhost:7860"


class FramePackAdapter:
    """FramePack-F1 text-to-video adapter. Connects to local Gradio server."""

    def __init__(self, model_id: str = "framepack-f1-13b") -> None:
        self._model_id = model_id
        self.capabilities = VideoCapabilities(
            provider_id=f"framepack.{model_id}",
            display_name="FramePack F1",
            supported_durations_sec=[4, 6, 8, 10, 12, 16, 24, 32, 60],
            supported_aspect_ratios=["16:9", "9:16", "1:1", "4:3"],
            supported_resolutions=["480p", "720p"],
            max_reference_images=1,
            supports_native_audio=False,
            supports_frame_conditioning=True,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=True,
            is_local=True,
            cost_per_second_usd=0.0,
            notes="Most VRAM-efficient open T2V. 6GB VRAM for 60s@30fps. Requires localhost Gradio server.",
        )

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        if not await self.healthcheck():
            raise RuntimeError(f"FramePack server not reachable at {FRAMEPACK_BASE}")

        payload = {
            "prompt": req.prompt,
            "negative_prompt": req.negative_prompt or "",
            "width": 1280 if req.aspect_ratio == "16:9" else 720,
            "height": 720 if req.aspect_ratio == "16:9" else 1280,
            "total_second_length": req.duration_sec,
            "fps": 30,
            "gs": 7.5,
            "seed": req.seed if req.seed is not None else -1,
        }

        if req.reference_images:
            # FramePack supports single image conditioning
            payload["input_image"] = str(req.reference_images[0])

        async with httpx.AsyncClient(timeout=1800.0) as client:
            resp = await client.post(
                f"{FRAMEPACK_BASE}/api/predict",
                json={"fn_index": 0, "data": list(payload.values())},
            )
            resp.raise_for_status()
            data = resp.json()
            video_path = data.get("data", [{}])[0].get("name", "")
            if not video_path:
                raise RuntimeError("No video path in FramePack response")
            clip_path = Path(video_path)
            last_frame = self._extract_last_frame(clip_path)
            return VideoGenResult(
                clip_path=clip_path,
                last_frame_path=last_frame,
                duration_sec=float(req.duration_sec),
                has_audio=False,
                cost_usd=0.0,
                provider_id=self.capabilities.provider_id,
            )

    async def extend(self, req: ExtendRequest) -> VideoGenResult:
        raise CapabilityError("FramePack does not support native extend")

    async def healthcheck(self) -> bool:
        try:
            r = httpx.get(f"{FRAMEPACK_BASE}/info", timeout=5.0)
            return r.status_code == 200
        except Exception:
            return False

    def _extract_last_frame(self, clip_path: Path) -> Path:
        out = clip_path.with_suffix(".last_frame.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(clip_path),
             "-vf", "scale=320:-1", "-vframes", "1", str(out)],
            capture_output=True,
            check=True,
        )
        return out
