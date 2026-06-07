"""Semantic cache using txtai (SQLite mode) or local embeddings."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SemanticCache:
    """Caches LLM responses by embedding similarity (cosine >= 0.95)."""

    def __init__(self, cache_dir: Path, dim: int = 384) -> None:
        self.cache_dir = cache_dir
        self.dim = dim
        self._index_path = cache_dir / "semantic_cache.db"
        self._entries: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        import json

        if self._index_path.exists():
            try:
                self._entries = json.loads(self._index_path.read_text(encoding="utf-8"))
            except Exception:
                self._entries = {}

    def _save(self) -> None:
        import json

        self._index_path.write_text(json.dumps(self._entries, indent=2), encoding="utf-8")

    def _cosine(self, a: list[float], b: list[float]) -> float:
        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))

    async def lookup(self, text: str, embedding: list[float]) -> Any | None:
        for entry in self._entries.values():
            sim = self._cosine(embedding, entry["embedding"])
            if sim >= 0.95:
                logger.debug("Semantic cache hit (sim=%.3f)", sim)
                return entry["response"]
        return None

    async def store(self, text: str, embedding: list[float], response: Any, continuity_hash: str = "") -> None:
        key = hashlib.sha256(text.encode()).hexdigest()[:16]
        self._entries[key] = {
            "text": text,
            "embedding": embedding,
            "response": response,
            "continuity_hash": continuity_hash,
        }
        self._save()

    def invalidate(self, continuity_hash: str) -> None:
        """Invalidate entries matching a continuity/style pack hash change."""
        before = len(self._entries)
        self._entries = {k: v for k, v in self._entries.items() if v.get("continuity_hash") != continuity_hash}
        if len(self._entries) < before:
            logger.info("Invalidated %d semantic cache entries", before - len(self._entries))
            self._save()
