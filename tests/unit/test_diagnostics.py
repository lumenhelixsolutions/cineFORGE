"""Unit tests for the diagnostics engine."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.diagnostics import DiagnosticResult, DiagnosticsEngine


class TestDiagnosticResult:
    def test_to_dict(self) -> None:
        r = DiagnosticResult("test", "ok", "message", "fixit")
        assert r.to_dict() == {
            "name": "test",
            "status": "ok",
            "message": "message",
            "fix": "fixit",
        }


class TestDiagnosticsEngine:
    @pytest.fixture
    def engine(self, tmp_path: Path) -> DiagnosticsEngine:
        return DiagnosticsEngine(data_dir=tmp_path, projects_dir=tmp_path / "projects")

    @pytest.mark.asyncio
    async def test_run_all_returns_list(self, engine: DiagnosticsEngine) -> None:
        results = await engine.run_all()
        assert isinstance(results, list)
        assert len(results) >= 5
        names = {r.name for r in results}
        assert "Python Version" in names
        assert "FFmpeg" in names

    def test_check_python_version_ok(self, engine: DiagnosticsEngine) -> None:
        result = engine._check_python_version()
        assert result.status == "ok"
        assert "Python" in result.message

    def test_check_ffmpeg_not_found(self, engine: DiagnosticsEngine) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = engine._check_ffmpeg()
        assert result.status == "error"
        assert "not found" in result.message

    def test_check_data_dir_writable(self, engine: DiagnosticsEngine) -> None:
        result = engine._check_data_dir()
        assert result.status == "ok"
        assert "writable" in result.message

    def test_check_env_file_missing(self, engine: DiagnosticsEngine) -> None:
        with patch.object(Path, "exists", return_value=False):
            result = engine._check_env_file()
        assert result.status == "warning"
        assert ".env" in result.message

    def test_check_frontend_deps_missing(self, engine: DiagnosticsEngine) -> None:
        with patch.object(Path, "exists", return_value=False):
            result = engine._check_frontend_deps()
        assert result.status == "error"
        assert "node_modules" in result.message
