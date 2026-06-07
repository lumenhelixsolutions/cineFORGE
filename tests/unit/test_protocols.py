"""Unit tests for adapter protocols and Pydantic models."""
import pytest
from pathlib import Path

from backend.adapters.protocols import (
    VideoCapabilities, VideoGenRequest, VideoGenResult,
    LLMCapabilities, LLMRequest, LLMResponse, LLMUsage,
    ExtendRequest
)


class TestVideoCapabilities:
    def test_basic_instantiation(self):
        caps = VideoCapabilities(
            provider_id="vertex.veo-3.1",
            display_name="Veo 3.1",
            supported_durations_sec=[4, 6, 8],
            supported_aspect_ratios=["16:9", "9:16", "1:1"],
            supported_resolutions=["720p", "1080p"],
            max_reference_images=3,
            supports_native_audio=True,
            supports_frame_conditioning=True,
            supports_extend=True,
            max_extend_total_sec=148,
            supports_negative_prompt=True,
            is_local=False,
            cost_per_second_usd=0.10,
        )
        assert caps.provider_id == "vertex.veo-3.1"
        assert caps.cost_per_second_usd == 0.10

    def test_serialization(self):
        caps = VideoCapabilities(
            provider_id="fal.kling-2.5",
            display_name="Kling 2.5",
            supported_durations_sec=[5, 10],
            supported_aspect_ratios=["16:9", "9:16"],
            supported_resolutions=["720p", "1080p"],
            max_reference_images=1,
            supports_native_audio=False,
            supports_frame_conditioning=True,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=True,
            is_local=False,
            cost_per_second_usd=0.06,
        )
        dumped = caps.model_dump()
        assert dumped["provider_id"] == "fal.kling-2.5"
        assert dumped["max_extend_total_sec"] is None


class TestVideoGenRequest:
    def test_minimal_request(self):
        req = VideoGenRequest(
            prompt="A woman walks through a neon alley",
            duration_sec=6,
            aspect_ratio="16:9",
            resolution="1080p",
        )
        assert req.reference_images == []
        assert req.first_frame is None

    def test_full_request(self):
        req = VideoGenRequest(
            prompt="Close-up of hands typing",
            negative_prompt="no blur, no text",
            duration_sec=8,
            aspect_ratio="9:16",
            resolution="720p",
            reference_images=[Path("/tmp/ref1.jpg")],
            first_frame=Path("/tmp/frame.jpg"),
            seed=42,
        )
        assert len(req.reference_images) == 1
        assert req.seed == 42


class TestLLMUsage:
    def test_cost_calculation(self):
        usage = LLMUsage(
            input_tokens=1000,
            output_tokens=500,
            cached_input_tokens=800,
            cost_usd=0.015,
        )
        assert usage.input_tokens == 1000
        assert usage.cached_input_tokens == 800


class TestExtendRequest:
    def test_defaults(self):
        req = ExtendRequest(source_clip=Path("/tmp/clip.mp4"), prompt="Continue walking")
        assert req.duration_sec == 7

    def test_override_duration(self):
        req = ExtendRequest(source_clip=Path("/tmp/clip.mp4"), prompt="Pan left", duration_sec=4)
        assert req.duration_sec == 4
