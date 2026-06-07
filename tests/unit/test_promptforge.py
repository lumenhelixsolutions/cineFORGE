"""Unit tests for PromptForge prompt generation and validation."""
import pytest
from pathlib import Path

from backend.promptforge.template import PromptForge
from backend.promptforge.continuity import ContinuityBible
from backend.promptforge.validators import PromptValidator
from backend.adapters.protocols import VideoCapabilities


class TestPromptForge:
    def test_basic_prompt_generation(self):
        continuity = ContinuityBible.from_project("test", Path.cwd() / ".pytest_tmp")
        pf = PromptForge(continuity=continuity, style_pack={"name": "cinematic_noir", "palette": "teal and magenta", "film_stock": "35mm"})

        shot = type('Shot', (), {
            'continuity': {"characters": ["alice"], "location": "alley", "time_of_day": "night", "weather": "rain"},
            'summary': "Alice walks through the rain",
            'duration_sec': 6,
            'tier': 'hero',
            'aspect_ratio': '16:9',
        })()

        caps = VideoCapabilities(
            provider_id="vertex.veo-3.1", display_name="Veo 3.1",
            supported_durations_sec=[4, 6, 8], supported_aspect_ratios=["16:9"],
            supported_resolutions=["1080p"], max_reference_images=3,
            supports_native_audio=True, supports_frame_conditioning=True,
            supports_extend=True, max_extend_total_sec=148,
            supports_negative_prompt=True, is_local=False, cost_per_second_usd=0.10,
        )

        prompt = pf.forge(shot, caps)
        assert "[CAMERA]:" in prompt
        assert "[SUBJECT]:" in prompt
        assert "[CONTEXT]:" in prompt
        assert "[LIGHTING]:" in prompt
        assert "[STYLE]:" in prompt
        assert "[AUDIO]:" in prompt
        assert "[NEGATIVE]:" in prompt

    def test_prompt_hash_consistency(self):
        continuity = ContinuityBible.from_project("test", Path.cwd() / ".pytest_tmp")
        pf = PromptForge(continuity=continuity)
        h1 = pf.hash_prompt("Test prompt")
        h2 = pf.hash_prompt("Test prompt")
        assert h1 == h2
        assert h1 != pf.hash_prompt("Different prompt")

    def test_identity_token_resolution(self):
        continuity = ContinuityBible.from_project("test", Path.cwd() / ".pytest_tmp")
        token = continuity.resolve_character("alice")
        assert "30-year-old woman" in token
        assert "silver locket" in token

    def test_location_resolution(self):
        continuity = ContinuityBible.from_project("test", Path.cwd() / ".pytest_tmp")
        loc = continuity.resolve_location("alley")
        assert "rain-slick" in loc
        assert "teal and magenta" in loc


class TestPromptValidator:
    def test_valid_request(self):
        caps = VideoCapabilities(
            provider_id="vertex.veo-3.1", display_name="Veo 3.1",
            supported_durations_sec=[4, 6, 8], supported_aspect_ratios=["16:9"],
            supported_resolutions=["1080p"], max_reference_images=3,
            supports_native_audio=True, supports_frame_conditioning=True,
            supports_extend=True, max_extend_total_sec=148,
            supports_negative_prompt=True, is_local=False, cost_per_second_usd=0.10,
        )
        PromptValidator.validate_against_capabilities(
            prompt="test", duration=6, aspect="16:9", ref_count=0,
            use_frame_bridge=False, use_extend=False, caps=caps,
        )

    def test_invalid_duration(self):
        caps = VideoCapabilities(
            provider_id="fake", display_name="Fake",
            supported_durations_sec=[4, 6], supported_aspect_ratios=["16:9"],
            supported_resolutions=["720p"], max_reference_images=0,
            supports_native_audio=False, supports_frame_conditioning=False,
            supports_extend=False, max_extend_total_sec=None,
            supports_negative_prompt=False, is_local=True, cost_per_second_usd=0.0,
        )
        with pytest.raises(ValueError, match="Duration 8s not in"):
            PromptValidator.validate_against_capabilities(
                prompt="test", duration=8, aspect="16:9", ref_count=0,
                use_frame_bridge=False, use_extend=False, caps=caps,
            )

    def test_frame_bridge_unsupported(self):
        caps = VideoCapabilities(
            provider_id="fake", display_name="Fake",
            supported_durations_sec=[4, 6, 8], supported_aspect_ratios=["16:9"],
            supported_resolutions=["720p"], max_reference_images=0,
            supports_native_audio=False, supports_frame_conditioning=False,
            supports_extend=False, max_extend_total_sec=None,
            supports_negative_prompt=False, is_local=True, cost_per_second_usd=0.0,
        )
        with pytest.raises(ValueError, match="Frame bridge requested but not supported"):
            PromptValidator.validate_against_capabilities(
                prompt="test", duration=6, aspect="16:9", ref_count=0,
                use_frame_bridge=True, use_extend=False, caps=caps,
            )

    def test_prompt_structure_validation(self):
        result = PromptValidator.validate_prompt_structure("[CAMERA]: test [SUBJECT]: test [CONTEXT]: test [LIGHTING]: test [STYLE]: test")
        assert result["valid"] is True

    def test_missing_camera_tag(self):
        result = PromptValidator.validate_prompt_structure("[SUBJECT]: test [CONTEXT]: test")
        assert result["valid"] is False
        assert any("[CAMERA]:" in e for e in result["errors"])
