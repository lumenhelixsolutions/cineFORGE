"""Unit tests for optional local caption assist (M18)."""

from __future__ import annotations

import os

from backend.local_caption import caption_image, is_enabled


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("LOCAL_CAPTION_ENABLED", raising=False)
    assert is_enabled() is False
    out = caption_image("nope.png")
    assert out["ok"] is False


def test_enabled_missing_file(monkeypatch):
    monkeypatch.setenv("LOCAL_CAPTION_ENABLED", "true")
    out = caption_image("/nonexistent/panel.png")
    assert out["ok"] is False
    assert "not found" in out["error"].lower()