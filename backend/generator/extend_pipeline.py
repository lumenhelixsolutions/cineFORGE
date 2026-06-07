"""Extend pipeline — uses VideoModel.extend() for native clip extension."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.adapters.protocols import ExtendRequest, CapabilityError

logger = logging.getLogger(__name__)


class ExtendPipeline:
    """Extends an existing clip using the provider's native extend API."""

    def __init__(self, adapter: Any) -> None:
        self.adapter = adapter

    async def run(self, source_clip: Path, prompt: str, duration_sec: int = 7) -> Any:
        if not self.adapter.capabilities.supports_extend:
            raise CapabilityError(f"{self.adapter.capabilities.provider_id} does not support extend")
        req = ExtendRequest(source_clip=source_clip, prompt=prompt, duration_sec=duration_sec)
        return await self.adapter.extend(req)
