"""PromptForge validators — enforce capability constraints before API call."""

from __future__ import annotations

import logging
from typing import Any

from backend.adapters.protocols import VideoCapabilities

logger = logging.getLogger(__name__)


class PromptValidator:
    """Validates a forged prompt against VideoCapabilities."""

    @staticmethod
    def validate_against_capabilities(
        prompt: str,
        duration: int,
        aspect: str,
        ref_count: int,
        use_frame_bridge: bool,
        use_extend: bool,
        caps: VideoCapabilities,
    ) -> None:
        errors = []
        if duration not in caps.supported_durations_sec:
            errors.append(f"Duration {duration}s not in {caps.supported_durations_sec}")
        if aspect not in caps.supported_aspect_ratios:
            errors.append(f"Aspect {aspect} not in {caps.supported_aspect_ratios}")
        if ref_count > caps.max_reference_images:
            errors.append(f"Refs {ref_count} > max {caps.max_reference_images}")
        if use_frame_bridge and not caps.supports_frame_conditioning:
            errors.append("Frame bridge requested but not supported")
        if use_extend and not caps.supports_extend:
            errors.append("Extend requested but not supported")
        if errors:
            raise ValueError("; ".join(errors))

    @staticmethod
    def validate_prompt_structure(prompt: str) -> dict[str, Any]:
        """Check prompt follows template structure."""
        result: dict[str, Any] = {"valid": True, "errors": []}
        required_tags = ["[CAMERA]:", "[SUBJECT]:", "[CONTEXT]:", "[LIGHTING]:", "[STYLE]:"]
        for tag in required_tags:
            if tag not in prompt:
                result["valid"] = False
                result["errors"].append(f"Missing required tag: {tag}")
        # Check audio word count
        audio_match = __import__("re").search(r"\[AUDIO\]: (.+)", prompt)
        if audio_match:
            words = audio_match.group(1).split()
            if len(words) > 12:
                result["valid"] = False
                result["errors"].append(f"Audio cue too long: {len(words)} words (max 12)")
        # Check negative is at end
        neg_idx = prompt.find("[NEGATIVE]:")
        if neg_idx != -1 and neg_idx < len(prompt) - 200:
            result["warnings"] = ["Negative prompt may not be at end of prompt"]
        return result
