"""Adapter swap test: switching providers without restart or storyboard regeneration.

DoD #12: Switching active video provider via UI or routing.yaml hot-reload
must not require restart or re-generating storyboard. Director re-evaluates
bridge_strategy against new capabilities and emits a diff.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.adapters.protocols import VideoCapabilities, VideoModel
from backend.director.storyboard import _enforce_capabilities


class FakeVeoAdapter:
    capabilities = VideoCapabilities(
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


class FakeKlingAdapter:
    capabilities = VideoCapabilities(
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


class TestAdapterSwap:
    def test_swap_veo_to_kling_re_evaluates_bridge(self):
        """When swapping from Veo (supports extend) to Kling (no extend),
        bridge_strategy 'extend' must fallback to match_cut."""
        shots = [
            {
                "duration_sec": 8,
                "bridge_strategy": "extend",
                "preferred_bridge": "extend",
            }
        ]
        # First with Veo
        veo_result = _enforce_capabilities(shots, FakeVeoAdapter.capabilities)
        assert veo_result[0]["bridge_strategy"] == "extend"

        # Then swap to Kling (no extend support)
        kling_result = _enforce_capabilities(shots, FakeKlingAdapter.capabilities)
        assert kling_result[0]["bridge_strategy"] != "extend"
        assert kling_result[0]["bridge_strategy"] in {"hard_cut", "match_cut"}

    def test_swap_veo_to_kling_duration_clamping(self):
        """Kling only supports 5s and 10s; 8s shots must clamp to nearest valid."""
        shots = [{"duration_sec": 8, "bridge_strategy": "hard_cut", "preferred_bridge": "hard_cut"}]
        kling_result = _enforce_capabilities(shots, FakeKlingAdapter.capabilities)
        assert kling_result[0]["duration_sec"] in {5, 10}

    def test_swap_preserves_storyboard_intent(self):
        """preferred_bridge must be preserved so re-targeting back to Veo restores extend."""
        shots = [
            {"duration_sec": 8, "bridge_strategy": "extend", "preferred_bridge": "extend"}
        ]
        kling_result = _enforce_capabilities(shots, FakeKlingAdapter.capabilities)
        assert kling_result[0]["preferred_bridge"] == "extend"

        # Swap back to Veo
        veo_result = _enforce_capabilities(kling_result, FakeVeoAdapter.capabilities)
        assert veo_result[0]["bridge_strategy"] == "extend"
