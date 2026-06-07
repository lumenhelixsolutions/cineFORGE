"""Capability honesty test: Director must never emit unsupported bridge strategies.

DoD #11: A unit test instantiates a fake VideoModel with
supports_frame_conditioning=False and supports_extend=False, runs the Director,
and asserts no shot has bridge_strategy in {frame_bridge, extend}.
"""
import pytest
from unittest.mock import AsyncMock

from backend.adapters.protocols import VideoCapabilities, LLMDirector, LLMCapabilities, LLMRequest, LLMResponse, LLMUsage
from backend.director.storyboard import generate_storyboard


class FakeNoFrameNoExtendCapabilities:
    """A video model that supports neither frame conditioning nor extend."""
    capabilities = VideoCapabilities(
        provider_id="fake.limited",
        display_name="Limited Model",
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
        # Return shots that *try* to use frame_bridge and extend
        return LLMResponse(
            content=[
                {
                    "id": "s1", "order_index": 0, "duration_sec": 6, "tier": "hero",
                    "summary": "Shot 1", "bridge_strategy": "frame_bridge",
                    "preferred_bridge": "frame_bridge", "continuity": {},
                },
                {
                    "id": "s2", "order_index": 1, "duration_sec": 8, "tier": "standard",
                    "summary": "Shot 2", "bridge_strategy": "extend",
                    "preferred_bridge": "extend", "continuity": {},
                },
                {
                    "id": "s3", "order_index": 2, "duration_sec": 4, "tier": "broll",
                    "summary": "Shot 3", "bridge_strategy": "hard_cut",
                    "preferred_bridge": "hard_cut", "continuity": {},
                },
            ],
            usage=LLMUsage(input_tokens=100, output_tokens=50, cost_usd=0.0),
            provider_id="fake.llm",
        )

    async def healthcheck(self) -> bool:
        return True


@pytest.mark.asyncio
class TestCapabilityHonesty:
    async def test_no_frame_bridge_when_unsupported(self):
        llm = FakeLLM()
        treatment = {
            "logline": "Test",
            "acts": [{"title": "Act 1", "beats": [{"id": "b1", "summary": "Beat", "target_duration_sec": 6, "emotional_register": "wonder"}]}],
        }
        shots, _ = await generate_storyboard(
            llm=llm,
            treatment=treatment,
            capabilities=FakeNoFrameNoExtendCapabilities.capabilities,
            style_pack=None,
        )
        for shot in shots:
            assert shot["bridge_strategy"] != "frame_bridge",                 f"Shot {shot['id']} illegally uses frame_bridge when unsupported"

    async def test_no_extend_when_unsupported(self):
        llm = FakeLLM()
        treatment = {
            "logline": "Test",
            "acts": [{"title": "Act 1", "beats": [{"id": "b1", "summary": "Beat", "target_duration_sec": 6, "emotional_register": "wonder"}]}],
        }
        shots, _ = await generate_storyboard(
            llm=llm,
            treatment=treatment,
            capabilities=FakeNoFrameNoExtendCapabilities.capabilities,
            style_pack=None,
        )
        for shot in shots:
            assert shot["bridge_strategy"] != "extend",                 f"Shot {shot['id']} illegally uses extend when unsupported"

    async def test_preferred_bridge_preserved_for_retargting(self):
        """preferred_bridge must retain the original intent for later re-targeting."""
        llm = FakeLLM()
        treatment = {
            "logline": "Test",
            "acts": [{"title": "Act 1", "beats": [{"id": "b1", "summary": "Beat", "target_duration_sec": 6, "emotional_register": "wonder"}]}],
        }
        shots, _ = await generate_storyboard(
            llm=llm,
            treatment=treatment,
            capabilities=FakeNoFrameNoExtendCapabilities.capabilities,
            style_pack=None,
        )
        # The first shot preferred frame_bridge, second preferred extend
        assert shots[0]["preferred_bridge"] == "frame_bridge"
        assert shots[1]["preferred_bridge"] == "extend"
