"""Luma Dream Machine adapter — direct API via api.lumalabs.ai or fal.ai fallback."""

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


class LumaAdapter:
    """Real adapter for Luma Dream Machine / Ray 2."""

    def __init__(self, model_id: str = "ray-2") -> None:
        self._model_id = model_id
        self._luma_key = os.getenv("LUMA_API_KEY", "")
        self._fal_key = os.getenv("FAL_KEY", "")
        self._base_url = os.getenv("LUMA_BASE_URL", "https://api.lumalabs.ai/dream-machine/v1")
        self._use_fal = not self._luma_key and bool(self._fal_key)
        self.capabilities = VideoCapabilities(
            provider_id="luma.dream-machine",
            display_name="Luma Dream Machine",
            supported_durations_sec=[5, 9],
            supported_aspect_ratios=["16:9", "9:16", "1:1", "4:3", "3:4"],
            supported_resolutions=["540p", "720p", "1080p", "4k"],
            max_reference_images=2,
            supports_native_audio=False,
            supports_frame_conditioning=True,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=False,
            is_local=False,
            cost_per_second_usd=0.05,
            notes="Requires LUMA_API_KEY or FAL_KEY. Supports first/last frame conditioning.",
        )

    def estimate_cost(self, duration_sec: int, resolution: str = "720p") -> float:
        multiplier = {"540p": 1.0, "720p": 2.0, "1080p": 4.0, "4k": 8.0}.get(resolution, 1.0)
        base = 0.50 if self._use_fal else self.capabilities.cost_per_second_usd * 5
        per_sec = base / 5 * multiplier
        return duration_sec * per_sec

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        if not self._luma_key and not self._fal_key:
            raise RuntimeError("LUMA_API_KEY or FAL_KEY environment variable not set")

        if os.getenv("CINEFORGE_MOCK_VIDEO", "false").lower() == "true":
            return self._mock_generate(req)

        if self._use_fal:
            return await self._generate_fal(req)
        return await self._generate_direct(req)

    async def _generate_direct(self, req: VideoGenRequest) -> VideoGenResult:
        headers = {
            "Authorization": f"Bearer {self._luma_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self._model_id,
            "prompt": req.prompt,
            "aspect_ratio": req.aspect_ratio,
            "duration": f"{req.duration_sec}s",
            "resolution": req.resolution,
            "loop": False,
        }

        if req.first_frame is not None:
            payload["frame0_image"] = self._image_to_data_uri(req.first_frame)
        if req.last_frame is not None:
            payload["frame1_image"] = self._image_to_data_uri(req.last_frame)
        if req.reference_images and not (req.first_frame or req.last_frame):
            payload["frame0_image"] = self._image_to_data_uri(req.reference_images[0])

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self._base_url}/generations",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            gen_id = data.get("id")
            if not gen_id:
                raise RuntimeError("No generation ID in Luma response")

            video_url = await self._poll_generation(client, gen_id, headers)
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

    async def _poll_generation(self, client: httpx.AsyncClient, gen_id: str, headers: dict[str, str]) -> str:
        for _ in range(120):
            resp = await client.get(
                f"{self._base_url}/generations/{gen_id}",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            state = data.get("state")
            if state == "completed":
                url = data.get("assets", {}).get("video") or data.get("video_url")
                if not url:
                    raise RuntimeError("No video URL in completed Luma generation")
                return str(url)
            if state == "failed":
                reason = data.get("failure_reason") or data.get("error", "unknown")
                raise RuntimeError(f"Luma generation {gen_id} failed: {reason}")
            await asyncio.sleep(5)
        raise RuntimeError("Luma generation polling timed out")

    async def _generate_fal(self, req: VideoGenRequest) -> VideoGenResult:
        headers = {
            "Authorization": f"Key {self._fal_key}",
            "Content-Type": "application/json",
        }
        endpoint = "fal-ai/luma-dream-machine"
        payload: dict[str, Any] = {
            "prompt": req.prompt,
            "aspect_ratio": req.aspect_ratio,
            "duration": req.duration_sec,
            "resolution": req.resolution,
        }
        if req.first_frame is not None:
            payload["image_url"] = self._image_to_data_uri(req.first_frame)
        if req.last_frame is not None:
            payload["end_image_url"] = self._image_to_data_uri(req.last_frame)

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

    async def extend(self, req: ExtendRequest) -> VideoGenResult:
        raise CapabilityError("Luma Dream Machine does not support extend")

    async def healthcheck(self) -> bool:
        if self._use_fal:
            return bool(self._fal_key)
        if not self._luma_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self._base_url}/generations",
                    headers={"Authorization": f"Bearer {self._luma_key}"},
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
