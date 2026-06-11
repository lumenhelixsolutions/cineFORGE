"""Mock adapters for testing purposes."""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any

from backend.adapters.protocols import (
    Embedder,
    LLMCapabilities,
    LLMDirector,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    ReferenceImageGenerator,
    TTSProvider,
    VideoCapabilities,
    VideoGenRequest,
    VideoGenResult,
    VideoModel,
)

logger = logging.getLogger(__name__)

# ─────────── Video ──────────────────────────────────────────────── 

class MockVideoModel(VideoModel):
    capabilities = VideoCapabilities(
        provider_id="mock-video",
        display_name="Mock Video Provider",
        supported_durations_sec=[5, 10, 15, 30, 60],
        supported_aspect_ratios=["16:9", "9:16", "1:1"],
        supported_resolutions=["1080p", "720p"],
        max_reference_images=5,
        supports_native_audio=True,
        supports_frame_conditioning=True,
        supports_extend=True,
        max_extend_total_sec=60,
        supports_negative_prompt=True,
        is_local=True,
        cost_per_second_usd=0.0,
    )

    def __init__(self, temp_dir: Path | None = None):
        # Use a specific temp dir for tests if provided, otherwise fallback to system temp
        self._temp_dir = temp_dir or Path("/tmp")

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        logger.info("MockVideoModel: Generating video for prompt: %s", req.prompt)
        await asyncio.sleep(0.1)  # Faster for testing

        clip_id = str(uuid.uuid4())
        clip_path = self._temp_dir / f"mock_clip_{clip_id}.mp4"      
        last_frame_path = self._temp_dir / f"mock_frame_{clip_id}.jpg"

        # Create dummy files
        clip_path.touch()
        last_frame_path.touch()

        return VideoGenResult(
            clip_path=clip_path,
            last_frame_path=last_frame_path,
            duration_sec=float(req.duration_sec),
            has_audio=True,
            cost_usd=0.0,
            provider_id=self.capabilities.provider_id,
        )

    async def extend(self, req: Any) -> VideoGenResult:
        # Implementation for E2E testing of the extend endpoint
        logger.info("MockVideoModel: Extending video")
        await asyncio.sleep(0.1)
        
        clip_id = str(uuid.uuid4())
        clip_path = self._temp_dir / f"mock_clip_extended_{clip_id}.mp4"
        last_frame_path = self._temp_dir / f"mock_frame_extended_{clip_id}.jpg"

        clip_path.touch()
        last_frame_path.touch()

        return VideoGenResult(
            clip_path=clip_path,
            last_frame_path=last_frame_path,
            duration_sec=float(getattr(req, 'duration_sec', 7) + 7), # Mocked duration
            has_audio=True,
            cost_usd=0.0,
            provider_id=self.capabilities.provider_id,
        )

    async def healthcheck(self) -> bool:
        return True


# ─────────── LLM Director ───────────────────────────────────────── 

class MockLLMDirector(LLMDirector):
    capabilities = LLMCapabilities(
        provider_id="mock-llm",
        display_name="Mock LLM Provider",
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
        logger.info("MockLLMDirector: Completing request")
        await asyncio.sleep(0.1)

        # Return a dummy JSON response if a schema is provided, otherwise plain text
        content = "This is a mock response from the LLM Director."   
        if req.response_schema:
            content = {"message": "This is a mock structured response.", "status": "success"}

        return LLMResponse(
            content=content,
            tool_calls=[],
            usage=LLMUsage(input_tokens=10, output_tokens=20, cost_usd=0.0, provider_id=self.capabilities.provider_id),
            provider_id=self.capabilities.provider_id,
        )

    async def healthcheck(self) -> bool:
        return True


# ─────────── Embedder ───────────────────────────────────────────── 

class MockEmbedder(Embedder):
    def __init__(self, dim: int = 768):
        self.dim = dim
        self.provider_id = "mock-embed"
        self.is_local = True

    async def embed(self, texts: list[str]) -> list[list[float]]:    
        logger.info("MockEmbedder: Embedding %d texts", len(texts))  
        return [[0.1] * self.dim for _ in texts]


# ─────────── TTS Provider ───────────────────────────────────────── 

class MockTTSProvider(TTSProvider):
    def __init__(self):
        self.provider_id = "mock-tts"
        self.is_local = True

    async def synthesize(self, text: str, voice: str, out: Path) -> Path:
        logger.info("MockTTSProvider: Synthesizing text: %s", text)  
        await asyncio.sleep(0.1)
        out.touch()
        return out


# ─────────── RefImg Generator ───────────────────────────────────── 

class MockRefImgGenerator(ReferenceImageGenerator):
    def __init__(self, temp_dir: Path | None = None):
        self.provider_id = "mock-refimg"
        self.is_local = True
        self._temp_dir = temp_dir or Path("/tmp")

    async def generate(self, prompt: str, refs: list[Path] = []) -> Path:
        logger.info("MockRefImgGenerator: Generating ref image for prompt: %s", prompt)
        await asyncio.sleep(0.1)
        ref_path = self._temp_dir / f"mock_ref_{uuid.uuid4()}.jpg"   
        ref_path.touch()
        return ref_path
