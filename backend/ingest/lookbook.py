"""lookBOOK shot_graph.json → CineForge storyboard shot records."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


LOOKBOOK_SCHEMA = "lookbook.shot_graph.v0.3"
VALID_DURATIONS = (4, 6, 8)
BRIDGE_MAP = {
    "cut": "hard_cut",
    "hard_cut": "hard_cut",
    "match_cut": "match_cut",
    "fade": "hard_cut",
    "dissolve": "match_cut",
}


def _snap_duration(seconds: float) -> int:
    target = max(4, min(8, round(seconds) or 4))
    return min(VALID_DURATIONS, key=lambda d: abs(d - target))


def _build_prompt(shot: dict[str, Any]) -> str:
    parts: list[str] = []
    shot_type = shot.get("type", "establishing")
    camera = shot.get("camera", "static")
    motion = shot.get("motion_directive", "").strip()
    parts.append(f"{shot_type} shot, camera: {camera}.")
    if motion:
        parts.append(motion)
    dialogue = shot.get("dialogue") or []
    if dialogue:
        parts.append("Dialogue: " + " ".join(str(d) for d in dialogue))
    return " ".join(parts).strip()[:2000]


def lookbook_shot_to_cineforge(shot: dict[str, Any], order_index: int) -> dict[str, Any]:
    """Map one lookBOOK shot dict to CineForge shot persistence shape."""
    prompt = _build_prompt(shot)
    transition = BRIDGE_MAP.get(str(shot.get("transition_in", "cut")).lower(), "hard_cut")
    narration_parts = shot.get("narration") or []
    narration = " ".join(str(n) for n in narration_parts).strip() or None
    characters = [str(c) for c in (shot.get("characters") or [])]
    return {
        "order_index": order_index,
        "duration_sec": _snap_duration(float(shot.get("duration_seconds", 4))),
        "tier": "hero" if shot.get("type") == "establishing" else "standard",
        "continuity": {
            "characters": characters,
            "location": f"scene_{shot.get('scene_index', 0)}",
            "props": [str(p) for p in (shot.get("panels") or [])],
        },
        "prompt_text": prompt,
        "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
        "bridge_strategy": transition,
        "preferred_bridge": transition,
        "ref_image_paths": [],
        "narration": narration,
        "transition_in": transition,
        "status": "draft",
        "source": {
            "provider": "lookbook",
            "shot_index": shot.get("shot_index", order_index),
            "schema": LOOKBOOK_SCHEMA,
        },
    }


def parse_lookbook_shot_graph(payload: dict[str, Any] | str | Path) -> dict[str, Any]:
    """Load and validate a lookBOOK shot graph payload."""
    if isinstance(payload, Path):
        data = json.loads(payload.read_text(encoding="utf-8"))
    elif isinstance(payload, str):
        data = json.loads(payload)
    else:
        data = payload
    if not isinstance(data, dict):
        raise ValueError("lookBOOK shot graph must be a JSON object")
    shots = data.get("shots")
    if not isinstance(shots, list) or not shots:
        raise ValueError("lookBOOK shot graph must contain a non-empty shots array")
    schema = data.get("schema") or data.get("schema_version") or ""
    if schema and LOOKBOOK_SCHEMA not in str(schema):
        raise ValueError(f"Unsupported lookBOOK schema: {schema}")
    return data


def convert_lookbook_to_shots(payload: dict[str, Any] | str | Path) -> list[dict[str, Any]]:
    """Convert a full lookBOOK shot_graph to CineForge shot dicts."""
    data = parse_lookbook_shot_graph(payload)
    return [
        lookbook_shot_to_cineforge(shot, idx)
        for idx, shot in enumerate(data["shots"])
        if isinstance(shot, dict)
    ]


def build_treatment_from_lookbook(payload: dict[str, Any]) -> dict[str, Any]:
    """Minimal treatment stub so ingested projects have narrative context."""
    data = parse_lookbook_shot_graph(payload)
    beats = []
    for shot in data["shots"]:
        if not isinstance(shot, dict):
            continue
        beats.append({
            "title": f"Shot {shot.get('shot_index', len(beats))}",
            "summary": _build_prompt(shot)[:200],
            "duration_sec": _snap_duration(float(shot.get("duration_seconds", 4))),
        })
    return {
        "title": "lookBOOK import",
        "logline": f"Imported {len(beats)} shots from lookBOOK shot graph.",
        "acts": [{"act_number": 1, "beats": beats}],
        "source": "lookbook",
        "schema": data.get("schema") or LOOKBOOK_SCHEMA,
    }