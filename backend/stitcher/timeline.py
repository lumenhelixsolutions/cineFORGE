"""Stitcher — assembles clips into master MP4 with transitions."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Callable, cast

from backend.postprocess.lut import apply_lut
from backend.stitcher.ffmpeg_wrap import run_ffmpeg, FFmpegError, concat_clips

logger = logging.getLogger(__name__)


class Stitcher:
    """Assembles rendered shots into a final video with transitions."""

    def __init__(self, project_dir: Path, transitions_dir: Path, prefabs_dir: Path | None = None) -> None:
        self.project_dir = project_dir
        self.transitions_dir = transitions_dir
        self.prefabs_dir = prefabs_dir
        self._temp_dir = project_dir / "temp"
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    def assemble(
        self,
        shots: list[Any],
        output_path: Path,
        aspect_ratio: str = "16:9",
        style_pack: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Concatenate clips with transitions, return timeline sidecar."""
        if not shots:
            raise ValueError("No shots to assemble")

        temp_files: list[Path] = []
        segments: list[Path] = []

        for shot in shots:
            clip = Path(shot.clip_path) if hasattr(shot, "clip_path") else Path(shot["clip_path"])
            if not clip.exists():
                logger.warning("Missing clip: %s", clip)
                continue

            # Normalize to common format
            processed = self._normalize_clip(clip, aspect_ratio)
            temp_files.append(processed)

            # LUT color grading
            lut_path = self._resolve_lut_for_shot(shot, style_pack)
            if lut_path is not None:
                lut_out = self._temp_dir / f"lut_{processed.name}"
                apply_lut(processed, lut_path, lut_out)
                temp_files.append(lut_out)
                processed = lut_out

            # Narration mixing
            narration_path = self._get_narration_path(shot)
            if narration_path is not None and narration_path.exists():
                narrated = self._temp_dir / f"narr_{processed.name}"
                processed = self._mix_narration(processed, narration_path, narrated)
                temp_files.append(narrated)

            # Transitions
            transition_in = getattr(shot, "transition_in", None) or shot.get("transition_in", "hard_cut")
            if transition_in != "hard_cut" and segments:
                apply_fn = self._load_transition(transition_in)
                if apply_fn is not None:
                    merged = apply_fn(segments[-1], processed)
                    if merged.parent == self._temp_dir:
                        temp_files.append(merged)
                    segments[-1] = merged
                else:
                    segments.append(processed)
            else:
                segments.append(processed)

        if not segments:
            raise ValueError("No valid clips found")

        if len(segments) == 1:
            run_ffmpeg(["-i", segments[0], "-c", "copy", output_path])
        else:
            concat_list = self._temp_dir / "concat.txt"
            with open(concat_list, "w") as f:
                for entry in segments:
                    f.write(f"file '{entry}'\n")
            concat_clips(concat_list, output_path)

        # Build timeline sidecar
        timeline = {
            "version": "1.1",
            "aspect_ratio": aspect_ratio,
            "duration_sec": sum(
                float(s.duration_sec) if hasattr(s, "duration_sec") else float(s["duration_sec"]) for s in shots
            ),
            "tracks": [
                {
                    "type": "video",
                    "clips": [
                        {
                            "shot_id": s.id if hasattr(s, "id") else s["id"],
                            "start_sec": 0,
                            "duration_sec": s.duration_sec if hasattr(s, "duration_sec") else s["duration_sec"],
                            "path": str(s.clip_path if hasattr(s, "clip_path") else s["clip_path"]),
                            "bridge": s.bridge_strategy
                            if hasattr(s, "bridge_strategy")
                            else s.get("bridge_strategy", "hard_cut"),
                            "transition_in": getattr(s, "transition_in", None) or s.get("transition_in", "hard_cut"),
                            "narration": str(self._get_narration_path(s)) if self._get_narration_path(s) else None,
                        }
                        for s in shots
                    ],
                }
            ],
        }

        # Clean temp files
        for temp_file in temp_files:
            temp_file.unlink(missing_ok=True)

        return timeline

    def _normalize_clip(self, clip: Path, aspect_ratio: str) -> Path:
        """Ensure clip matches target aspect ratio and codec."""
        out = self._temp_dir / f"norm_{clip.name}"
        w, h = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920) if aspect_ratio == "9:16" else (1080, 1080)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(clip),
                "-vf",
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(out),
            ],
            capture_output=True,
            check=True,
        )
        return out

    def _get_narration_path(self, shot: Any) -> Path | None:
        shot_id = shot.id if hasattr(shot, "id") else shot["id"]
        path = self.project_dir / "shots" / str(shot_id) / "narration.wav"
        return path if path.exists() else None

    def _mix_narration(self, video: Path, narration: Path, output: Path) -> Path:
        """Mix narration audio with video using amix, falling back to simple overlay."""
        try:
            run_ffmpeg(
                [
                    "-i",
                    video,
                    "-i",
                    narration,
                    "-filter_complex",
                    "[0:a][1:a]amix=inputs=2:duration=first[aout]",
                    "-map",
                    "0:v",
                    "-map",
                    "[aout]",
                    "-c:v",
                    "copy",
                    "-shortest",
                    output,
                ]
            )
        except FFmpegError:
            # Fallback if video has no audio stream
            run_ffmpeg(
                [
                    "-i",
                    video,
                    "-i",
                    narration,
                    "-c:v",
                    "copy",
                    "-map",
                    "0:v",
                    "-map",
                    "1:a",
                    "-shortest",
                    output,
                ]
            )
        return output

    def _load_transition(self, name: str) -> Callable[[Path, Path], Path] | None:
        path = self.transitions_dir / f"{name}.py"
        if not path.exists():
            return None
        import importlib.util

        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, "apply", None)
        if callable(fn):
            return cast(Callable[[Path, Path], Path], fn)
        return None

    def _resolve_lut_for_shot(self, shot: Any, style_pack: dict[str, Any] | None) -> Path | None:
        if not style_pack:
            return None
        lut_name: str | None = style_pack.get("lut_path")
        if not lut_name:
            return None
        lut = Path(lut_name)
        if lut.is_absolute() and lut.exists():
            return lut
        # Relative to prefabs dir
        prefabs_dir = self.prefabs_dir
        if prefabs_dir:
            p2: Path = prefabs_dir / "luts" / lut_name
            if p2.exists():
                return p2
        # Fallback to shipped luts
        shipped = Path(__file__).parent.parent / "prefabs" / "shipped" / "luts"
        p3: Path = shipped / lut_name
        if p3.exists():
            return p3
        return None
