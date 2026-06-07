"""Application settings and configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """CineForge runtime configuration."""

    model_config = SettingsConfigDict(env_prefix="CINEFORGE_", case_sensitive=False)

    # Server
    port: int = int(os.getenv("CINEFORGE_PORT", "8765"))
    host: str = "127.0.0.1"
    log_level: str = "info"

    # Paths
    data_dir: Path = Path(os.getenv("CINEFORGE_DATA_DIR", str(Path.home() / ".cineforge")))
    projects_dir: Path = Path("")
    prefabs_dir: Path = Path("")
    cache_dir: Path = Path("")

    # Database
    database_url: str = ""

    # Feature flags
    enable_tts: bool = True
    enable_refimg: bool = True
    mock_video: bool = os.getenv("CINEFORGE_MOCK_VIDEO", "false").lower() == "true"
    mock_llm: bool = os.getenv("CINEFORGE_MOCK_LLM", "false").lower() == "true"

    # Defaults
    default_routing_profile: str = "hybrid"
    default_budget_usd: float = 1.00
    max_project_size_mb: int = 500

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.projects_dir = self.data_dir / "projects"
        self.prefabs_dir = self.data_dir / "prefabs"
        self.cache_dir = self.data_dir / "cache"
        self.database_url = f"sqlite+aiosqlite:///{self.data_dir / 'cineforge.db'}"
        # Ensure directories exist
        for d in (self.data_dir, self.projects_dir, self.prefabs_dir, self.cache_dir):
            d.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
