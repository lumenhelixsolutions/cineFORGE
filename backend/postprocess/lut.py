"""LUT color grading via FFmpeg."""
from __future__ import annotations

from pathlib import Path

from backend.stitcher.ffmpeg_wrap import run_ffmpeg


def apply_lut(video_path: Path, lut_path: Path, output_path: Path) -> None:
    """Apply a 3D LUT (.cube) to a video using FFmpeg."""
    run_ffmpeg([
        "-i", video_path,
        "-vf", f"lut3d={lut_path}",
        "-c:a", "copy",
        output_path,
    ])
