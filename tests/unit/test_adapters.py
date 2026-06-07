"""Unit tests for video adapters."""
from pathlib import Path

import pytest

from backend.adapters.video.kling_adapter import KlingAdapter
from backend.adapters.video.sora_adapter import SoraAdapter
from backend.adapters.video.luma_adapter import LumaAdapter
from backend.adapters.protocols import VideoGenRequest, ExtendRequest, CapabilityError


class TestKlingAdapter:
    def test_instantiation(self) -> None:
        adapter = KlingAdapter()
        assert adapter.capabilities.provider_id == "kling.3.0"

    def test_estimate_cost(self) -> None:
        adapter = KlingAdapter()
        assert adapter.estimate_cost(5) == pytest.approx(0.075 * 5)

    @pytest.mark.asyncio
    async def test_healthcheck_no_key(self) -> None:
        adapter = KlingAdapter()
        adapter._api_key = ""
        assert not await adapter.healthcheck()

    @pytest.mark.asyncio
    async def test_generate_raises_without_key(self) -> None:
        adapter = KlingAdapter()
        adapter._api_key = ""
        req = VideoGenRequest(
            prompt="test", duration_sec=5, aspect_ratio="16:9", resolution="720p"
        )
        with pytest.raises(RuntimeError, match="KLING_API_KEY"):
            await adapter.generate(req)

    @pytest.mark.asyncio
    async def test_mock_generate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CINEFORGE_MOCK_VIDEO", "true")
        adapter = KlingAdapter()
        adapter._api_key = "fake"
        req = VideoGenRequest(
            prompt="test", duration_sec=5, aspect_ratio="16:9", resolution="720p"
        )
        result = await adapter.generate(req)
        assert result.clip_path.exists()
        assert result.duration_sec == 5.0
        assert result.provider_id == "kling.3.0.mock"

    @pytest.mark.asyncio
    async def test_extend_raises(self) -> None:
        adapter = KlingAdapter()
        req = ExtendRequest(source_clip=Path("/tmp/clip.mp4"), prompt="continue")
        with pytest.raises(CapabilityError):
            await adapter.extend(req)


class TestSoraAdapter:
    def test_instantiation(self) -> None:
        adapter = SoraAdapter()
        assert adapter.capabilities.provider_id == "openai.sora"

    def test_estimate_cost(self) -> None:
        adapter = SoraAdapter()
        assert adapter.estimate_cost(10, "720p") == pytest.approx(1.0)
        assert adapter.estimate_cost(10, "1080p") == pytest.approx(2.0)

    @pytest.mark.asyncio
    async def test_healthcheck_no_key(self) -> None:
        adapter = SoraAdapter()
        adapter._api_key = ""
        assert not await adapter.healthcheck()

    @pytest.mark.asyncio
    async def test_generate_raises_without_key(self) -> None:
        adapter = SoraAdapter()
        adapter._api_key = ""
        req = VideoGenRequest(
            prompt="test", duration_sec=5, aspect_ratio="16:9", resolution="720p"
        )
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            await adapter.generate(req)

    @pytest.mark.asyncio
    async def test_mock_generate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CINEFORGE_MOCK_VIDEO", "true")
        adapter = SoraAdapter()
        adapter._api_key = "fake"
        req = VideoGenRequest(
            prompt="test", duration_sec=5, aspect_ratio="16:9", resolution="720p"
        )
        result = await adapter.generate(req)
        assert result.clip_path.exists()
        assert result.duration_sec == 5.0
        assert result.provider_id == "openai.sora.mock"

    @pytest.mark.asyncio
    async def test_extend_raises(self) -> None:
        adapter = SoraAdapter()
        req = ExtendRequest(source_clip=Path("/tmp/clip.mp4"), prompt="continue")
        with pytest.raises(CapabilityError):
            await adapter.extend(req)


class TestLumaAdapter:
    def test_instantiation(self) -> None:
        adapter = LumaAdapter()
        assert adapter.capabilities.provider_id == "luma.dream-machine"

    def test_estimate_cost(self) -> None:
        adapter = LumaAdapter()
        assert adapter.estimate_cost(5, "720p") > 0

    @pytest.mark.asyncio
    async def test_healthcheck_no_key(self) -> None:
        adapter = LumaAdapter()
        adapter._luma_key = ""
        adapter._fal_key = ""
        adapter._use_fal = False
        assert not await adapter.healthcheck()

    @pytest.mark.asyncio
    async def test_generate_raises_without_key(self) -> None:
        adapter = LumaAdapter()
        adapter._luma_key = ""
        adapter._fal_key = ""
        adapter._use_fal = False
        req = VideoGenRequest(
            prompt="test", duration_sec=5, aspect_ratio="16:9", resolution="720p"
        )
        with pytest.raises(RuntimeError, match="LUMA_API_KEY or FAL_KEY"):
            await adapter.generate(req)

    @pytest.mark.asyncio
    async def test_mock_generate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CINEFORGE_MOCK_VIDEO", "true")
        adapter = LumaAdapter()
        adapter._luma_key = "fake"
        req = VideoGenRequest(
            prompt="test", duration_sec=5, aspect_ratio="16:9", resolution="720p"
        )
        result = await adapter.generate(req)
        assert result.clip_path.exists()
        assert result.duration_sec == 5.0
        assert result.provider_id == "luma.dream-machine.mock"

    @pytest.mark.asyncio
    async def test_extend_raises(self) -> None:
        adapter = LumaAdapter()
        req = ExtendRequest(source_clip=Path("/tmp/clip.mp4"), prompt="continue")
        with pytest.raises(CapabilityError):
            await adapter.extend(req)
