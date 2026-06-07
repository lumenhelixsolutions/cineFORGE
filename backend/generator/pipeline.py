"""RenderPipeline — orchestrates VideoModel protocol for shot generation."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, cast

from backend.adapters.registry import AdapterRegistry
from backend.adapters.protocols import VideoGenRequest, AspectRatio
from backend.token_ledger.router import RoutingConfig

logger = logging.getLogger(__name__)


class RenderPipeline:
    """Orchestrates video generation per shot, respecting routing and capabilities."""

    def __init__(
        self,
        registry: AdapterRegistry,
        router: RoutingConfig,
        project_dir: Path,
    ) -> None:
        self.registry = registry
        self.router = router
        self.project_dir = project_dir
        self._clips_dir = project_dir / "clips"
        self._clips_dir.mkdir(parents=True, exist_ok=True)

    async def render_shot(self, shot: Any, project: Any) -> Any:
        """Render a single shot via the routed provider, with optional post-processing."""
        tier = shot.tier if hasattr(shot, "tier") else shot.get("tier", "standard")
        preview = project.preview_mode if hasattr(project, "preview_mode") else False
        profile = project.routing_profile if hasattr(project, "routing_profile") else "hybrid"

        provider_id = self.router.resolve_video(tier, profile, preview)
        adapter = self.registry.video_adapter(provider_id)
        caps = adapter.capabilities

        # Build request
        aspect = cast(AspectRatio, project.aspect_ratio if hasattr(project, "aspect_ratio") else "16:9")
        resolution = project.resolution if hasattr(project, "resolution") else "1080p"
        prompt = shot.prompt_text if hasattr(shot, "prompt_text") else shot.get("prompt_text", "")

        refs = []
        if hasattr(shot, "ref_image_paths") and shot.ref_image_paths:
            refs = [Path(p) for p in shot.ref_image_paths if Path(p).exists()]

        # Frame bridge: use previous shot's last frame
        first_frame = None
        if shot.bridge_strategy == "frame_bridge" and caps.supports_frame_conditioning:
            prev = self._get_previous_shot(shot, project)
            if prev and prev.last_frame_path and Path(prev.last_frame_path).exists():
                first_frame = Path(prev.last_frame_path)

        req = VideoGenRequest(
            prompt=prompt,
            duration_sec=shot.duration_sec if hasattr(shot, "duration_sec") else 6,
            aspect_ratio=aspect,
            resolution=resolution,
            reference_images=refs[: caps.max_reference_images],
            first_frame=first_frame,
        )

        logger.info("Rendering shot %s via %s", getattr(shot, "id", "unknown"), provider_id)
        result = await adapter.generate(req)

        # Move result into project clips dir
        dest = self._clips_dir / f"{getattr(shot, 'id', 'unknown')}.mp4"
        shutil.copy2(result.clip_path, dest)
        result.clip_path = dest

        # Extract last frame if adapter didn't
        if not result.last_frame_path or not result.last_frame_path.exists():
            result.last_frame_path = self._extract_last_frame(dest)

        # ── Post-processing pipeline ──────────────────────────
        result = await self._post_process(result, profile, tier)

        return result

    async def _generate_narration(self, shot: Any, shot_dir: Path) -> Path | None:
        """Generate narration audio for a shot using the Piper TTS adapter."""
        text = getattr(shot, "narration", None) or shot.get("narration", "")
        if not text:
            return None
        try:
            adapter = self.registry.tts_adapter("piper.local")
        except KeyError:
            logger.warning("TTS adapter piper.local not found")
            return None
        out = shot_dir / "narration.wav"
        shot_dir.mkdir(parents=True, exist_ok=True)
        await adapter.synthesize(text=text, voice="en_US-lessac-medium", out=out)
        return out

    async def _generate_reference_images(
        self, shot: Any, shot_dir: Path, style_pack: dict[str, Any] | None = None
    ) -> Path | None:
        """Generate a reference image for hero/standard shots."""
        tier = getattr(shot, "tier", None) or shot.get("tier", "standard")
        if tier not in {"hero", "standard"}:
            return None
        prompt = getattr(shot, "prompt_text", None) or shot.get("prompt_text", "")
        if not prompt:
            return None

        adapters = self.registry.refimg_adapters()
        adapter_name = None
        if "local.diffusers" in adapters:
            adapter_name = "local.diffusers"
        elif "fal.flux" in adapters:
            adapter_name = "fal.flux"
        if not adapter_name:
            logger.warning("No refimg adapter available")
            return None

        adapter = adapters[adapter_name]
        style_hint = ""
        if style_pack:
            style_hint = f" Style: {style_pack.get('name', '')}. {style_pack.get('palette', '')}."
        full_prompt = f"{prompt}.{style_hint}"
        try:
            ref_path = await adapter.generate(full_prompt)
        except Exception as exc:
            logger.warning("Refimg generation failed: %s", exc)
            return None

        shot_dir.mkdir(parents=True, exist_ok=True)
        dest = shot_dir / "ref.png"
        shutil.copy2(ref_path, dest)
        return dest

    async def _post_process(self, result: Any, profile: str, tier: str) -> Any:
        """Apply RIFE interpolation and Real-ESRGAN upscaling if configured."""
        video_cfg = self.router.profiles.get(profile, {}).get("video", {})

        # RIFE interpolation
        interp_provider = video_cfg.get("post_interpolate")
        if interp_provider and tier in {"hero", "standard"}:
            try:
                interp_adapter = self.registry.video_adapter(interp_provider)
                interp_req = VideoGenRequest(
                    prompt=str(result.clip_path),
                    duration_sec=int(result.duration_sec),
                    aspect_ratio="16:9",
                    resolution="720p",
                )
                interp_result = await interp_adapter.generate(interp_req)
                result.clip_path = interp_result.clip_path
                result.last_frame_path = interp_result.last_frame_path
                result.provider_id = f"{result.provider_id}+rife"
                logger.info("Applied RIFE interpolation to %s", result.clip_path)
            except Exception as exc:
                logger.warning("RIFE interpolation failed: %s", exc)

        # Real-ESRGAN upscaling
        upscale_provider = video_cfg.get("post_upscale")
        if upscale_provider and tier in {"hero"}:
            try:
                upscale_adapter = self.registry.video_adapter(upscale_provider)
                upscale_req = VideoGenRequest(
                    prompt=str(result.clip_path),
                    duration_sec=int(result.duration_sec),
                    aspect_ratio="16:9",
                    resolution="1080p",
                )
                upscale_result = await upscale_adapter.generate(upscale_req)
                result.clip_path = upscale_result.clip_path
                result.last_frame_path = upscale_result.last_frame_path
                result.provider_id = f"{result.provider_id}+sr"
                logger.info("Applied Real-ESRGAN upscaling to %s", result.clip_path)
            except Exception as exc:
                logger.warning("Real-ESRGAN upscaling failed: %s", exc)

        return result

    def _get_previous_shot(self, shot: Any, project: Any) -> Any:
        shots = sorted(project.shots, key=lambda s: s.order_index)
        idx = next((i for i, s in enumerate(shots) if s.id == shot.id), -1)
        if idx > 0:
            return shots[idx - 1]
        return None

    def _extract_last_frame(self, clip: Path) -> Path:
        import subprocess

        out = clip.with_suffix(".last_frame.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(clip), "-vf", "scale=320:-1", "-vframes", "1", str(out)],
            capture_output=True,
            check=True,
        )
        return out
