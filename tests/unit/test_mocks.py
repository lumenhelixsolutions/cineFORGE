import pytest
import asyncio
from pathlib import Path
from backend.adapters.mocks import MockVideoModel, MockLLMDirector, MockEmbedder, MockTTSProvider, MockRefImgGenerator
from backend.adapters.protocols import VideoGenRequest, LLMRequest, AspectRatio

@pytest.mark.asyncio
async def test_mock_video_model_generate(tmp_path):
    """Verify MockVideoModel generates valid VideoGenResult with dummy files."""
    model = MockVideoModel(temp_dir=tmp_path)
    req = VideoGenRequest(
        prompt="A beautiful sunset over the mountains",
        duration_sec=10,
        aspect_ratio="16:9",
        resolution="1080p"
    )
    
    result = await model.generate(req)
    
    assert result.provider_id == "mock-video"
    assert result.duration_sec == 10.0
    assert result.clip_path.exists()
    assert result.last_frame_path.exists()
    assert result.cost_usd == 0.0

@pytest.mark.asyncio
async def test_mock_llm_director_complete():
    """Verify MockLLMDirector returns structured content when schema is provided."""
    model = MockLLMDirector()
    req = LLMRequest(
        system="You are a helpful assistant.",
        messages=[{"role": "user", "content": "Hello"}],
        response_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
    )
    
    result = await model.complete(req)
    
    assert result.provider_id == "mock-llm"
    assert isinstance(result.content, dict)
    assert result.content["status"] == "success"
    assert result.usage.input_tokens == 10

@pytest.mark.asyncio
async def test_mock_embedder():
    """Verify MockEmbedder returns correct dimensions."""
    dim = 512
    model = MockEmbedder(dim=dim)
    texts = ["hello", "world"]
    
    embeddings = await model.embed(texts)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) == dim
    assert embeddings[0][0] == 0.1

@pytest.mark.asyncio
async def test_mock_tts_synthesize(tmp_path):
    """Verify MockTTSProvider creates the output file."""
    model = MockTTSProvider()
    out_file = tmp_path / "output.mp3"
    
    result_path = await model.synthesize("Hello world", "en-US-Standard-A", out_file)
    
    assert result_path == out_file
    assert result_path.exists()

@pytest.mark.asyncio
async def test_mock_refimg_generate(tmp_path):
    """Verify MockRefImgGenerator creates a dummy reference image."""
    model = MockRefImgGenerator(temp_dir=tmp_path)
    # Note: Mock now takes temp_dir, so it's platform agnostic.

    ref_path = await model.generate("a cinematic shot")

    assert ref_path.suffix == ".jpg"
    assert ref_path.exists()
