"""Prompt caching with LiteLLM and provider-native layers."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class PromptCache:
    """In-memory prompt cache with stable-prefix layout for breakpoint hits."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self._hit_keys: set[str] = set()

    def key(self, system: str, messages: list[dict[str, Any]], schema: dict[str, Any] | None) -> str:
        payload = json.dumps({"system": system, "messages": messages, "schema": schema}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, system: str, messages: list[dict[str, Any]], schema: dict[str, Any] | None) -> Any | None:
        k = self.key(system, messages, schema)
        entry = self._cache.get(k)
        if entry:
            self._hit_keys.add(k)
            logger.debug("Cache hit: %s", k[:16])
            return entry["response"]
        return None

    def set(self, system: str, messages: list[dict[str, Any]], schema: dict[str, Any] | None, response: Any) -> None:
        k = self.key(system, messages, schema)
        self._cache[k] = {"response": response, "hits": self._cache.get(k, {}).get("hits", 0) + 1}

    def hit_rate(self) -> float:
        if not self._cache:
            return 0.0
        return len(self._hit_keys) / len(self._cache)
