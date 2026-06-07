"""Opt-in telemetry for CineForge production insights.

Session tracking: render success/failure, token usage, adapter popularity.
Cost aggregation per provider.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TELEMETRY_DIR = Path.home() / ".cineforge" / "telemetry"
_SESSION_FILE: Path | None = None
_BUFFER: list[dict[str, Any]] = []


def _enabled() -> bool:
    return os.getenv("CINEFORGE_TELEMETRY", "0") == "1"


def _ensure_session() -> None:
    global _SESSION_FILE
    if _SESSION_FILE is None:
        _TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        _SESSION_FILE = _TELEMETRY_DIR / f"session_{ts}.jsonl"


def _write(event: dict[str, Any]) -> None:
    if not _enabled():
        return
    _ensure_session()
    event["_ts"] = datetime.now(timezone.utc).isoformat()
    _BUFFER.append(event)
    if _SESSION_FILE is not None:
        with open(_SESSION_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")


def log_render_event(
    shot_id: str,
    provider_id: str,
    success: bool,
    duration_sec: float,
    cost_usd: float,
    error: str | None = None,
) -> None:
    """Log a render attempt outcome."""
    _write(
        {
            "event": "render",
            "shot_id": shot_id,
            "provider_id": provider_id,
            "success": success,
            "duration_sec": duration_sec,
            "cost_usd": cost_usd,
            "error": error,
        }
    )


def log_adapter_use(adapter_kind: str, provider_id: str, task: str) -> None:
    """Log adapter retrieval/invocation."""
    _write(
        {
            "event": "adapter_use",
            "adapter_kind": adapter_kind,
            "provider_id": provider_id,
            "task": task,
        }
    )


def log_stitch_event(
    project_id: str,
    shot_count: int,
    output_path: str,
    duration_sec: float,
) -> None:
    """Log a stitch operation."""
    _write(
        {
            "event": "stitch",
            "project_id": project_id,
            "shot_count": shot_count,
            "output_path": output_path,
            "duration_sec": duration_sec,
        }
    )


def session_summary() -> dict[str, Any]:
    """Aggregate current session stats from in-memory buffer."""
    renders = [e for e in _BUFFER if e.get("event") == "render"]
    adapters = [e for e in _BUFFER if e.get("event") == "adapter_use"]
    stitches = [e for e in _BUFFER if e.get("event") == "stitch"]

    provider_cost: dict[str, float] = {}
    provider_renders: dict[str, int] = {}
    for r in renders:
        pid = r.get("provider_id", "unknown")
        provider_cost[pid] = provider_cost.get(pid, 0.0) + r.get("cost_usd", 0.0)
        provider_renders[pid] = provider_renders.get(pid, 0) + 1

    return {
        "session_file": str(_SESSION_FILE) if _SESSION_FILE else None,
        "render_count": len(renders),
        "render_successes": sum(1 for r in renders if r.get("success")),
        "render_failures": sum(1 for r in renders if not r.get("success")),
        "total_cost_usd": sum(r.get("cost_usd", 0.0) for r in renders),
        "provider_cost": provider_cost,
        "provider_renders": provider_renders,
        "adapter_uses": len(adapters),
        "stitch_count": len(stitches),
    }
