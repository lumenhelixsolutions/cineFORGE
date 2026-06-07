"""Local sentence-transformers embedder (CPU-friendly)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.adapters.protocols import Embedder

logger = logging.getLogger(__name__)


class LocalEmbedder:
    """BGE-small or similar, runs on CPU."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.provider_id = "local.bge-small"
        self.is_local = True
        self._model_name = model_name
        self._model: Any | None = None
        self.dim = 384  # bge-small-en-v1.5

    def _load(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
                logger.info("Loaded embedder: %s", self._model_name)
            except ImportError:
                raise RuntimeError("sentence-transformers not installed")
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [e.tolist() for e in embeddings]
