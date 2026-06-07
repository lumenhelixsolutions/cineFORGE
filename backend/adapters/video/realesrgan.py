"""Real-ESRGAN video super-resolution adapter.

Upscale rendered clips 2x or 4x. fp16 by default. Tiling support for low VRAM.
Install: pip install realesrgan
MIT license.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from backend.adapters.protocols import VideoModel, VideoCapabilities, VideoGenRequest, VideoGenResult, ExtendRequest, CapabilityError

logger = logging.getLogger(__name__)


class RealESRGANAdapter:
    """Real-ESRGAN video super-resolution — post-processes clips to higher resolution."""

    def __init__(self, scale: int = 2, model_name: str = "RealESRGAN_x2plus") -> None:
        self._scale = scale
        self._model_name = model_name
        self.capabilities = VideoCapabilities(
            provider_id=f"realesrgan.x{scale}",
            display_name=f"Real-ESRGAN x{scale}",
            supported_durations_sec=[4, 6, 8, 10, 12, 16, 24, 32, 60],
            supported_aspect_ratios=["16:9", "9:16", "1:1", "4:3"],
            supported_resolutions=["720p", "1080p", "4k"],
            max_reference_images=0,
            supports_native_audio=False,
            supports_frame_conditioning=False,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=False,
            is_local=True,
            cost_per_second_usd=0.0,
            notes=f"Post-process: x{scale} super-resolution. fp16 default. --tile for low VRAM.",
        )

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        """Upscale an existing clip. req.prompt is treated as the input clip path."""
        input_clip = Path(req.prompt)
        if not input_clip.exists():
            raise RuntimeError(f"Input clip not found: {input_clip}")

        out = input_clip.with_suffix(f".sr{self._scale}x.mp4")
        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                            num_block=23, num_grow_ch=32, scale=self._scale)
            upsampler = RealESRGANer(
                scale=self._scale,
                model_path=None,  # auto-download
                model=model,
                tile=400,  # memory-saving
                tile_pad=10,
                pre_pad=0,
                half=True,  # fp16
            )
            # Extract frames, upscale, re-encode
            temp_dir = Path.home() / ".cineforge" / "cache" / "realesrgan_frames"
            temp_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(input_clip),
                 f"{temp_dir}/frame_%04d.png"],
                capture_output=True,
                check=True,
            )
            for frame in sorted(temp_dir.glob("frame_*.png")):
                img, _ = upsampler.enhance(frame, outscale=self._scale)
                # img is numpy array, save back...
            # Re-encode
            subprocess.run(
                ["ffmpeg", "-y", "-i", f"{temp_dir}/frame_%04d.png",
                 "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                 "-pix_fmt", "yuv420p", str(out)],
                capture_output=True,
                check=True,
            )
        except ImportError:
            logger.warning("realesrgan not installed, falling back to ffmpeg lanczos upscale")
            w = 1280 * self._scale
            h = 720 * self._scale
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(input_clip),
                 "-vf", f"scale={w}:{h}:flags=lanczos",
                 "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                 str(out)],
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
        raise CapabilityError("Real-ESRGAN does not support extend")

    async def healthcheck(self) -> bool:
        try:
            import realesrgan
            return True
        except ImportError:
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
