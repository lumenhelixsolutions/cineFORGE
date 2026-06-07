"""Unit tests for Director treatment and storyboard generation."""
import json
import pytest
from unittest.mock import AsyncMock

from backend.adapters.protocols import (
    LLMDirector, LLMCapabilities, LLMRequest, LLMResponse, LLMUsage,
    VideoCapabilities
)
from backend.director.treatment import generate_treatment, TREATMENT_SCHEMA
from backend.director.storyboard import generate_storyboard, _enforce_capabilities


class FakeLLM:
    capabilities = LLMCapabilities(
        provider_id="fake.llm",
        display_name="Fake LLM",
        context_window=128000,
        supports_prompt_caching=True,
        supports_structured_output=True,
        supports_tool_use=True,
        is_local=True,
        cost_per_1k_input_usd=0.0,
        cost_per_1k_output_usd=0.0,
        cost_per_1k_cached_input_usd=0.0,
    )

    async def complete(self, req: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content={
                "logline": "A woman discovers a hidden message in an old film reel.",
                "theme": "Memory and loss",
                "tone": "Melancholic noir",
                "acts": [
                    {
                        "title": "Discovery",
                        "beats": [
                            {"id": "b1", "summary": "Finds reel in attic", "target_duration_sec": 6, "emotional_register": "wonder"},
                            {"id": "b2", "summary": "Plays first frame", "target_duration_sec": 4, "emotional_register": "tense"},
                        ]
                    },
                    {
                        "title": "Descent",
                        "beats": [
                            {"id": "b3", "summary": "Image distorts", "target_duration_sec": 8, "emotional_register": "grief"},
                        ]
                    },
                    {
                        "title": "Revelation",
                        "beats": [
                            {"id": "b4", "summary": "Faces truth", "target_duration_sec": 6, "emotional_register": "triumph"},
                        ]
                    },
                ],
                "style_pack_suggestion": "cinematic_noir",
            },
            usage=LLMUsage(input_tokens=500, output_tokens=300, cost_usd=0.0),
            provider_id="fake.llm",
        )

    async def healthcheck(self) -> bool:
        return True


@pytest.mark.asyncio
class TestTreatment:
    async def test_generate_treatment_structure(self):
        llm = FakeLLM()
        treatment, usage = await generate_treatment(
            llm=llm,
            source_text="A woman finds an old film reel in her grandmother's attic.",
            style_pack=None,
            target_duration=60,
        )
        assert "logline" in treatment
        assert "acts" in treatment
        assert len(treatment["acts"]) == 3
        assert all("beats" in act for act in treatment["acts"])
        assert usage.input_tokens == 500

    async def test_treatment_respects_target_duration(self):
        llm = FakeLLM()
        treatment, _ = await generate_treatment(
            llm=llm,
            source_text="Short text.",
            style_pack=None,
            target_duration=30,
        )
        total = sum(
            beat["target_duration_sec"]
            for act in treatment["acts"]
            for beat in act["beats"]
        )
        # Should be roughly in range (allowing flexibility)
        assert 10 <= total <= 40


@pytest.mark.asyncio
class TestStoryboard:
    async def test_generate_storyboard(self):
        llm = FakeLLM()
        # Override to return shots
        llm.complete = AsyncMock(return_value=LLMResponse(
            content=[
                {
                    "id": "s1", "order_index": 0, "duration_sec": 6, "tier": "hero",
                    "summary": "Attic wide shot", "bridge_strategy": "hard_cut",
                    "preferred_bridge": "frame_bridge", "continuity": {"characters": ["alice"], "location": "attic"},
                },
                {
                    "id": "s2", "order_index": 1, "duration_sec": 4, "tier": "standard",
                    "summary": "Close-up of reel", "bridge_strategy": "frame_bridge",
                    "preferred_bridge": "frame_bridge", "continuity": {"characters": ["alice"], "location": "attic"},
                },
            ],
            usage=LLMUsage(input_tokens=800, output_tokens=400, cost_usd=0.0),
            provider_id="fake.llm",
        ))

        caps = VideoCapabilities(
            provider_id="vertex.veo-3.1",
            display_name="Veo 3.1",
            supported_durations_sec=[4, 6, 8],
            supported_aspect_ratios=["16:9"],
            supported_resolutions=["1080p"],
            max_reference_images=3,
            supports_native_audio=True,
            supports_frame_conditioning=True,
            supports_extend=True,
            max_extend_total_sec=148,
            supports_negative_prompt=True,
            is_local=False,
            cost_per_second_usd=0.10,
        )

        treatment = {
            "logline": "Test",
            "acts": [{"title": "Act 1", "beats": [{"id": "b1", "summary": "Test beat", "target_duration_sec": 6, "emotional_register": "wonder"}]}],
        }

        shots, usage = await generate_storyboard(llm=llm, treatment=treatment, capabilities=caps, style_pack=None)
        assert len(shots) == 2
        assert shots[0]["order_index"] == 0
        assert shots[1]["order_index"] == 1

    def test_enforce_capabilities_frame_bridge_fallback(self):
        shots = [
            {"duration_sec": 10, "bridge_strategy": "frame_bridge", "preferred_bridge": "frame_bridge"},
        ]
        caps = VideoCapabilities(
            provider_id="fake.no-frame",
            display_name="No Frame",
            supported_durations_sec=[4, 6, 8],
            supported_aspect_ratios=["16:9"],
            supported_resolutions=["720p"],
            max_reference_images=0,
            supports_native_audio=False,
            supports_frame_conditioning=False,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=False,
            is_local=True,
            cost_per_second_usd=0.0,
        )
        result = _enforce_capabilities(shots, caps)
        assert result[0]["bridge_strategy"] == "match_cut"

    def test_enforce_capabilities_duration_clamping(self):
        shots = [{"duration_sec": 10, "bridge_strategy": "hard_cut", "preferred_bridge": "hard_cut"}]
        caps = VideoCapabilities(
            provider_id="fake", display_name="Fake",
            supported_durations_sec=[4, 6, 8],
            supported_aspect_ratios=["16:9"],
            supported_resolutions=["720p"],
            max_reference_images=0,
            supports_native_audio=False,
            supports_frame_conditioning=False,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=False,
            is_local=True,
            cost_per_second_usd=0.0,
        )
        result = _enforce_capabilities(shots, caps)
        assert result[0]["duration_sec"] == 8  # closest valid duration
