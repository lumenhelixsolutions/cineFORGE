"""Flash white — 3-frame white flash."""

from pathlib import Path
import subprocess


def apply(clip_a: Path, clip_b: Path) -> Path:
    out = clip_a.with_name(f"{clip_a.stem}_flash_{clip_b.stem}.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(clip_a),
            "-i",
            str(clip_b),
            "-filter_complex",
            "[0:v][1:v]xfade=transition=fadewhite:duration=0.1:offset=0[outv];[0:a][1:a]acrossfade=d=0.1[outa]",
            "-map",
            "[outv]",
            "-map",
            "[outa]",
            str(out),
        ],
        capture_output=True,
        check=True,
    )
    return out
