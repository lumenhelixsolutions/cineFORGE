"""LangGraph runner for CineForge render pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph

from nodes import (
    GraphState,
    node_approve_render,
    node_approve_storyboard,
    node_export,
    node_ingest,
    node_render,
    node_stitch,
)

ROOT = Path(__file__).resolve().parent


def load_graph_profiles() -> dict[str, Any]:
    path = ROOT / "graph_profiles.json"
    if not path.exists():
        return {"version": 1, "profiles": {}, "graphs": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_profile_config(profile_id: str) -> dict[str, Any]:
    doc = load_graph_profiles()
    profiles = doc.get("profiles") or {}
    cfg = profiles.get(profile_id) or {}
    return {
        "profile_id": profile_id,
        "preview_mode": bool(cfg.get("previewMode", True)),
        "graph": cfg.get("graph") or "cineforge-render-pipeline",
    }


def should_continue_after_storyboard(state: GraphState) -> str:
    if state.get("error") or not state.get("approved_storyboard"):
        return "end"
    return "render"


def should_continue_after_render(state: GraphState) -> str:
    if state.get("error"):
        return "end"
    return "approve_render"


def should_continue_after_render_approve(state: GraphState) -> str:
    if state.get("error") or not state.get("approved_render"):
        return "end"
    return "stitch"


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("ingest", node_ingest)
    graph.add_node("approve_storyboard", node_approve_storyboard)
    graph.add_node("render", node_render)
    graph.add_node("approve_render", node_approve_render)
    graph.add_node("stitch", node_stitch)
    graph.add_node("export", node_export)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "approve_storyboard")
    graph.add_conditional_edges(
        "approve_storyboard",
        should_continue_after_storyboard,
        {"render": "render", "end": END},
    )
    graph.add_edge("render", "approve_render")
    graph.add_conditional_edges(
        "approve_render",
        should_continue_after_render_approve,
        {"stitch": "stitch", "end": END},
    )
    graph.add_edge("stitch", "export")
    graph.add_edge("export", END)
    return graph.compile()


def invoke_graph(
    profile_id: str,
    *,
    project_id: str,
    dry_run_mode: bool = False,
    auto_approve: bool = False,
    ingest_payload: dict[str, Any] | None = None,
    cineforge_base: str | None = None,
) -> dict[str, Any]:
    cfg = resolve_profile_config(profile_id)
    initial: GraphState = {
        "project_id": project_id,
        "dry_run_mode": dry_run_mode,
        "auto_approve": auto_approve,
        "preview_mode": cfg["preview_mode"],
        "ingest_payload": ingest_payload,
        "cineforge_base": cineforge_base,
        "approved_storyboard": False,
        "approved_render": False,
    }
    app = build_graph()
    final = app.invoke(initial)
    return {
        "ok": not final.get("error"),
        "profile_id": profile_id,
        "project_id": project_id,
        "config": cfg,
        "state": final,
        "error": final.get("error"),
        "dry_run_mode": dry_run_mode,
        "stitched": bool((final.get("stitch_result") or {}).get("output_path")),
    }