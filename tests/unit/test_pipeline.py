"""Unit tests for RenderPipeline helper methods."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from backend.generator.pipeline import RenderPipeline
from backend.adapters.registry import AdapterRegistry
from backend.token_ledger.router import RoutingConfig


class FakeAdapter:
    capabilities = MagicMock()
    capabilities.max_reference_images = 3
    capabilities.supports_frame_conditioning = False

    async def generate(self, req):
        return MagicMock(clip_path=Path("/tmp/fake.mp4"), duration_sec=6.0)


class FakeTTS:
    provider_id = "piper.local"
    is_local = True

    async def synthesize(self, text: str, voice: str, out: Path) -> Path:
        out.write_bytes(b"audio")
        return out


class FakeRefImg:
    provider_id = "local.diffusers"
    is_local = True

    async def generate(self, prompt: str, refs=None):
        path = Path("/tmp/ref.png")
        path.write_bytes(b"img")
        return path


class FakeRegistry:
    def __init__(self):
        self._tts = {"piper.local": FakeTTS()}
        self._refimg = {"local.diffusers": FakeRefImg()}

    def tts_adapter(self, name: str):
        return self._tts[name]

    def refimg_adapters(self):
        return self._refimg


@pytest.mark.asyncio
class TestRenderPipeline:
    async def test_generate_narration(self, tmp_path):
        registry = FakeRegistry()
        router = RoutingConfig(config={})
        pipeline = RenderPipeline(registry, router, tmp_path)
        shot = MagicMock()
        shot.narration = "Hello world"
        shot_dir = tmp_path / "shots" / "s1"
        result = await pipeline._generate_narration(shot, shot_dir)
        assert result is not None
        assert result.name == "narration.wav"
        assert result.exists()

    async def test_generate_narration_no_text(self, tmp_path):
        registry = FakeRegistry()
        router = RoutingConfig(config={})
        pipeline = RenderPipeline(registry, router, tmp_path)
        shot = {"narration": None}
        shot_dir = tmp_path / "shots" / "s1"
        result = await pipeline._generate_narration(shot, shot_dir)
        assert result is None

    async def test_generate_reference_images(self, tmp_path):
        registry = FakeRegistry()
        router = RoutingConfig(config={})
        pipeline = RenderPipeline(registry, router, tmp_path)
        shot = MagicMock()
        shot.tier = "hero"
        shot.prompt_text = "A cat in a hat"
        shot_dir = tmp_path / "shots" / "s1"
        result = await pipeline._generate_reference_images(shot, shot_dir, style_pack=None)
        assert result is not None
        assert result.name == "ref.png"
        assert result.exists()

    async def test_generate_reference_images_skips_broll(self, tmp_path):
        registry = FakeRegistry()
        router = RoutingConfig(config={})
        pipeline = RenderPipeline(registry, router, tmp_path)
        shot = MagicMock()
        shot.tier = "broll"
        shot_dir = tmp_path / "shots" / "s1"
        result = await pipeline._generate_reference_images(shot, shot_dir)
        assert result is None
