"""Unit tests for preflight checks."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.preflight import PreflightError, check_disk_space, run_all


class TestCheckDiskSpace:
    def test_ok_when_enough_space(self, tmp_path: Path) -> None:
        proj = MagicMock()
        proj.id = "test-proj"
        proj.output_dir = str(tmp_path)
        result = check_disk_space(proj, required_mb=1)
        assert result["check"] == "disk_space"
        assert result["status"] == "ok"
        assert result["free_mb"] > 0

    def test_error_when_insufficient_space(self, tmp_path: Path) -> None:
        proj = MagicMock()
        proj.id = "test-proj"
        proj.output_dir = str(tmp_path)
        with patch("shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=1024)  # 1 KB
            with pytest.raises(PreflightError, match="Insufficient disk space"):
                check_disk_space(proj, required_mb=1024)


class TestRunAll:
    def test_returns_results(self, tmp_path: Path) -> None:
        proj = MagicMock()
        proj.id = "test-proj"
        proj.output_dir = str(tmp_path)
        results = run_all(proj)
        assert isinstance(results, list)
        assert any(r["check"] == "disk_space" for r in results)
