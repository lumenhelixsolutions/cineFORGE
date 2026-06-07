"""Unit tests for Stitcher and FFmpeg wrapper."""
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.stitcher.ffmpeg_wrap import (
    run_ffmpeg, extract_last_frame, concat_clips, normalize_video, FFmpegError
)
from backend.stitcher.timeline import Stitcher


class TestFFmpegWrap:
    def test_run_ffmpeg_success(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = run_ffmpeg(['-i', 'input.mp4', 'output.mp4'])
            assert result.returncode == 0
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == 'ffmpeg'
            assert '-i' in args
            assert 'input.mp4' in args

    def test_run_ffmpeg_failure_raises(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ['ffmpeg'], stderr=b'Error: codec not found'
            )
            with pytest.raises(FFmpegError, match="codec not found"):
                run_ffmpeg(['-bad-arg'])

    def test_run_ffmpeg_not_found(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            with pytest.raises(FFmpegError, match="not found in PATH"):
                run_ffmpeg(['-i', 'input.mp4'])

    def test_extract_last_frame(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            clip = Path('/tmp/test.mp4')
            out = extract_last_frame(clip)
            assert out == clip.with_suffix('.last_frame.jpg')
            mock_run.assert_called_once()

    def test_normalize_video(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            normalize_video(Path('/tmp/in.mp4'), Path('/tmp/out.mp4'), 1920, 1080)
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            cmd = " ".join(args)
            assert '1920' in cmd
            assert '1080' in cmd


class TestStitcher:
    def test_assemble_empty_shots_raises(self):
        stitcher = Stitcher(Path('/tmp/project'), Path('/tmp/transitions'))
        with pytest.raises(ValueError, match="No shots to assemble"):
            stitcher.assemble([], Path('/tmp/out.mp4'))

    def test_assemble_with_shots(self, tmp_path):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            project_dir = tmp_path / "project"
            transitions_dir = tmp_path / "transitions"
            project_dir.mkdir(parents=True, exist_ok=True)
            transitions_dir.mkdir(parents=True, exist_ok=True)
            clip_path = tmp_path / "fake.mp4"
            clip_path.write_bytes(b"fake")
            stitcher = Stitcher(project_dir, transitions_dir)

            # Create the normalized file that _normalize_clip would produce
            # since subprocess.run is mocked and won't create it
            norm_path = stitcher._temp_dir / f"norm_{clip_path.name}"
            norm_path.write_bytes(b"fake")

            shot = {
                "clip_path": str(clip_path),
                "duration_sec": 6,
                "id": "s1",
                "bridge_strategy": "hard_cut",
                "order_index": 0,
            }

            result = stitcher.assemble([shot], tmp_path / "out.mp4")
            assert 'tracks' in result
            assert result['aspect_ratio'] == '16:9'
            mock_run.assert_called()

    def test_assemble_with_transition(self, tmp_path):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            project_dir = tmp_path / "project"
            transitions_dir = tmp_path / "transitions"
            project_dir.mkdir(parents=True, exist_ok=True)
            transitions_dir.mkdir(parents=True, exist_ok=True)
            # Create a fake transition prefab
            (transitions_dir / "cross_dissolve_300ms.py").write_text(
                "from pathlib import Path\n"
                "def apply(clip_a, clip_b):\n"
                "    out = clip_a.with_name('merged.mp4')\n"
                "    return out\n"
            )
            clip1 = tmp_path / "clip1.mp4"
            clip2 = tmp_path / "clip2.mp4"
            clip1.write_bytes(b"fake1")
            clip2.write_bytes(b"fake2")
            stitcher = Stitcher(project_dir, transitions_dir)

            shots = [
                {"clip_path": str(clip1), "duration_sec": 6, "id": "s1", "bridge_strategy": "hard_cut", "order_index": 0},
                {"clip_path": str(clip2), "duration_sec": 4, "id": "s2", "bridge_strategy": "hard_cut", "transition_in": "cross_dissolve_300ms", "order_index": 1},
            ]
            result = stitcher.assemble(shots, tmp_path / "out.mp4")
            assert 'tracks' in result
            assert len(result['tracks'][0]['clips']) == 2
            # Normalize calls for 2 clips + final ffmpeg copy = 3 subprocess calls
            assert mock_run.call_count >= 2

    def test_assemble_with_narration(self, tmp_path):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            project_dir = tmp_path / "project"
            transitions_dir = tmp_path / "transitions"
            project_dir.mkdir(parents=True, exist_ok=True)
            transitions_dir.mkdir(parents=True, exist_ok=True)
            clip = tmp_path / "clip.mp4"
            clip.write_bytes(b"fake")
            # Create narration file
            shot_dir = project_dir / "shots" / "s1"
            shot_dir.mkdir(parents=True)
            narration_path = shot_dir / "narration.wav"
            narration_path.write_bytes(b"audio")
            stitcher = Stitcher(project_dir, transitions_dir)

            shot = {
                "clip_path": str(clip),
                "duration_sec": 6,
                "id": "s1",
                "bridge_strategy": "hard_cut",
                "order_index": 0,
            }
            result = stitcher.assemble([shot], tmp_path / "out.mp4")
            assert 'tracks' in result
            # Check that amix or fallback mapping was attempted
            calls = [" ".join(str(a) for a in call[0][0]) for call in mock_run.call_args_list]
            assert any("amix" in c or "-map 1:a" in c for c in calls)
