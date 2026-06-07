"""fal.ai multi-model aggregator adapter."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
import yaml

from backend.adapters.protocols import (
    VideoModel, VideoCapabilities, VideoGenRequest, VideoGenResult,
    ExtendRequest, CapabilityError
)

logger = logging.getLogger(__name__)


class FalAdapter:
    """Dispatches to fal.ai hosted models via fal-client."""

    def __init__(self, model_id: str = "veo-3.1") -> None:
        self._model_id = model_id
        self._manifest = self._load_manifest()
        self.capabilities = self._build_capabilities()
        self._api_key = os.getenv("FAL_KEY", "")

    def _load_manifest(self) -> dict[str, Any]:
        manifest_path = Path(__file__).with_suffix(".yaml")
        if manifest_path.exists():
            result: dict[str, Any] = yaml.safe_load(manifest_path.read_text()) or {}
            return result
        return {}

    def _build_capabilities(self) -> VideoCapabilities:
        entry = self._manifest.get(self._model_id, {})
        return VideoCapabilities(
            provider_id=f"fal.{self._model_id}",
            display_name=entry.get("display_name", f"fal {self._model_id}"),
            supported_durations_sec=entry.get("durations", [4, 6, 8]),
            supported_aspect_ratios=entry.get("aspect_ratios", ["16:9", "9:16", "1:1"]),
            supported_resolutions=entry.get("resolutions", ["720p", "1080p"]),
            max_reference_images=entry.get("max_refs", 0),
            supports_native_audio=entry.get("native_audio", False),
            supports_frame_conditioning=entry.get("frame_cond", False),
            supports_extend=entry.get("extend", False),
            max_extend_total_sec=entry.get("max_extend"),
            supports_negative_prompt=entry.get("negative_prompt", False),
            is_local=False,
            cost_per_second_usd=entry.get("cost_per_sec", 0.05),
            notes=entry.get("notes", ""),
        )

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        if not self._api_key:
            raise RuntimeError("FAL_KEY environment variable not set")

        if os.getenv("CINEFORGE_MOCK_VIDEO", "false").lower() == "true":
            return self._mock_generate(req)

        headers = {"Authorization": f"Key {self._api_key}", "Content-Type": "application/json"}
        endpoint = self._manifest.get(self._model_id, {}).get("endpoint", f"fal-ai/{self._model_id}")
        payload = {
            "prompt": req.prompt,
            "duration": req.duration_sec,
            "aspect_ratio": req.aspect_ratio,
        }
        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"https://queue.fal.run/{endpoint}",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            video_url = data.get("video", {}).get("url")
            if not video_url:
                raise RuntimeError("No video URL in fal response")

            video_resp = await client.get(video_url)
            video_resp.raise_for_status()
            clip_path = Path("/tmp") / f"fal_{self._model_id}_{os.urandom(4).hex()}.mp4"
            clip_path.write_bytes(video_resp.content)

            last_frame_path = self._extract_last_frame(clip_path)
            return VideoGenResult(
                clip_path=clip_path,
                last_frame_path=last_frame_path,
                duration_sec=float(req.duration_sec),
                has_audio=self.capabilities.supports_native_audio,
                cost_usd=req.duration_sec * self.capabilities.cost_per_second_usd,
                provider_id=self.capabilities.provider_id,
            )

    async def extend(self, req: ExtendRequest) -> VideoGenResult:
        raise CapabilityError("Extend not supported on fal adapter in v0.1")

    async def healthcheck(self) -> bool:
        return bool(self._api_key)

    def _extract_last_frame(self, clip_path: Path) -> Path:
        out = clip_path.with_suffix(".last_frame.jpg")
        import subprocess
        subprocess.run(
            ["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(clip_path),
             "-vf", "scale=320:-1", "-vframes", "1", str(out)],
            capture_output=True,
            check=True,
        )
        return out

    def _mock_generate(self, req: VideoGenRequest) -> VideoGenResult:
        import tempfile, subprocess
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
