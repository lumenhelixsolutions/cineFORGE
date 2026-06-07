"""Typed FFmpeg wrapper — never use shell=True."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    pass


def run_ffmpeg(args: Sequence[str | Path], timeout: int = 300) -> subprocess.CompletedProcess[str]:
    """Run ffmpeg with typed args, no shell interpolation."""
    cmd = ["ffmpeg", "-y"] + [str(a) for a in args]
    logger.debug("FFmpeg: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
        return result
    except subprocess.CalledProcessError as exc:
        logger.error("FFmpeg failed: %s\nstderr: %s", exc.cmd, exc.stderr)
        raise FFmpegError(f"FFmpeg failed: {exc.stderr}") from exc
    except FileNotFoundError:
        raise FFmpegError("ffmpeg binary not found in PATH")


def extract_last_frame(clip: Path, out: Path | None = None, scale: int = 320) -> Path:
    """Extract the last frame of a video clip."""
    if out is None:
        out = clip.with_suffix(".last_frame.jpg")
    run_ffmpeg([
        "-sseof", "-0.1", "-i", clip,
        "-vf", f"scale={scale}:-1",
        "-vframes", "1",
        out,
    ])
    return out


def concat_clips(clip_list_path: Path, output: Path) -> None:
    """Concatenate clips using the concat demuxer."""
    run_ffmpeg([
        "-f", "concat", "-safe", "0",
        "-i", clip_list_path,
        "-c", "copy",
        output,
    ])


def normalize_video(input_path: Path, output: Path, width: int, height: int) -> None:
    """Normalize video to target dimensions with padding."""
    run_ffmpeg([
        "-i", input_path,
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        output,
    ])
