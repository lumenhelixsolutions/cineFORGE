"""Adapter protocols — the modularity contract.

Core code imports ONLY from this module. No concrete provider imports
outside backend/adapters/*.
"""
from __future__ import annotations

from typing import Any, Protocol, Literal, runtime_checkable
from pathlib import Path

from pydantic import BaseModel, Field

# ─────────── Video ────────────────────────────────────────────────

AspectRatio = Literal["16:9", "9:16", "1:1", "4:3", "3:4"]


class VideoCapabilities(BaseModel):
    provider_id: str
    display_name: str
    supported_durations_sec: list[int]
    supported_aspect_ratios: list[AspectRatio]
    supported_resolutions: list[str]
    max_reference_images: int
    supports_native_audio: bool
    supports_frame_conditioning: bool
    supports_extend: bool
    max_extend_total_sec: int | None
    supports_negative_prompt: bool
    is_local: bool
    cost_per_second_usd: float
    notes: str = ""


class VideoGenRequest(BaseModel):
    prompt: str
    negative_prompt: str | None = None
    duration_sec: int
    aspect_ratio: AspectRatio
    resolution: str
    reference_images: list[Path] = Field(default_factory=list)
    first_frame: Path | None = None
    last_frame: Path | None = None
    seed: int | None = None


class VideoGenResult(BaseModel):
    clip_path: Path
    last_frame_path: Path
    duration_sec: float
    has_audio: bool
    cost_usd: float
    provider_id: str
    raw_response_path: Path | None = None


class ExtendRequest(BaseModel):
    source_clip: Path
    prompt: str
    duration_sec: int = 7


class CapabilityError(Exception):
    """Raised when a request exceeds adapter capabilities."""
    pass


@runtime_checkable
class VideoModel(Protocol):
    capabilities: VideoCapabilities

    async def generate(self, req: VideoGenRequest) -> VideoGenResult:
        ...

    async def extend(self, req: ExtendRequest) -> VideoGenResult:
        """Raise CapabilityError if not supported."""
        ...

    async def healthcheck(self) -> bool:
        ...


# ─────────── LLM Director ─────────────────────────────────────────

class LLMCapabilities(BaseModel):
    provider_id: str
    display_name: str
    context_window: int
    supports_prompt_caching: bool
    supports_structured_output: bool
    supports_tool_use: bool
    is_local: bool
    cost_per_1k_input_usd: float
    cost_per_1k_output_usd: float
    cost_per_1k_cached_input_usd: float


class LLMRequest(BaseModel):
    system: str
    messages: list[dict[str, Any]]
    response_schema: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    max_tokens: int = 4096
    temperature: float = 0.7
    cache_breakpoints: list[int] = Field(default_factory=list)


class LLMUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    cost_usd: float


class LLMResponse(BaseModel):
    content: str | dict[str, Any] | list[dict[str, Any]]
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    usage: LLMUsage
    provider_id: str


@runtime_checkable
class LLMDirector(Protocol):
    capabilities: LLMCapabilities

    async def complete(self, req: LLMRequest) -> LLMResponse:
        ...

    async def healthcheck(self) -> bool:
        ...


# ─────────── Embedder (semantic cache) ────────────────────────────

@runtime_checkable
class Embedder(Protocol):
    dim: int
    provider_id: str
    is_local: bool

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


# ─────────── Optional: TTS, Reference image gen ───────────────────

@runtime_checkable
class TTSProvider(Protocol):
    provider_id: str
    is_local: bool

    async def synthesize(self, text: str, voice: str, out: Path) -> Path:
        ...


@runtime_checkable
class ReferenceImageGenerator(Protocol):
    provider_id: str
    is_local: bool

    async def generate(self, prompt: str, refs: list[Path] = Field(default_factory=list)) -> Path:
        ...
