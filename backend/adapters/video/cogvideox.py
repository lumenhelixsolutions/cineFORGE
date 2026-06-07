"""CogVideoX-5B / 2B adapter — lightweight open text-to-video.

CogVideoX-2B: ~3.6GB VRAM (16-bit), short 720p clips
CogVideoX-5B: ~4.4GB VRAM (16-bit), better quality
License: 2B Apache-2.0, 5B non-commercial

Source: https://github.com/THUDM/CogVideo
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
COGVIDEO_BASE = "http://localhost:7860"


class CogVideoXAdapter:
    """CogVideoX text-to-video adapter."""

    def __init__(self, model_id: str = "cogvideox-5b") -> None:
        self._model_id = model_id
        is_2b = "2b" in model_id.lower()
        self.capabilities = VideoCapabilities(
            provider_id=f"cogvideo.{model_id}",
            display_name="CogVideoX 2B" if is_2b else "CogVideoX 5B",
            supported_durations_sec=[4, 6],
            supported_aspect_ratios=["16:9", "1:1"],
            supported_resolutions=["720p"],
            max_reference_images=0,
            supports_native_audio=False,
            supports_frame_conditioning=False,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=True,
            is_local=True,
            cost_per_second_usd=0.0,
            notes=f"Lightweight T2V. {'~3.6GB VRAM' if is_2b else '~4.4GB VRAM'} 16-bit. Short clips only.",
        )

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        if not await self.healthcheck():
            raise RuntimeError(f"CogVideoX server not reachable at {COGVIDEO_BASE}")

        payload = {
            "prompt": req.prompt,
            "num_frames": req.duration_sec * 8,  # ~8fps
            "height": 480,
            "width": 720,
            "guidance_scale": 6.0,
        }
        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt
        if req.seed is not None:
            payload["seed"] = req.seed

        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(f"{COGVIDEO_BASE}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            video_path = data.get("video_path")
            if not video_path:
                raise RuntimeError("No video_path in CogVideoX response")
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
        raise CapabilityError("CogVideoX does not support extend")

    async def healthcheck(self) -> bool:
        try:
            r = httpx.get(f"{COGVIDEO_BASE}/health", timeout=5.0)
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
