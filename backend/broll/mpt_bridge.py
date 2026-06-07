"""MoneyPrinterTurbo B-roll bridge.

Extracts scene metadata (description, location, mood, time-of-day) from a shot
and generates supplementary B-roll footage via the MoneyPrinterTurbo REST API.
"""

from __future__ import annotations

import logging
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from backend.settings import get_settings

logger = logging.getLogger(__name__)


def _extract_metadata(shot: Any) -> dict[str, str]:
    """Pull location, mood, time-of-day from shot continuity / prompt."""
    continuity: dict[str, Any] = (
        shot.continuity if hasattr(shot, "continuity") else shot.get("continuity", {}) or {}
    )
    prompt: str = (
        shot.prompt_text if hasattr(shot, "prompt_text") else shot.get("prompt_text", "") or ""
    )

    location = continuity.get("location", "")
    mood = continuity.get("mood", "")
    time_of_day = continuity.get("time_of_day", "")

    # Fallback heuristics from prompt text
    if not location:
        for keyword in ("attic", "forest", "beach", "city", "street", "mountain", "room", "house", "studio", "park", "ocean"):
            if keyword in prompt.lower():
                location = keyword
                break
    if not mood:
        for keyword in ("melancholic", "tense", "joyful", "dark", "bright", "somber", "mysterious", "romantic", "eerie"):
            if keyword in prompt.lower():
                mood = keyword
                break
    if not time_of_day:
        for keyword in ("sunrise", "sunset", "dawn", "dusk", "night", "evening", "morning", "midday"):
            if keyword in prompt.lower():
                time_of_day = keyword
                break
        if not time_of_day:
            time_of_day = "day"

    description = prompt or continuity.get("summary", "")

    return {
        "description": description,
        "location": location or "unknown location",
        "mood": mood or "neutral",
        "time_of_day": time_of_day,
    }


def _build_broll_prompt(meta: dict[str, str], style_hint: str = "") -> str:
    """Craft a cinematic B-roll prompt from extracted metadata."""
    parts = [
        f"Cinematic B-roll footage: {meta['description']}",
        f"Setting: {meta['location']} at {meta['time_of_day']}",
        f"Atmosphere: {meta['mood']}",
        "Slow, smooth camera movement. Shallow depth of field."
        " Professional colour grading, high detail, 4K aesthetic.",
    ]
    prompt = " ".join(parts)
    if style_hint:
        prompt += f" {style_hint}"
    return prompt


class MPTBrollBridge:
    """Bridge that turns shot metadata into tailored B-roll clips via MoneyPrinterTurbo."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self._broll_dir = project_dir / "broll"
        self._broll_dir.mkdir(parents=True, exist_ok=True)

    async def generate_for_shot(
        self,
        shot: Any,
        project: Any,
        mpt_bridge: Any | None = None,
    ) -> dict[str, Any]:
        """Generate a single B-roll clip for *shot* via MPT.

        Returns a dict with clip_path, thumbnail_path, metadata, cost_usd, provider_id.
        """
        from tools.shared.mpt_bridge import get_bridge

        meta = _extract_metadata(shot)
        style_hint = ""
        if hasattr(project, "style_pack_id") and project.style_pack_id:
            style_hint = f"Style pack: {project.style_pack_id}."

        prompt = _build_broll_prompt(meta, style_hint)

        bridge = mpt_bridge or get_bridge()
        result = bridge.generate_video(
            video_subject=prompt,
            video_script="",
            video_concat_mode="random",  # B-roll style: random cuts
            subtitle_enabled=False,
            bgm_type="no_music",
        )
        task_id = result.get("task_id")
        if not task_id:
            raise RuntimeError("MPT did not return a task_id")

        # Poll MPT until completion (with timeout)
        video_url = await self._poll_mpt_task(bridge, task_id, timeout_sec=300)

        # Download video into project vault
        clip_name = f"broll_{getattr(shot, 'id', uuid.uuid4().hex)}_{uuid.uuid4().hex[:8]}.mp4"
        dest = self._broll_dir / clip_name
        await self._download_video(video_url, dest)

        # Extract thumbnail
        thumb = self._extract_thumbnail(dest)

        return {
            "clip_path": str(dest),
            "thumbnail_path": str(thumb) if thumb else None,
            "metadata": meta,
            "cost_usd": 0.0,  # MPT cost tracking is external
            "provider_id": "mpt",
            "prompt_text": prompt,
            "duration_sec": 0.0,  # Could probe with ffprobe if needed
        }

    async def _poll_mpt_task(self, bridge: Any, task_id: str, timeout_sec: int = 300) -> str:
        """Poll MPT until the task is complete and return the video URL."""
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            status = bridge.get_task(task_id)
            data = status.get("data", status)
            state = data.get("state", data.get("status", "unknown"))
            if state in ("completed", "success", "done"):
                url = data.get("video_url", data.get("url", ""))
                if url:
                    return url
                raise RuntimeError("MPT task completed but no video_url returned")
            if state in ("failed", "error"):
                raise RuntimeError(f"MPT task failed: {data}")
            await self._async_sleep(5)
        raise RuntimeError("MPT task polling timed out")

    async def _async_sleep(self, seconds: float) -> None:
        import asyncio
        await asyncio.sleep(seconds)

    async def _download_video(self, url: str, dest: Path) -> None:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)

    def _extract_thumbnail(self, clip: Path) -> Path | None:
        """Extract a single frame to use as thumbnail."""
        import subprocess

        out = clip.with_suffix(".jpg")
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(clip),
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
        except Exception as exc:
            logger.warning("Thumbnail extraction failed: %s", exc)
            return None
