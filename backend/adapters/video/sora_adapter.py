"""OpenAI Sora 2 adapter — platform API via api.openai.com.

Note: OpenAI shut down the consumer Sora app in March 2026. The platform API
endpoint documented here (`/v1/video/generations`) may still exist for
enterprise/approved developers, but availability is uncertain and subject to
change without notice.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

import httpx

from backend.adapters.protocols import (
    VideoModel,
    VideoCapabilities,
    VideoGenRequest,
    VideoGenResult,
    ExtendRequest,
    CapabilityError,
)

logger = logging.getLogger(__name__)

try:
    import openai
except ModuleNotFoundError:
    openai = None  # type: ignore[assignment]


class SoraAdapter:
    """Real adapter for OpenAI Sora 2."""

    def __init__(self, model_id: str = "sora-2") -> None:
        self._model_id = model_id
        self._api_key = os.getenv("OPENAI_API_KEY", "")
        self.capabilities = VideoCapabilities(
            provider_id="openai.sora",
            display_name="OpenAI Sora 2",
            supported_durations_sec=[4, 6, 8, 10, 20],
            supported_aspect_ratios=["16:9", "9:16", "1:1"],
            supported_resolutions=["720p", "1080p"],
            max_reference_images=0,
            supports_native_audio=False,
            supports_frame_conditioning=False,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=True,
            is_local=False,
            cost_per_second_usd=0.15,
            notes="Requires OPENAI_API_KEY. Platform API availability uncertain after March 2026 consumer app shutdown.",
        )

    def estimate_cost(self, duration_sec: int, resolution: str = "720p") -> float:
        rate = {"720p": 0.10, "1080p": 0.20, "4k": 0.50}.get(resolution, 0.15)
        if "pro" in self._model_id:
            rate *= 2
        return duration_sec * rate

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")

        if os.getenv("CINEFORGE_MOCK_VIDEO", "false").lower() == "true":
            return self._mock_generate(req)

        if openai is not None:
            try:
                return await self._generate_sdk(req)
            except Exception as exc:
                logger.warning(
                    "OpenAI SDK video generation failed, falling back to httpx: %s", exc
                )

        return await self._generate_httpx(req)

    async def _generate_sdk(self, req: VideoGenRequest) -> VideoGenResult:
        if openai is None:
            raise RuntimeError("openai SDK is not installed")
        client = openai.AsyncOpenAI(api_key=self._api_key)
        if not hasattr(client, "video"):
            raise RuntimeError("OpenAI SDK does not expose video resource")

        kwargs: dict[str, Any] = {
            "model": self._model_id,
            "prompt": req.prompt,
        }
        if req.negative_prompt:
            kwargs["negative_prompt"] = req.negative_prompt

        image_path = req.first_frame or (
            req.reference_images[0] if req.reference_images else None
        )
        if image_path is not None:
            kwargs["image"] = self._image_to_data_uri(image_path)

        client_any = cast(Any, client)
        generation = await client_any.video.generations.create(**kwargs)
        for _ in range(120):
            generation = await client_any.video.generations.retrieve(
                generation.id
            )
            status = getattr(generation, "status", None)
            if status == "completed":
                break
            if status in ("failed", "error"):
                reason = getattr(generation, "failure_reason", "unknown")
                raise RuntimeError(f"Sora generation failed: {reason}")
            await asyncio.sleep(5)
        else:
            raise RuntimeError("Sora generation polling timed out")

        video_url = self._extract_video_url(generation)
        if not video_url:
            raise RuntimeError("No video URL in Sora response")

        async with httpx.AsyncClient(timeout=300.0) as http:
            video_resp = await http.get(video_url)
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

    async def _generate_httpx(self, req: VideoGenRequest) -> VideoGenResult:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self._model_id,
            "prompt": req.prompt,
            "duration": req.duration_sec,
            "size": self._aspect_ratio_to_size(req.aspect_ratio),
        }
        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt

        image_path = req.first_frame or (
            req.reference_images[0] if req.reference_images else None
        )
        if image_path is not None:
            payload["image"] = self._image_to_data_uri(image_path)

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/video/generations",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            job_id = data.get("id")
            if not job_id:
                raise RuntimeError("No job ID in Sora response")

            video_url = await self._poll_job(client, job_id, headers)
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

    async def _poll_job(
        self, client: httpx.AsyncClient, job_id: str, headers: dict[str, str]
    ) -> str:
        for _ in range(120):
            resp = await client.get(
                f"https://api.openai.com/v1/video/generations/{job_id}",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status == "completed":
                url = self._extract_video_url(data)
                if not url:
                    raise RuntimeError("No video URL in completed Sora job")
                return url
            if status in ("failed", "error"):
                raise RuntimeError(
                    f"Sora job {job_id} failed: {data.get('failure_reason', 'unknown error')}"
                )
            await asyncio.sleep(5)
        raise RuntimeError("Sora job polling timed out")

    def _extract_video_url(self, data: Any) -> str | None:
        if isinstance(data, dict):
            for key in ("output", "video", "result", "data"):
                val = data.get(key)
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    return val[0].get("url")
                if isinstance(val, dict):
                    return val.get("url") or val.get("video_url")
        if hasattr(data, "output"):
            out = data.output
            if isinstance(out, list) and len(out) > 0:
                return getattr(out[0], "url", None)
        return None

    def _aspect_ratio_to_size(self, aspect_ratio: str) -> str:
        return {
            "16:9": "1920x1080",
            "9:16": "1080x1920",
            "1:1": "1080x1080",
            "4:3": "1440x1080",
            "3:4": "1080x1440",
        }.get(aspect_ratio, "1920x1080")

    async def extend(self, req: ExtendRequest) -> VideoGenResult:
        raise CapabilityError("Sora 2 does not support extend")

    async def healthcheck(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def _image_to_data_uri(self, path: Path) -> str:
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        suffix = path.suffix.lower()
        mime = (
            "image/jpeg"
            if suffix in (".jpg", ".jpeg")
            else "image/png"
            if suffix == ".png"
            else "image/webp"
        )
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
