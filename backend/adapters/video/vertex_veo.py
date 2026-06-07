"""Google Vertex AI Veo 3.1 adapter."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from backend.adapters.protocols import (
    VideoModel, VideoCapabilities, VideoGenRequest, VideoGenResult,
    ExtendRequest, CapabilityError
)

logger = logging.getLogger(__name__)


class VertexVeoAdapter:
    """Veo 3.1 / Veo 3.1 Fast / Veo 3 via google-genai SDK."""

    def __init__(self, model_id: str = "veo-3.1") -> None:
        self._model_id = model_id
        self.capabilities = VideoCapabilities(
            provider_id=f"vertex.{model_id}",
            display_name=f"Google {model_id}",
            supported_durations_sec=[4, 6, 8],
            supported_aspect_ratios=["16:9", "9:16", "1:1"],
            supported_resolutions=["720p", "1080p"],
            max_reference_images=3,
            supports_native_audio=True,
            supports_frame_conditioning=True,
            supports_extend=True,
            max_extend_total_sec=148,
            supports_negative_prompt=True,
            is_local=False,
            cost_per_second_usd=0.05 if "fast" in model_id else 0.10,
            notes="Requires GOOGLE_APPLICATION_CREDENTIALS",
        )
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(vertexai=True, project=os.getenv("GOOGLE_CLOUD_PROJECT"))
            except ImportError:
                raise RuntimeError("google-genai not installed")
        return self._client

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        if os.getenv("CINEFORGE_MOCK_VIDEO", "false").lower() == "true":
            return self._mock_generate(req)

        client = self._get_client()
        # Build generation config
        config: dict[str, Any] = {
            "aspect_ratio": req.aspect_ratio,
            "duration_seconds": req.duration_sec,
            "number_of_videos": 1,
        }
        if req.negative_prompt:
            config["negative_prompt"] = req.negative_prompt
        if req.seed is not None:
            config["seed"] = req.seed

        # Reference images
        refs: list[dict[str, Any]] = []
        for p in req.reference_images:
            refs.append({"image": {"bytes": p.read_bytes()}})
        if req.first_frame:
            refs.append({"image": {"bytes": req.first_frame.read_bytes()}, "type": "FIRST_FRAME"})
        if req.last_frame:
            refs.append({"image": {"bytes": req.last_frame.read_bytes()}, "type": "LAST_FRAME"})

        try:
            operation = client.models.generate_videos(
                model=self._model_id,
                prompt=req.prompt,
                config=config,
            )
            # Poll for result
            import time
            while not operation.done:
                time.sleep(5)
                operation = client.operations.get(operation)

            video_bytes = operation.result.generated_videos[0].video.bytes
            clip_path = self._save_clip(video_bytes, req)
            last_frame_path = self._extract_last_frame(clip_path)

            return VideoGenResult(
                clip_path=clip_path,
                last_frame_path=last_frame_path,
                duration_sec=float(req.duration_sec),
                has_audio=True,
                cost_usd=req.duration_sec * self.capabilities.cost_per_second_usd,
                provider_id=self.capabilities.provider_id,
            )
        except Exception as exc:
            logger.error("Veo generation failed: %s", exc)
            raise

    async def extend(self, req: ExtendRequest) -> VideoGenResult:
        if not self.capabilities.supports_extend:
            raise CapabilityError("Extend not supported")
        # Veo extend: use the source clip as first frame + prompt
        return await self.generate(VideoGenRequest(
            prompt=req.prompt,
            duration_sec=req.duration_sec,
            aspect_ratio="16:9",  # inferred from source
            resolution="1080p",
            first_frame=req.source_clip,
        ))

    async def healthcheck(self) -> bool:
        try:
            return bool(os.getenv("GOOGLE_CLOUD_PROJECT"))
        except Exception:
            return False

    def _save_clip(self, data: bytes, req: VideoGenRequest) -> Path:
        out = Path("/tmp") / f"veo_{os.urandom(4).hex()}.mp4"
        out.write_bytes(data)
        return out

    def _extract_last_frame(self, clip_path: Path) -> Path:
        out = clip_path.with_suffix(".last_frame.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(clip_path), "-vf", r"select=eq(n\,0)+eq(n\,N-1)",
             "-vsync", "vfr", "-q:v", "2", str(out)],
            capture_output=True,
            check=True,
        )
        # Actually extract last frame properly
        subprocess.run(
            ["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(clip_path),
             "-vf", "scale=320:-1", "-vframes", "1", str(out)],
            capture_output=True,
            check=True,
        )
        return out

    def _mock_generate(self, req: VideoGenRequest) -> VideoGenResult:
        """Return a synthetic result for testing."""
        import tempfile
        clip = Path(tempfile.mktemp(suffix=".mp4"))
        # Generate a test video with ffmpeg
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
