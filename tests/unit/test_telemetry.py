"""Unit tests for telemetry module."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from backend import telemetry


class TestTelemetry:
    def teardown_method(self) -> None:
        telemetry._BUFFER.clear()
        telemetry._SESSION_FILE = None

    def test_enabled_false_by_default(self) -> None:
        assert not telemetry._enabled()

    def test_enabled_with_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CINEFORGE_TELEMETRY", "1")
        assert telemetry._enabled()

    def test_write_when_disabled(self) -> None:
        telemetry._write({"event": "test"})
        assert len(telemetry._BUFFER) == 0

    def test_write_when_enabled(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("CINEFORGE_TELEMETRY", "1")
        monkeypatch.setattr(telemetry, "_TELEMETRY_DIR", tmp_path)
        telemetry._SESSION_FILE = None
        telemetry._write({"event": "render"})
        assert len(telemetry._BUFFER) == 1
        assert telemetry._BUFFER[0]["event"] == "render"
        assert "_ts" in telemetry._BUFFER[0]

    def test_log_render_event(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("CINEFORGE_TELEMETRY", "1")
        monkeypatch.setattr(telemetry, "_TELEMETRY_DIR", tmp_path)
        telemetry._SESSION_FILE = None
        telemetry.log_render_event("s1", "veo", True, 5.0, 0.5)
        assert len(telemetry._BUFFER) == 1
        assert telemetry._BUFFER[0]["shot_id"] == "s1"

    def test_session_summary_empty(self) -> None:
        summary = telemetry.session_summary()
        assert summary["render_count"] == 0
        assert summary["total_cost_usd"] == 0.0

    def test_session_summary_with_events(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("CINEFORGE_TELEMETRY", "1")
        monkeypatch.setattr(telemetry, "_TELEMETRY_DIR", tmp_path)
        telemetry._SESSION_FILE = None
        telemetry.log_render_event("s1", "veo", True, 5.0, 0.5)
        telemetry.log_render_event("s2", "veo", False, 3.0, 0.0, error="timeout")
        telemetry.log_stitch_event("p1", 2, "/out.mp4", 8.0)
        summary = telemetry.session_summary()
        assert summary["render_count"] == 2
        assert summary["render_successes"] == 1
        assert summary["render_failures"] == 1
        assert summary["stitch_count"] == 1
        assert summary["provider_cost"]["veo"] == 0.5
        assert summary["provider_renders"]["veo"] == 2
