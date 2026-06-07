"""Prefab loader — discovers style packs, grammars, and transitions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class PrefabLoader:
    """Loads and caches prefabs from ~/.cineforge/prefabs/."""

    def __init__(self, prefabs_dir: Path) -> None:
        self.prefabs_dir = prefabs_dir
        self._style_packs: dict[str, dict[str, Any]] = {}
        self._grammars: dict[str, dict[str, Any]] = {}
        self._transitions: dict[str, dict[str, Any]] = {}
        self._scan()

    def _scan(self) -> None:
        sp_dir = self.prefabs_dir / "style_packs"
        if sp_dir.exists():
            for f in sp_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(f.read_text(encoding="utf-8"))
                    self._style_packs[f.stem] = data
                except Exception as exc:
                    logger.warning("Failed to load style pack %s: %s", f, exc)

        g_dir = self.prefabs_dir / "grammars"
        if g_dir.exists():
            for f in g_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(f.read_text(encoding="utf-8"))
                    self._grammars[f.stem] = data
                except Exception as exc:
                    logger.warning("Failed to load grammar %s: %s", f, exc)

        t_dir = self.prefabs_dir / "transitions"
        if t_dir.exists():
            for f in t_dir.glob("*.py"):
                self._transitions[f.stem] = {"path": str(f), "name": f.stem}

    def get_style_pack(self, pack_id: str | None) -> dict[str, Any] | None:
        if not pack_id:
            return self._style_packs.get("cinematic_noir")
        return self._style_packs.get(pack_id)

    def list_style_packs(self) -> list[dict[str, Any]]:
        return [
            {"id": k, "name": v.get("name", k), "description": v.get("description", "")}
            for k, v in self._style_packs.items()
        ]

    def list_grammars(self) -> list[dict[str, Any]]:
        return [
            {"id": k, "name": v.get("name", k), "description": v.get("description", "")}
            for k, v in self._grammars.items()
        ]

    def list_transitions(self) -> list[dict[str, Any]]:
        return [{"id": k, "name": v["name"]} for k, v in self._transitions.items()]

    def load_transition(self, name: str) -> Any:
        """Dynamically import a transition prefab and return its apply function."""
        info = self._transitions.get(name)
        if not info:
            return None
        import importlib.util

        spec = importlib.util.spec_from_file_location(name, info["path"])
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, "apply", None)

    def reload(self) -> None:
        self._style_packs.clear()
        self._grammars.clear()
        self._transitions.clear()
        self._scan()
