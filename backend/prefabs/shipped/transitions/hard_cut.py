"""Hard cut — instant transition."""
from pathlib import Path
from typing import Any

def apply(clip_a: Path, clip_b: Path) -> Path:
    """No processing needed for hard cut; handled by concat demuxer."""
    return clip_b
