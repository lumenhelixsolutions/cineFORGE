"""Stage B: Treatment → Shot[] with continuity tags."""
from __future__ import annotations

import json
import logging
from typing import Any, cast

from pydantic import BaseModel

from backend.adapters.protocols import LLMDirector, LLMRequest, LLMUsage, VideoCapabilities

logger = logging.getLogger(__name__)


STORYBOARD_SYSTEMS = {
    "documentary": """You are CineForge Director, a documentary shot list generator.
Expand each beat into 1..N shots (4/6/8s). Prioritize: establishing shots, interview framing, B-roll cutaways, archival inserts, natural lighting.
Use Chain of Draft: every reasoning step must be ≤5 words.
Respect video model capabilities.
Output strict JSON array of shots.
""",
    "explainer": """You are CineForge Director, an educational shot list generator.
Expand each beat into 1..N shots (4/6/8s). Prioritize: title cards, diagram reveals, step visualization, split-screen comparisons, clean backgrounds.
Use Chain of Draft: every reasoning step must be ≤5 words.
Respect video model capabilities.
Output strict JSON array of shots.
""",
    "archival": """You are CineForge Director, a historical shot list generator.
Expand each beat into 1..N shots (4/6/8s). Prioritize: period-appropriate framing, slow pans over documents, sepia grading, narrator-driven pacing.
Use Chain of Draft: every reasoning step must be ≤5 words.
Respect video model capabilities.
Output strict JSON array of shots.
""",
    "news": """You are CineForge Director, a news shot list generator.
Expand each beat into 1..N shots (4/6s). Prioritize: urgency, on-screen text, location identifiers, witness footage style, tight deadlines.
Use Chain of Draft: every reasoning step must be ≤5 words.
Respect video model capabilities.
Output strict JSON array of shots.
""",
    "research": """You are CineForge Director, a science shot list generator.
Expand each beat into 1..N shots (4/6/8s). Prioritize: equation close-ups, graph animations, lab footage, before/after comparisons, citation overlays.
Use Chain of Draft: every reasoning step must be ≤5 words.
Respect video model capabilities.
Output strict JSON array of shots.
""",
    "cinematic": """You are CineForge Director, a cinematic shot list generator.
Expand each beat into 1..N shots (4/6/8s). Prioritize: dramatic lighting, camera movement, emotional close-ups, wide establishing, continuity.
Use Chain of Draft: every reasoning step must be ≤5 words.
Respect video model capabilities.
Output strict JSON array of shots.
""",
}

DEFAULT_STORYBOARD_SYSTEM = STORYBOARD_SYSTEMS["documentary"]

SHOT_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "order_index": {"type": "integer"},
            "duration_sec": {"type": "integer", "enum": [4, 6, 8]},
            "tier": {"type": "string", "enum": ["hero", "standard", "broll", "title"]},
            "summary": {"type": "string", "maxLength": 200},
            "continuity": {
                "type": "object",
                "properties": {
                    "characters": {"type": "array", "items": {"type": "string"}},
                    "location": {"type": "string"},
                    "time_of_day": {"type": "string"},
                    "props": {"type": "array", "items": {"type": "string"}}
                }
            },
            "bridge_strategy": {"type": "string", "enum": ["hard_cut", "match_cut", "frame_bridge", "extend"]},
            "preferred_bridge": {"type": "string", "enum": ["hard_cut", "match_cut", "frame_bridge", "extend"]},
            "camera": {"type": "string", "maxLength": 100},
            "lighting": {"type": "string", "maxLength": 100},
            "audio_hint": {"type": "string", "maxLength": 60},
        },
        "required": ["id", "order_index", "duration_sec", "tier", "summary", "bridge_strategy", "preferred_bridge"]
    }
}


async def generate_storyboard(
    llm: LLMDirector,
    treatment: dict[str, Any],
    capabilities: VideoCapabilities,
    style_pack: dict[str, Any] | None,
    topic: str = "documentary",
) -> tuple[list[dict[str, Any]], LLMUsage]:
    """Expand treatment beats into shots, respecting capabilities."""
    caps_text = _format_capabilities(capabilities)
    style_hint = f"Style pack: {style_pack.get('name', 'default')}" if style_pack else ""

    system_prompt = STORYBOARD_SYSTEMS.get(topic, DEFAULT_STORYBOARD_SYSTEM)
    user_msg = f"""Treatment:
{json.dumps(treatment, indent=2)}

Video model capabilities:
{caps_text}

{style_hint}

Generate the shot list JSON now."""

    req = LLMRequest(
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
        response_schema=SHOT_SCHEMA,
        temperature=0.7,
        max_tokens=8192,
    )

    resp = await llm.complete(req)
    shots = resp.content if isinstance(resp.content, list) else json.loads(cast(str, resp.content))

    # Post-process: enforce capability constraints
    shots = _enforce_capabilities(shots, capabilities)
    return shots, resp.usage


def _format_capabilities(caps: VideoCapabilities) -> str:
    lines = [
        f"Provider: {caps.display_name}",
        f"Durations: {caps.supported_durations_sec}",
        f"Aspect ratios: {caps.supported_aspect_ratios}",
        f"Max refs: {caps.max_reference_images}",
        f"Native audio: {caps.supports_native_audio}",
        f"Frame conditioning: {caps.supports_frame_conditioning}",
        f"Extend: {caps.supports_extend} (max {caps.max_extend_total_sec}s)",
    ]
    return "\n".join(lines)


def _enforce_capabilities(shots: list[dict[str, Any]], caps: VideoCapabilities) -> list[dict[str, Any]]:
    """Hard-enforce capability constraints on generated shots."""
    valid_durations = set(caps.supported_durations_sec)
    for s in shots:
        preferred_bridge = s.get("preferred_bridge", s.get("bridge_strategy", "hard_cut"))
        s["preferred_bridge"] = preferred_bridge

        # Restore original intent when the current target now supports it
        if preferred_bridge == "frame_bridge" and caps.supports_frame_conditioning:
            s["bridge_strategy"] = "frame_bridge"
        if preferred_bridge == "extend" and caps.supports_extend:
            s["bridge_strategy"] = "extend"

        if s["duration_sec"] not in valid_durations:
            s["duration_sec"] = min(valid_durations, key=lambda d: abs(d - s["duration_sec"]))
        # Bridge strategy fallback
        if s["bridge_strategy"] == "frame_bridge" and not caps.supports_frame_conditioning:
            s["bridge_strategy"] = "match_cut" if preferred_bridge == "frame_bridge" else preferred_bridge
        if s["bridge_strategy"] == "extend" and not caps.supports_extend:
            s["bridge_strategy"] = "match_cut" if preferred_bridge == "extend" else preferred_bridge
        if s["bridge_strategy"] not in {"hard_cut", "match_cut", "frame_bridge", "extend"}:
            s["bridge_strategy"] = "hard_cut"
        # Prompt hash computed by PromptForge after forging
        s["prompt_hash"] = ""
        s["prompt_text"] = ""
        s["ref_image_paths"] = []
    return shots
