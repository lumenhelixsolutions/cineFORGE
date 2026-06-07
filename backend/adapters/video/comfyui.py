"""ComfyUI maximalist local adapter."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path

import httpx

from backend.adapters.protocols import (
    VideoModel, VideoCapabilities, VideoGenRequest, VideoGenResult,
    ExtendRequest, CapabilityError
)

logger = logging.getLogger(__name__)
COMFY_BASE = "http://localhost:8188"


class ComfyUIAdapter:
    """Posts to a localhost ComfyUI instance with user-supplied workflow JSON."""

    def __init__(self, workflow_path: str | None = None) -> None:
        self._workflow_path = workflow_path or self._default_workflow()
        self.capabilities = VideoCapabilities(
            provider_id="comfyui.local",
            display_name="ComfyUI (Local)",
            supported_durations_sec=[4, 6, 8, 10, 12],
            supported_aspect_ratios=["16:9", "9:16", "1:1", "4:3"],
            supported_resolutions=["720p", "1080p", "4k"],
            max_reference_images=4,
            supports_native_audio=False,
            supports_frame_conditioning=True,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=True,
            is_local=True,
            cost_per_second_usd=0.0,
            notes="Arbitrary workflows. User configures workflow JSON path.",
        )

    def _default_workflow(self) -> str:
        ref = Path(__file__).parent / "workflows" / "wan2.2_default.json"
        return str(ref)

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        if os.getenv("CINEFORGE_MOCK_VIDEO", "false").lower() == "true":
            return self._mock_generate(req)

        workflow = json.loads(Path(self._workflow_path).read_text())
        # Inject prompt into workflow — simplistic substitution
        for node in workflow.values():
            if isinstance(node, dict) and "inputs" in node:
                if "text" in node["inputs"] and node["inputs"]["text"] == "__PROMPT__":
                    node["inputs"]["text"] = req.prompt
                if "width" in node["inputs"]:
                    node["inputs"]["width"] = 1280 if req.aspect_ratio == "16:9" else 720
                if "height" in node["inputs"]:
                    node["inputs"]["height"] = 720 if req.aspect_ratio == "16:9" else 1280
                if "duration" in node["inputs"]:
                    node["inputs"]["duration"] = req.duration_sec

        async with httpx.AsyncClient(timeout=600.0) as client:
            # Queue prompt
            queue_resp = await client.post(
                f"{COMFY_BASE}/prompt",
                json={"prompt": workflow},
            )
            queue_resp.raise_for_status()
            prompt_id = queue_resp.json()["prompt_id"]

            # Poll for completion
            for _ in range(360):  # 30 minutes
                await client.get(f"{COMFY_BASE}/history/{prompt_id}")
                # Check output folder
                # Simplified: assume output lands in ComfyUI output dir
                time.sleep(5)

            # Find latest output
            output_dir = Path.home() / "ComfyUI" / "output"
            outputs = sorted(output_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not outputs:
                raise RuntimeError("No output video found from ComfyUI")
            clip_path = outputs[0]
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
        raise CapabilityError("ComfyUI extend not implemented in v0.1")

    async def healthcheck(self) -> bool:
        try:
            r = httpx.get(f"{COMFY_BASE}/system_stats", timeout=5.0)
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
