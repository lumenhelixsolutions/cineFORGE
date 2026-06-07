"""Stage A: SourceDoc → Treatment (3-act, beat-level)."""
from __future__ import annotations

import json
import logging
from typing import Any, cast

from pydantic import BaseModel

from backend.adapters.protocols import LLMDirector, LLMRequest, LLMUsage

logger = logging.getLogger(__name__)


class Beat(BaseModel):
    id: str
    summary: str
    target_duration_sec: int
    emotional_register: str


class Act(BaseModel):
    title: str
    beats: list[Beat]


class TreatmentOutput(BaseModel):
    logline: str
    theme: str
    tone: str
    acts: list[Act]
    style_pack_suggestion: str


TREATMENT_SYSTEMS = {
    "documentary": """You are CineForge Director, a documentary filmmaker.
Write a 3-act documentary treatment from the source material.
Focus on: factual accuracy, interview subjects, B-roll opportunities, archival footage needs.
Use Chain of Draft: every reasoning step must be ≤5 words.
Output strict JSON matching the provided schema.
""",
    "explainer": """You are CineForge Director, an educational content producer.
Write a 3-act explainer treatment from the source material.
Focus on: concept hierarchy, visual metaphors, step-by-step reveal, call-to-action.
Use Chain of Draft: every reasoning step must be ≤5 words.
Output strict JSON matching the provided schema.
""",
    "archival": """You are CineForge Director, a historical documentarian.
Write a 3-act archival treatment from the source material.
Focus on: period authenticity, primary sources, narrator voice, emotional through-line.
Use Chain of Draft: every reasoning step must be ≤5 words.
Output strict JSON matching the provided schema.
""",
    "news": """You are CineForge Director, a news producer.
Write an inverted-pyramid treatment (hook→context→details→impact).
Focus on: immediacy, source attribution, visual evidence, audience relevance.
Use Chain of Draft: every reasoning step must be ≤5 words.
Output strict JSON matching the provided schema.
""",
    "research": """You are CineForge Director, a science communicator.
Write a 3-act research walkthrough from the source material.
Focus on: hypothesis, methodology visualization, result reveal, implication.
Use Chain of Draft: every reasoning step must be ≤5 words.
Output strict JSON matching the provided schema.
""",
    "cinematic": """You are CineForge Director, a cinematic treatment writer.
Write a 3-act cinematic treatment from the source material.
Focus on: visual spectacle, emotional arc, character development, set pieces.
Use Chain of Draft: every reasoning step must be ≤5 words.
Output strict JSON matching the provided schema.
""",
}

DEFAULT_TREATMENT_SYSTEM = TREATMENT_SYSTEMS["documentary"]

TREATMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "logline": {"type": "string", "maxLength": 200},
        "theme": {"type": "string", "maxLength": 80},
        "tone": {"type": "string", "maxLength": 80},
        "acts": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "beats": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "summary": {"type": "string", "maxLength": 140},
                                "target_duration_sec": {"type": "integer", "enum": [4, 6, 8, 16, 24]},
                                "emotional_register": {"type": "string", "enum": ["calm","tense","wonder","grief","triumph","comic","stark","intimate"]}
                            },
                            "required": ["id", "summary", "target_duration_sec", "emotional_register"]
                        }
                    }
                },
                "required": ["title", "beats"]
            }
        },
        "style_pack_suggestion": {"type": "string"}
    },
    "required": ["logline", "theme", "tone", "acts", "style_pack_suggestion"]
}


async def generate_treatment(
    llm: LLMDirector,
    source_text: str,
    style_pack: dict[str, Any] | None,
    target_duration: int,
    topic: str = "documentary",
) -> tuple[dict[str, Any], LLMUsage]:
    """Generate a 3-act treatment from source text."""
    style_hint = f"Suggested style: {style_pack.get('name', 'cinematic_noir')}" if style_pack else ""
    user_msg = f"""Source material (first 8000 chars):
{source_text[:8000]}

Target total duration: {target_duration}s.
{style_hint}

Write the treatment JSON now."""

    system_prompt = TREATMENT_SYSTEMS.get(topic, DEFAULT_TREATMENT_SYSTEM)
    req = LLMRequest(
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
        response_schema=TREATMENT_SCHEMA,
        temperature=0.7,
        max_tokens=4096,
    )

    resp = await llm.complete(req)
    content = resp.content if isinstance(resp.content, dict) else json.loads(cast(str, resp.content))
    return content, resp.usage
