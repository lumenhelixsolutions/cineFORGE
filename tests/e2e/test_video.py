"""Tiny valid MP4 generator for E2E tests."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest
import requests


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


pytestmark = pytest.mark.e2e


@pytest.mark.e2e
class TestVideoPipeline:
    def test_video_pipeline(
        self,
        backend_server: str,
        mock_video_adapter,
        tmp_path: Path,
    ) -> None:
        """End-to-end test of project creation, ingest, treatment, storyboard, and mocked render."""
        base = backend_server

        # 1. Create project
        resp = requests.post(
            f"{base}/projects",
            json={
                "name": "E2E Video Pipeline",
                "aspect_ratio": "16:9",
                "resolution": "1080p",
                "target_duration_sec": 60,
            },
            timeout=10,
        )
        assert resp.status_code == 200
        project_id = resp.json()["id"]

        # 2. Ingest sample document
        test_file = tmp_path / "source.txt"
        test_file.write_text(
            "A woman discovers an old film reel in her grandmother's attic. "
            "The reel contains footage of a mysterious figure that seems to predict future events."
        )
        with open(test_file, "rb") as f:
            resp = requests.post(
                f"{base}/projects/{project_id}/sources",
                files={"file": ("source.txt", f, "text/plain")},
                timeout=10,
            )
        assert resp.status_code == 200
        source = resp.json()
        assert source["kind"] == "txt"
        assert source["word_count"] > 0

        # 3. Generate treatment
        resp = requests.post(
            f"{base}/projects/{project_id}/treatment",
            json={"topic": "documentary"},
            timeout=30,
        )
        assert resp.status_code == 200
        treatment = resp.json()
        assert "treatment" in treatment
        assert "token_usage" in treatment

        # 4. Generate storyboard (creates shots)
        resp = requests.post(
            f"{base}/projects/{project_id}/storyboard",
            json={"topic": "documentary"},
            timeout=30,
        )
        assert resp.status_code == 200
        storyboard = resp.json()
        assert storyboard["shot_count"] > 0

        # 5. Run mocked render
        resp = requests.post(
            f"{base}/projects/{project_id}/render",
            json={"shot_ids": None},
            timeout=10,
        )
        assert resp.status_code == 200
        job = resp.json()
        assert job["status"] == "queued"
        assert job["shot_count"] > 0

        # Poll until shots are done or failed
        for _ in range(40):
            proj = requests.get(f"{base}/projects/{project_id}", timeout=5).json()
            if all(s["status"] in ("done", "failed") for s in proj.get("shots", [])):
                break
            time.sleep(0.5)
        else:
            pytest.fail("Render did not complete in time")

        # Verify at least one shot succeeded
        proj = requests.get(f"{base}/projects/{project_id}", timeout=5).json()
        done_shots = [s for s in proj.get("shots", []) if s["status"] == "done"]
        assert len(done_shots) > 0, "No shots rendered successfully"

        # Verify clips exist
        for shot in done_shots:
            assert shot["clip_path"] is not None
            assert Path(shot["clip_path"]).exists()
