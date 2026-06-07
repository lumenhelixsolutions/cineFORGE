"""Entry-point discovery and lazy adapter instantiation."""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import Any, TypeVar, Generic

from backend.adapters.protocols import VideoModel, LLMDirector, Embedder, TTSProvider, ReferenceImageGenerator
from backend.telemetry import log_adapter_use

logger = logging.getLogger(__name__)

T = TypeVar("T")


class _LazyAdapter(Generic[T]):
    """Wraps an adapter class to defer instantiation until first use."""

    def __init__(self, cls: type[T]) -> None:
        self._cls = cls
        self._instance: T | None = None

    def get(self) -> T:
        if self._instance is None:
            self._instance = self._cls()
        return self._instance


class AdapterRegistry:
    """Discovers and lazily instantiates adapters via Python entry points."""

    def __init__(self) -> None:
        self._video: dict[str, _LazyAdapter[VideoModel]] = {}
        self._llm: dict[str, _LazyAdapter[LLMDirector]] = {}
        self._embedder: dict[str, _LazyAdapter[Embedder]] = {}
        self._tts: dict[str, _LazyAdapter[TTSProvider]] = {}
        self._refimg: dict[str, _LazyAdapter[ReferenceImageGenerator]] = {}
        self._discover()

    def _discover(self) -> None:
        eps = entry_points()
        for ep in eps.select(group="cineforge.adapters.video"):
            try:
                cls = ep.load()
                self._video[ep.name] = _LazyAdapter(cls)
                logger.info("Discovered video adapter: %s", ep.name)
            except Exception as exc:
                logger.warning("Failed to load video adapter %s: %s", ep.name, exc)

        for ep in eps.select(group="cineforge.adapters.llm"):
            try:
                cls = ep.load()
                self._llm[ep.name] = _LazyAdapter(cls)
                logger.info("Discovered LLM adapter: %s", ep.name)
            except Exception as exc:
                logger.warning("Failed to load LLM adapter %s: %s", ep.name, exc)

        for ep in eps.select(group="cineforge.adapters.embedder"):
            try:
                cls = ep.load()
                self._embedder[ep.name] = _LazyAdapter(cls)
                logger.info("Discovered embedder adapter: %s", ep.name)
            except Exception as exc:
                logger.warning("Failed to load embedder adapter %s: %s", ep.name, exc)

        for ep in eps.select(group="cineforge.adapters.tts"):
            try:
                cls = ep.load()
                self._tts[ep.name] = _LazyAdapter(cls)
                logger.info("Discovered TTS adapter: %s", ep.name)
            except Exception as exc:
                logger.warning("Failed to load TTS adapter %s: %s", ep.name, exc)

        for ep in eps.select(group="cineforge.adapters.refimg"):
            try:
                cls = ep.load()
                self._refimg[ep.name] = _LazyAdapter(cls)
                logger.info("Discovered refimg adapter: %s", ep.name)
            except Exception as exc:
                logger.warning("Failed to load refimg adapter %s: %s", ep.name, exc)

    # ── Public accessors ─────────────────────────────────────────

    def video_adapters(self) -> dict[str, VideoModel]:
        return {k: v.get() for k, v in self._video.items()}

    def video_adapter(self, name: str) -> VideoModel:
        if name not in self._video:
            raise KeyError(f"Unknown video adapter: {name}")
        log_adapter_use("video", name, "generate")
        return self._video[name].get()

    def llm_adapters(self) -> dict[str, LLMDirector]:
        return {k: v.get() for k, v in self._llm.items()}

    def llm_adapter(self, name: str) -> LLMDirector:
        if name not in self._llm:
            raise KeyError(f"Unknown LLM adapter: {name}")
        log_adapter_use("llm", name, "complete")
        return self._llm[name].get()

    def embedder_adapters(self) -> dict[str, Embedder]:
        return {k: v.get() for k, v in self._embedder.items()}

    def embedder_adapter(self, name: str) -> Embedder:
        if name not in self._embedder:
            raise KeyError(f"Unknown embedder adapter: {name}")
        log_adapter_use("embedder", name, "embed")
        return self._embedder[name].get()

    def tts_adapters(self) -> dict[str, TTSProvider]:
        return {k: v.get() for k, v in self._tts.items()}

    def tts_adapter(self, name: str) -> TTSProvider:
        if name not in self._tts:
            raise KeyError(f"Unknown TTS adapter: {name}")
        return self._tts[name].get()

    def refimg_adapters(self) -> dict[str, ReferenceImageGenerator]:
        return {k: v.get() for k, v in self._refimg.items()}

    def refimg_adapter(self, name: str) -> ReferenceImageGenerator:
        if name not in self._refimg:
            raise KeyError(f"Unknown refimg adapter: {name}")
        return self._refimg[name].get()

    def all_capabilities(self) -> dict[str, Any]:
        caps: dict[str, Any] = {
            "video": {},
            "llm": {},
            "embedder": {},
            "tts": {},
            "refimg": {},
        }
        for k, v_video in self._video.items():
            try:
                caps["video"][k] = v_video.get().capabilities.model_dump()
            except Exception as exc:
                caps["video"][k] = {"error": str(exc)}
        for k, v_llm in self._llm.items():
            try:
                caps["llm"][k] = v_llm.get().capabilities.model_dump()
            except Exception as exc:
                caps["llm"][k] = {"error": str(exc)}
        for k, v_embed in self._embedder.items():
            try:
                caps["embedder"][k] = {
                    "dim": v_embed.get().dim,
                    "provider_id": v_embed.get().provider_id,
                    "is_local": v_embed.get().is_local,
                }
            except Exception as exc:
                caps["embedder"][k] = {"error": str(exc)}
        return caps

    def reload(self) -> None:
        """Re-scan entry points (e.g., after pip install)."""
        self._video.clear()
        self._llm.clear()
        self._embedder.clear()
        self._tts.clear()
        self._refimg.clear()
        self._discover()


# Singleton registry instance
_registry: AdapterRegistry | None = None


def get_registry() -> AdapterRegistry:
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
    return _registry
