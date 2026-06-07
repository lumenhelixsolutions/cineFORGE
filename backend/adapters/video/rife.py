"""RIFE frame interpolation adapter — doubles/triples FPS post-render.

Runs on ~0.5-1GB VRAM. Real-time on RTX. MIT license.
Install: pip install vsrife

This is a post-processing adapter, not a primary VideoModel.
It consumes rendered clips and outputs higher-FPS versions.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from backend.adapters.protocols import (
    VideoCapabilities,
    VideoGenRequest,
    VideoGenResult,
    ExtendRequest,
    CapabilityError,
)

logger = logging.getLogger(__name__)


class RIFEAdapter:
    """RIFE frame interpolation — post-processes clips to higher FPS."""

    def __init__(self, factor: int = 2) -> None:
        self._factor = factor
        self.capabilities = VideoCapabilities(
            provider_id="rife.local",
            display_name=f"RIFE {factor}x Interpolation",
            supported_durations_sec=[4, 6, 8, 10, 12, 16, 24, 32, 60],
            supported_aspect_ratios=["16:9", "9:16", "1:1", "4:3"],
            supported_resolutions=["480p", "720p", "1080p"],
            max_reference_images=0,
            supports_native_audio=False,
            supports_frame_conditioning=False,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=False,
            is_local=True,
            cost_per_second_usd=0.0,
            notes=f"Post-process: {factor}x frame interpolation. Requires vsrife. ~0.5GB VRAM.",
        )

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        """Interpolate an existing clip. req.prompt is treated as the input clip path."""
        input_clip = Path(req.prompt)
        if not input_clip.exists():
            raise RuntimeError(f"Input clip not found: {input_clip}")

        out = input_clip.with_suffix(f".rife{self._factor}x.mp4")
        try:
            from vsrife import rife

            rife(str(input_clip), output=str(out), factor=self._factor)
        except ImportError:
            # Fallback to ffmpeg minterpolate if vsrife not installed
            logger.warning("vsrife not installed, falling back to ffmpeg minterpolate")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(input_clip),
                    "-vf",
                    f"minterpolate='mi_mode=mci:mc_mode=aobmc:me_mode=bidir:fps={30 * self._factor}'",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    str(out),
                ],
                capture_output=True,
                check=True,
            )

        last_frame = self._extract_last_frame(out)
        return VideoGenResult(
            clip_path=out,
            last_frame_path=last_frame,
            duration_sec=float(req.duration_sec),
            has_audio=False,
            cost_usd=0.0,
            provider_id=self.capabilities.provider_id,
        )

    async def extend(self, req: ExtendRequest) -> VideoGenResult:
        raise CapabilityError("RIFE does not support extend")

    async def healthcheck(self) -> bool:
        import importlib.util

        return importlib.util.find_spec("vsrife") is not None

    def _extract_last_frame(self, clip_path: Path) -> Path:
        out = clip_path.with_suffix(".last_frame.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(clip_path), "-vf", "scale=320:-1", "-vframes", "1", str(out)],
            capture_output=True,
            check=True,
        )
        return out
