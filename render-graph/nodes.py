"""LangGraph nodes for CineForge render pipeline (M16)."""

from __future__ import annotations

import os
import time
from typing import TypedDict

from cineforge_client import (
    DEFAULT_BASE,
    fetch_lookbook_review,
    fetch_project,
    ingest_lookbook,
    patch_project,
    queue_render,
    stitch_project,
)


class GraphState(TypedDict, total=False):
    project_id: str
    cineforge_base: str
    ingest_payload: dict
    dry_run_mode: bool
    auto_approve: bool
    preview_mode: bool
    review: dict
    project: dict
    render_job: dict
    stitch_result: dict
    approved_storyboard: bool
    approved_render: bool
    error: str | None


def node_ingest(state: GraphState) -> GraphState:
    if state.get("error"):
        return state
    project_id = state.get("project_id") or ""
    if not project_id:
        return {**state, "error": "project_id required"}
    payload = state.get("ingest_payload")
    if state.get("dry_run_mode"):
        return {
            **state,
            "review": {"available": True, "dryRun": True, "message": "ingest skipped in dry-run"},
            "error": None,
        }
    if not payload:
        try:
            project = fetch_project(project_id, base=state.get("cineforge_base") or DEFAULT_BASE)
            return {**state, "project": project, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {**state, "error": str(exc)}
    try:
        base = state.get("cineforge_base") or DEFAULT_BASE
        ingest_lookbook(project_id, payload, base=base)
        review = fetch_lookbook_review(project_id, base=base)
        return {**state, "review": review, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": str(exc)}


def node_approve_storyboard(state: GraphState) -> GraphState:
    if state.get("error"):
        return state
    auto = state.get("auto_approve") or os.environ.get("RENDER_GRAPH_AUTO_APPROVE", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if auto or state.get("dry_run_mode"):
        return {**state, "approved_storyboard": True}
    review = state.get("review") or {}
    print(f"\n[approve_storyboard] Accept living review '{review.get('title', 'import')}'? (y/N): ", end="", flush=True)
    answer = input().strip().lower()
    if answer not in ("y", "yes"):
        return {**state, "approved_storyboard": False, "error": "storyboard rejected"}
    return {**state, "approved_storyboard": True}


def node_render(state: GraphState) -> GraphState:
    if state.get("error") or not state.get("approved_storyboard"):
        return state
    project_id = state.get("project_id") or ""
    base = state.get("cineforge_base") or DEFAULT_BASE
    if state.get("dry_run_mode"):
        review = state.get("review") or {}
        shots = review.get("shots") or []
        if not shots:
            payload = state.get("ingest_payload") or {}
            graph = payload.get("shot_graph") or {}
            shots = graph.get("shots") or []
        return {
            **state,
            "render_job": {
                "status": "dry_run",
                "shot_count": len(shots),
                "message": "render skipped — dry_run_mode",
            },
            "error": None,
        }
    try:
        if state.get("preview_mode", True):
            patch_project(project_id, {"preview_mode": True}, base=base)
        job = queue_render(project_id, base=base)
        deadline = time.time() + int(os.environ.get("RENDER_GRAPH_POLL_SEC", "90"))
        while time.time() < deadline:
            project = fetch_project(project_id, base=base)
            shots = project.get("shots") or []
            if shots and all(s.get("status") == "done" for s in shots):
                return {**state, "project": project, "render_job": job, "error": None}
            if any(s.get("status") == "failed" for s in shots):
                return {**state, "error": "one or more shots failed render", "render_job": job, "project": project}
            time.sleep(2)
        return {**state, "error": "render poll timeout", "render_job": job}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": str(exc)}


def node_approve_render(state: GraphState) -> GraphState:
    if state.get("error"):
        return state
    auto = state.get("auto_approve") or os.environ.get("RENDER_GRAPH_AUTO_APPROVE", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if auto or state.get("dry_run_mode"):
        return {**state, "approved_render": True}
    shots = (state.get("project") or {}).get("shots") or []
    done = sum(1 for s in shots if s.get("status") == "done")
    print(f"\n[approve_render] Stitch {done} rendered shot(s)? (y/N): ", end="", flush=True)
    answer = input().strip().lower()
    if answer not in ("y", "yes"):
        return {**state, "approved_render": False, "error": "render rejected"}
    return {**state, "approved_render": True}


def node_stitch(state: GraphState) -> GraphState:
    if state.get("error") or not state.get("approved_render"):
        return state
    project_id = state.get("project_id") or ""
    base = state.get("cineforge_base") or DEFAULT_BASE
    if state.get("dry_run_mode"):
        return {
            **state,
            "stitch_result": {"status": "dry_run", "output_path": None, "message": "stitch skipped"},
            "error": None,
        }
    try:
        result = stitch_project(project_id, base=base)
        return {**state, "stitch_result": result, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": str(exc)}


def node_export(state: GraphState) -> GraphState:
    if state.get("error"):
        return state
    stitch = state.get("stitch_result") or {}
    return {
        **state,
        "export_ready": bool(stitch.get("output_path")) or state.get("dry_run_mode", False),
        "error": None,
    }