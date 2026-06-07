"""Kling 3.0 adapter — direct API via api.klingai.com."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from backend.adapters.protocols import (
    VideoCapabilities,
    VideoGenRequest,
    VideoGenResult,
    ExtendRequest,
    CapabilityError,
)

logger = logging.getLogger(__name__)


class KlingAdapter:
    """Real adapter for Kling 3.0."""

    def __init__(self, model_id: str = "kling-3.0") -> None:
        self._model_id = model_id
        self._api_key = os.getenv("KLING_API_KEY", "")
        self._base_url = os.getenv("KLING_BASE_URL", "https://api.klingai.com")
        self.capabilities = VideoCapabilities(
            provider_id="kling.3.0",
            display_name="Kling 3.0",
            supported_durations_sec=[5, 10],
            supported_aspect_ratios=["16:9", "9:16", "1:1"],
            supported_resolutions=["720p", "1080p"],
            max_reference_images=1,
            supports_native_audio=False,
            supports_frame_conditioning=True,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=True,
            is_local=False,
            cost_per_second_usd=0.075,
            notes="Requires KLING_API_KEY. Async task-based API via api.klingai.com.",
        )

    def estimate_cost(self, duration_sec: int, resolution: str = "720p") -> float:
        return duration_sec * self.capabilities.cost_per_second_usd

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        if not self._api_key:
            raise RuntimeError("KLING_API_KEY environment variable not set")

        if os.getenv("CINEFORGE_MOCK_VIDEO", "false").lower() == "true":
            return self._mock_generate(req)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        model_variant = (
            "kling-v3-image-to-video" if (req.reference_images or req.first_frame) else "kling-v3-text-to-video"
        )

        payload: dict[str, Any] = {
            "model": model_variant,
            "prompt": req.prompt,
            "duration": req.duration_sec,
            "aspect_ratio": req.aspect_ratio,
            "quality": req.resolution,
        }
        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt

        image_path = req.first_frame or (req.reference_images[0] if req.reference_images else None)
        if image_path is not None:
            payload["image_start"] = self._image_to_data_uri(image_path)

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/videos/generations",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get("task_id") or data.get("id")
            if not task_id:
                raise RuntimeError("No task ID in Kling response")

            video_url = await self._poll_task(client, task_id, headers)
            video_resp = await client.get(video_url)
            video_resp.raise_for_status()

            clip_path = self._save_clip(video_resp.content)
            last_frame_path = self._extract_last_frame(clip_path)

            return VideoGenResult(
                clip_path=clip_path,
                last_frame_path=last_frame_path,
                duration_sec=float(req.duration_sec),
                has_audio=self.capabilities.supports_native_audio,
                cost_usd=self.estimate_cost(req.duration_sec, req.resolution),
                provider_id=self.capabilities.provider_id,
            )

    async def _poll_task(self, client: httpx.AsyncClient, task_id: str, headers: dict[str, str]) -> str:
        for _ in range(120):
            resp = await client.get(
                f"{self._base_url}/v1/tasks/{task_id}",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status") or data.get("state")
            if status == "completed":
                video_url = (
                    data.get("video_url")
                    or data.get("result", {}).get("video_url")
                    or data.get("assets", {}).get("video")
                )
                if not video_url:
                    raise RuntimeError("No video URL in completed Kling task")
                return str(video_url)
            if status in ("failed", "error"):
                raise RuntimeError(f"Kling task {task_id} failed: {data.get('error', 'unknown error')}")
            if status == "rate_limited":
                raise RuntimeError("Kling rate limit exceeded")
            await asyncio.sleep(5)
        raise RuntimeError("Kling task polling timed out")

    async def extend(self, req: ExtendRequest) -> VideoGenResult:
        raise CapabilityError("Kling 3.0 does not support extend")

    async def healthcheck(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self._base_url}/v1/tasks",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return resp.status_code != 401
        except Exception:
            return False

    def _image_to_data_uri(self, path: Path) -> str:
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        suffix = path.suffix.lower()
        mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png" if suffix == ".png" else "image/webp"
        return f"data:{mime};base64,{b64}"

    def _save_clip(self, data: bytes) -> Path:
        fd, path_str = tempfile.mkstemp(suffix=".mp4")
        os.write(fd, data)
        os.close(fd)
        return Path(path_str)

    def _extract_last_frame(self, clip_path: Path) -> Path:
        out = clip_path.with_suffix(".last_frame.jpg")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-sseof",
                "-0.1",
                "-i",
                str(clip_path),
                "-vf",
                "scale=320:-1",
                "-vframes",
                "1",
                str(out),
            ],
            capture_output=True,
            check=True,
        )
        return out

    def _mock_generate(self, req: VideoGenRequest) -> VideoGenResult:
        clip = Path(tempfile.mktemp(suffix=".mp4"))
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"testsrc=duration={req.duration_sec}:size=640x360:rate=30",
                "-pix_fmt",
                "yuv420p",
                str(clip),
            ],
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
