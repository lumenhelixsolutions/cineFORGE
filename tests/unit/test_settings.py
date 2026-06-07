"""Unit tests for application settings."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.settings import Settings, get_settings, _settings


class TestSettings:
    def teardown_method(self) -> None:
        # Reset singleton between tests
        import backend.settings as s
        s._settings = None

    def test_default_values(self, tmp_path: Path) -> None:
        s = Settings(data_dir=tmp_path)
        assert s.port == 8765
        assert s.host == "127.0.0.1"
        assert s.default_routing_profile == "hybrid"
        assert s.projects_dir == tmp_path / "projects"
        assert s.prefabs_dir == tmp_path / "prefabs"
        assert s.cache_dir == tmp_path / "cache"
        assert "sqlite" in s.database_url

    def test_mock_flags_from_env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("CINEFORGE_MOCK_VIDEO", "true")
        monkeypatch.setenv("CINEFORGE_MOCK_LLM", "TRUE")
        s = Settings(data_dir=tmp_path)
        assert s.mock_video is True
        assert s.mock_llm is True

    def test_directories_created(self, tmp_path: Path) -> None:
        data = tmp_path / "new_data"
        s = Settings(data_dir=data)
        assert data.exists()
        assert s.projects_dir.exists()
        assert s.prefabs_dir.exists()
        assert s.cache_dir.exists()

    def test_get_settings_singleton(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CINEFORGE_DATA_DIR", str(tmp_path))
        import backend.settings as s
        s._settings = None
        a = get_settings()
        b = get_settings()
        assert a is b
