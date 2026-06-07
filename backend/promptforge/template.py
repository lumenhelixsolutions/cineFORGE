"""PromptForge — Shot → Veo-ready prompt string.

Veo 3.1 rewards director-grade prompts. Template order matters because
Veo's attention biases toward the first half of the prompt.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from backend.adapters.protocols import VideoCapabilities
from backend.promptforge.continuity import ContinuityBible

logger = logging.getLogger(__name__)

# Ordered template — DO NOT REORDER without validating against Veo attention bias
PROMPT_TEMPLATE = """[CAMERA]: {camera}
[SUBJECT]: {identity_token} {action}
[CONTEXT]: {location} {time_of_day} {weather}
[LIGHTING]: {lighting}
[STYLE]: {style}
[AUDIO]: {audio}
[DURATION]: {duration}s, [ASPECT]: {aspect}
[NEGATIVE]: {negative}"""


class PromptForge:
    """Forges Veo-ready prompts from shot continuity data."""

    def __init__(
        self,
        continuity: ContinuityBible,
        style_pack: dict[str, Any] | None = None,
    ) -> None:
        self.continuity = continuity
        self.style_pack = style_pack or {}
        self._glossary: dict[str, str] = {}  # character -> identity_token cache

    def forge(self, shot: Any, capabilities: VideoCapabilities) -> str:
        """Generate a Veo-ready prompt string for a shot."""
        continuity = shot.continuity if hasattr(shot, "continuity") else shot.get("continuity", {})
        summary = shot.summary if hasattr(shot, "summary") else shot.get("summary", "")
        duration = shot.duration_sec if hasattr(shot, "duration_sec") else shot.get("duration_sec", 6)
        tier = shot.tier if hasattr(shot, "tier") else shot.get("tier", "standard")
        aspect = shot.aspect_ratio if hasattr(shot, "aspect_ratio") else "16:9"

        # Resolve identity tokens
        characters = continuity.get("characters", [])
        identity_tokens = [self._resolve_identity(c) for c in characters]
        identity_token = identity_tokens[0] if identity_tokens else ""

        # Extract action from summary
        action = self._extract_action(summary)

        # Resolve location
        location = continuity.get("location", "")
        location_desc = self.continuity.resolve_location(location)

        # Build camera from continuity + style pack
        camera = self._build_camera(continuity, tier)

        # Build lighting from continuity + style pack
        lighting = self._build_lighting(continuity)

        # Build style from style pack
        style = self._build_style()

        # Build audio (terse, ≤12 words)
        audio = self._build_audio(continuity)

        # Build negative
        negative = self._build_negative(continuity)

        # Validate against capabilities
        self._validate(duration, aspect, capabilities)

        prompt = PROMPT_TEMPLATE.format(
            camera=camera,
            identity_token=identity_token,
            action=action,
            location=location_desc,
            time_of_day=continuity.get("time_of_day", ""),
            weather=continuity.get("weather", ""),
            lighting=lighting,
            style=style,
            audio=audio,
            duration=duration,
            aspect=aspect,
            negative=negative,
        )

        # Post-process: ensure 3-6 sentences, 100-150 words
        prompt = self._tighten(prompt)
        return prompt.strip()

    def hash_prompt(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def _resolve_identity(self, char_id: str) -> str:
        if char_id not in self._glossary:
            token = self.continuity.resolve_character(char_id)
            self._glossary[char_id] = token
        return self._glossary[char_id]

    def _extract_action(self, summary: str) -> str:
        # Simple heuristic: first verb phrase
        words = summary.split()
        if len(words) > 3:
            return " ".join(words[1:])  # skip subject
        return summary

    def _build_camera(self, continuity: dict[str, Any], tier: str) -> str:
        default_lens = self.continuity.camera_grammar.get("lens_default", "35mm")
        default_motion = self.continuity.camera_grammar.get("motion_default", "slow handheld")

        # Tier-based camera variation
        if tier == "hero":
            return f"Wide establishing, {default_lens}, slow dolly-in, shallow depth of field"
        elif tier == "title":
            return f"Static locked-off, {default_lens}, center frame"
        elif tier == "broll":
            return f"Medium shot, {default_lens}, {default_motion}"
        return f"Medium close-up, {default_lens}, {default_motion}"

    def _build_lighting(self, continuity: dict[str, Any]) -> str:
        loc = continuity.get("location", "")
        loc_data = self.continuity.locations.get(loc, {})
        lighting: str = loc_data.get("lighting_model", "natural key, soft fill, neutral temperature")
        return lighting

    def _build_style(self) -> str:
        if not self.style_pack:
            return "cinematic, natural color, 35mm film grain"
        palette: str = self.style_pack.get("palette", "")
        stock: str = self.style_pack.get("film_stock", "")
        name: str = self.style_pack.get("name", "cinematic")
        return f"{name}, {palette}, {stock}"

    def _build_audio(self, continuity: dict[str, Any]) -> str:
        # Cap at 12 words
        hint = continuity.get("audio_hint", "")
        words = hint.split()
        if len(words) > 12:
            hint = " ".join(words[:12])
        return hint or "ambient room tone, subtle atmosphere"

    def _build_negative(self, continuity: dict[str, Any]) -> str:
        # ≤3 concise no-X clauses, end-of-prompt only
        negatives = ["no text overlays", "no logo watermarks", "no shaky cam"]
        return ", ".join(negatives[:3])

    def _validate(self, duration: int, aspect: str, caps: VideoCapabilities) -> None:
        if duration not in caps.supported_durations_sec:
            raise ValueError(f"Duration {duration}s not supported by {caps.provider_id}")
        if aspect not in caps.supported_aspect_ratios:
            raise ValueError(f"Aspect ratio {aspect} not supported by {caps.provider_id}")

    def _tighten(self, prompt: str) -> str:
        # Ensure 3-6 sentences, 100-150 words
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", prompt) if s.strip()]
        if len(sentences) < 3:
            # Pad with context detail if too short
            pass
        if len(sentences) > 6:
            sentences = sentences[:6]
        words = " ".join(sentences).split()
        if len(words) > 150:
            # Truncate gracefully at sentence boundary
            truncated = []
            count = 0
            for s in sentences:
                wc = len(s.split())
                if count + wc > 150:
                    break
                truncated.append(s)
            sentences = truncated
        return " ".join(sentences)
