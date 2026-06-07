"""Routing configuration — resolves providers per tier and profile."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_ROUTING = """profiles:
  cloud_premium:
    llm:
      treatment: anthropic.claude-sonnet-4-6
      storyboard: anthropic.claude-sonnet-4-6
      promptforge: anthropic.claude-haiku-4-5
      fallback: gemini.gemini-2.5-flash
    video:
      hero: vertex.veo-3.1
      standard: vertex.veo-3.1-fast
      broll: fal.hailuo-02
      title: wan2gp.wan-2.2-14b-gguf
      extend_ok: vertex.veo-3.1
    embedder: local.bge-small

  local_two_stage:
    llm:
      treatment: ollama.llama-4-70b
      storyboard: ollama.llama-4-70b
      promptforge: ollama.qwen-3-32b
      fallback: ollama.qwen-3-7b
    video:
      preview: wan2gp.ltx-video-2.3
      hero: wan2gp.wan-2.2-14b-gguf
      standard: wan2gp.wan-2.2-14b-gguf
      broll: wan2gp.ltx-video-2.3
      title: wan2gp.ltx-video-2.3
      human_subjects: wan2gp.hunyuan-1.5
    embedder: local.bge-small
    refimg: local.diffusers

  hybrid:
    llm:
      treatment: anthropic.claude-sonnet-4-6
      storyboard: anthropic.claude-sonnet-4-6
      promptforge: anthropic.claude-haiku-4-5
    video:
      preview: wan2gp.ltx-video-2.3
      hero: vertex.veo-3.1
      standard: vertex.veo-3.1-fast
      broll: wan2gp.wan-2.2-14b-gguf
      title: wan2gp.ltx-video-2.3
      extend_ok: vertex.veo-3.1
    embedder: local.bge-small
"""


class RoutingConfig:
    """Reads routing.yaml and resolves providers per task/tier."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.profiles: dict[str, Any] = config.get("profiles", {})

    @classmethod
    def from_file(cls, path: Path) -> "RoutingConfig":
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        else:
            data = yaml.safe_load(DEFAULT_ROUTING)
            path.write_text(DEFAULT_ROUTING, encoding="utf-8")
        return cls(data)

    def update(self, new_config: dict[str, Any]) -> None:
        self.config.update(new_config)
        self.profiles = self.config.get("profiles", {})

    def save(self, path: Path) -> None:
        path.write_text(yaml.safe_dump(self.config, sort_keys=False, allow_unicode=True), encoding="utf-8")

    def resolve_llm(self, task: str, profile: str) -> str:
        p = self.profiles.get(profile, {})
        llm = p.get("llm", {})
        result: str = llm.get(task, llm.get("fallback", "litellm"))
        return result

    def resolve_video(self, tier: str, profile: str, preview_mode: bool = False) -> str:
        p = self.profiles.get(profile, {})
        video = p.get("video", {})
        if preview_mode:
            preview_provider: str = video.get("preview", video.get("standard", "vertex.veo-3.1"))
            return preview_provider
        tier_provider: str = video.get(tier, video.get("standard", "vertex.veo-3.1"))
        return tier_provider

    def resolve_embedder(self, profile: str) -> str:
        p = self.profiles.get(profile, {})
        result: str = p.get("embedder", "local.bge-small")
        return result
