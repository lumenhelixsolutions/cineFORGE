"""Wan2GP low-VRAM local adapter (Wan 2.2 GGUF, LTX-Video, HunyuanVideo)."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

import httpx
import yaml

from backend.adapters.protocols import (
    VideoModel, VideoCapabilities, VideoGenRequest, VideoGenResult,
    ExtendRequest, CapabilityError
)

logger = logging.getLogger(__name__)
WAN2GP_BASE = "http://localhost:7860"


class Wan2GPAdapter:
    """POSTs to a localhost Wan2GP server. Detects loaded models."""

    def __init__(self, model_id: str = "wan-2.2-14b-gguf") -> None:
        self._model_id = model_id
        self._manifest = self._load_manifest()
        self.capabilities = self._build_capabilities()

    def _load_manifest(self) -> dict[str, Any]:
        path = Path(__file__).with_suffix(".yaml")
        if path.exists():
            result: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
            return result
        return {}

    def _build_capabilities(self) -> VideoCapabilities:
        entry = self._manifest.get(self._model_id, {})
        return VideoCapabilities(
            provider_id=f"wan2gp.{self._model_id}",
            display_name=entry.get("display_name", self._model_id),
            supported_durations_sec=entry.get("durations", [4, 6]),
            supported_aspect_ratios=entry.get("aspect_ratios", ["16:9", "1:1"]),
            supported_resolutions=entry.get("resolutions", ["720p"]),
            max_reference_images=entry.get("max_refs", 0),
            supports_native_audio=entry.get("native_audio", False),
            supports_frame_conditioning=entry.get("frame_cond", False),
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=entry.get("negative_prompt", True),
            is_local=True,
            cost_per_second_usd=0.0,
            notes=entry.get("notes", "Requires localhost Wan2GP server"),
        )

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        if os.getenv("CINEFORGE_MOCK_VIDEO", "false").lower() == "true":
            return self._mock_generate(req)

        payload = {
            "prompt": req.prompt,
            "width": 1280 if req.aspect_ratio == "16:9" else 720,
            "height": 720 if req.aspect_ratio == "16:9" else 1280,
            "video_length": req.duration_sec * 8,  # frames at 8fps approx
            "steps": 20,
        }
        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt
        if req.seed is not None:
            payload["seed"] = req.seed

        async with httpx.AsyncClient(timeout=600.0) as client:
            try:
                resp = await client.post(f"{WAN2GP_BASE}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                video_path = data.get("video_path")
                if not video_path:
                    raise RuntimeError("No video_path in Wan2GP response")
                clip_path = Path(video_path)
                last_frame = self._extract_last_frame(clip_path)
                return VideoGenResult(
                    clip_path=clip_path,
                    last_frame_path=last_frame,
                    duration_sec=float(req.duration_sec),
                    has_audio=self.capabilities.supports_native_audio,
                    cost_usd=0.0,
                    provider_id=self.capabilities.provider_id,
                )
            except httpx.ConnectError:
                raise RuntimeError(f"Wan2GP server not reachable at {WAN2GP_BASE}")

    async def extend(self, req: ExtendRequest) -> VideoGenResult:
        raise CapabilityError("Wan2GP does not support extend")

    async def healthcheck(self) -> bool:
        try:
            import httpx
            r = httpx.get(f"{WAN2GP_BASE}/health", timeout=5.0)
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

    def _mock_generate(self, req: VideoGenRequest) -> VideoGenResult:
        import tempfile
        clip = Path(tempfile.mktemp(suffix=".mp4"))
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc=duration={req.duration_sec}:size=640x360:rate=30",
             "-pix_fmt", "yuv420p", str(clip)],
            capture_output=True,
            check=True,
        )
        last_frame = self._extract_last_frame(clip)
        return VideoGenResult(
            clip_path=clip,
            last_frame_path=last_frame,
            duration_sec=float(req.duration_sec),
            has_audio=False,
            cost_usd=0.0,
            provider_id=self.capabilities.provider_id + ".mock",
        )
