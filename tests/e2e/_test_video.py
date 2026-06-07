"""Tiny valid MP4 generator for E2E tests."""
from __future__ import annotations

import subprocess
from pathlib import Path


def generate_test_mp4(out_path: Path, duration_sec: int = 1, width: int = 640, height: int = 360) -> Path:
    """Generate a minimal valid H.264 MP4 using ffmpeg.

    Parameters
    ----------
    out_path:
        Destination file path.
    duration_sec:
        Length of the video in seconds.
    width, height:
        Frame dimensions.

    Returns
    -------
    The *out_path* for convenience.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration_sec}:size={width}x{height}:rate=30",
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "30",
        "-an",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed to generate test MP4: {result.stderr}")
    return out_path
