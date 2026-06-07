"""Frame bridge — uses last frame of shot N as first frame of shot N+1."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

from backend.adapters.protocols import VideoGenRequest, VideoModel, AspectRatio

logger = logging.getLogger(__name__)


class FrameBridge:
    """Handles frame-conditioned continuity between adjacent shots."""

    def __init__(self, adapter: VideoModel) -> None:
        self.adapter = adapter

    async def bridge(
        self, source_clip: Path, prompt: str, duration_sec: int, aspect_ratio: str, resolution: str
    ) -> Any:
        if not self.adapter.capabilities.supports_frame_conditioning:
            raise RuntimeError("Adapter does not support frame conditioning")

        # Extract last frame from source
        last_frame = self._extract_last_frame(source_clip)

        req = VideoGenRequest(
            prompt=prompt,
            duration_sec=duration_sec,
            aspect_ratio=cast(AspectRatio, aspect_ratio),
            resolution=resolution,
            first_frame=last_frame,
        )
        return await self.adapter.generate(req)

    def _extract_last_frame(self, clip: Path) -> Path:
        import subprocess

        out = clip.with_suffix(".last_frame.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(clip), "-vf", "scale=320:-1", "-vframes", "1", str(out)],
            capture_output=True,
            check=True,
        )
        return out
