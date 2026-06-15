"""Optional local caption assist via Ollama (M18)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("LOCAL_CAPTION_MODEL", "llava")


def is_enabled() -> bool:
    return os.environ.get("LOCAL_CAPTION_ENABLED", "false").lower() in ("1", "true", "yes")


def caption_image(image_path: str, *, prompt: str | None = None, model: str | None = None) -> dict[str, Any]:
    """Generate a short caption for a local image using Ollama multimodal API."""
    if not is_enabled():
        return {"ok": False, "error": "LOCAL_CAPTION_ENABLED is not set"}
    if not os.path.isfile(image_path):
        return {"ok": False, "error": f"Image not found: {image_path}"}

    import base64

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    body = {
        "model": model or DEFAULT_MODEL,
        "prompt": prompt or "Describe this storyboard panel in one sentence for video generation.",
        "images": [b64],
        "stream": False,
    }
    req = urllib.request.Request(
        f"{OLLAMA_HOST.rstrip('/')}/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = str(payload.get("response") or "").strip()
        return {"ok": bool(text), "caption": text, "model": body["model"], "provider": "ollama"}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": f"Ollama unreachable: {exc}"}