"""Frame bridge — handled by generator, no stitcher filter needed."""

from pathlib import Path


def apply(clip_a: Path, clip_b: Path) -> Path:
    return clip_b
