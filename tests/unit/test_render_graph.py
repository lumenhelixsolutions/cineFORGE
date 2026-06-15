"""Unit smokes for CineForge render-graph (M16)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RENDER_GRAPH = Path(__file__).resolve().parents[2] / "render-graph"
sys.path.insert(0, str(RENDER_GRAPH))

from runner import build_graph, invoke_graph, load_graph_profiles, resolve_profile_config  # noqa: E402


def test_graph_profiles_load():
    doc = load_graph_profiles()
    assert doc.get("profiles")
    assert "preview-chain" in doc["profiles"]


def test_resolve_profile_config():
    cfg = resolve_profile_config("dry-run-audit")
    assert cfg["graph"] == "cineforge-render-pipeline"
    assert cfg["preview_mode"] is True


def test_build_graph_compiles():
    app = build_graph()
    assert app is not None


def test_invoke_graph_dry_run_without_project(monkeypatch):
    """Dry-run skips HTTP when project fetch would fail — uses ingest skip path."""
    result = invoke_graph(
        "dry-run-audit",
        project_id="00000000-0000-0000-0000-000000000099",
        dry_run_mode=True,
        auto_approve=True,
    )
    assert result["dry_run_mode"] is True
    assert result["ok"] is True
    assert result["state"]["render_job"]["status"] == "dry_run"


def test_graph_spec_present():
    spec = json.loads((RENDER_GRAPH / "graph.spec.json").read_text(encoding="utf-8"))
    assert spec["name"] == "cineforge-render-pipeline"
    assert "approve_storyboard" in {n["id"] for n in spec["nodes"]}