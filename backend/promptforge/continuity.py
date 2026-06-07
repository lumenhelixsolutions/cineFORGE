"""Continuity bible — per-project character/location/camera state."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONTINUITY = """characters:
  alice:
    identity_token: "the 30-year-old woman with auburn bob and silver locket"
    wardrobe: "navy peacoat, charcoal jeans, leather satchel"
    signature_props: ["silver locket", "leather satchel"]
locations:
  alley:
    description: "rain-slick neon-lit alley, brick walls, fire escape"
    palette: "teal and magenta, deep shadows"
    lighting_model: "wet key from neon signage, low fill"
camera_grammar:
  lens_default: "35mm"
  motion_default: "slow handheld"
  grade: "teal-magenta high-contrast film stock"
"""


class ContinuityBible:
    """Loads and resolves continuity YAML for a project."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.characters: dict[str, dict[str, Any]] = data.get("characters", {})
        self.locations: dict[str, dict[str, Any]] = data.get("locations", {})
        self.camera_grammar: dict[str, str] = data.get("camera_grammar", {})
        self._raw = data

    @classmethod
    def from_project(cls, project_id: str, projects_dir: Path) -> "ContinuityBible":
        path = projects_dir / project_id / "continuity.yaml"
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        else:
            data = yaml.safe_load(DEFAULT_CONTINUITY)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(DEFAULT_CONTINUITY, encoding="utf-8")
        return cls(data)

    def load_yaml(self, yaml_text: str) -> None:
        self._raw = yaml.safe_load(yaml_text)
        self.characters = self._raw.get("characters", {})
        self.locations = self._raw.get("locations", {})
        self.camera_grammar = self._raw.get("camera_grammar", {})

    def resolve_character(self, char_id: str) -> str:
        char = self.characters.get(char_id, {})
        token: str = char.get("identity_token", f"the {char_id}")
        wardrobe: str = char.get("wardrobe", "")
        if wardrobe:
            return f"{token}, wearing {wardrobe}"
        return token

    def resolve_location(self, loc_id: str) -> str:
        loc = self.locations.get(loc_id, {})
        desc: str = loc.get("description", loc_id)
        palette: str = loc.get("palette", "")
        if palette:
            return f"{desc}, color palette: {palette}"
        return desc

    def to_yaml(self) -> str:
        return yaml.safe_dump(self._raw, sort_keys=False, allow_unicode=True)
