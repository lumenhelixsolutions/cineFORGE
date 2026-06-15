"""HTTP client for CineForge FastAPI (render pipeline graph)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE = os.environ.get("CINEFORGE_URL", "http://127.0.0.1:8765")


def _request(method: str, path: str, body: dict[str, Any] | None = None, *, base: str = DEFAULT_BASE) -> Any:
    url = f"{base.rstrip('/')}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"} if data else {"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed ({exc.code}): {detail}") from exc


def fetch_health(base: str = DEFAULT_BASE) -> dict[str, Any]:
    return _request("GET", "/health", base=base)


def fetch_project(project_id: str, base: str = DEFAULT_BASE) -> dict[str, Any]:
    return _request("GET", f"/projects/{project_id}", base=base)


def patch_project(project_id: str, body: dict[str, Any], base: str = DEFAULT_BASE) -> dict[str, Any]:
    return _request("PATCH", f"/projects/{project_id}", body, base=base)


def ingest_lookbook(project_id: str, payload: dict[str, Any], base: str = DEFAULT_BASE) -> dict[str, Any]:
    return _request("POST", f"/projects/{project_id}/ingest/lookbook", payload, base=base)


def fetch_lookbook_review(project_id: str, base: str = DEFAULT_BASE) -> dict[str, Any]:
    return _request("GET", f"/projects/{project_id}/lookbook/review?format=json", base=base)


def queue_render(project_id: str, shot_ids: list[str] | None = None, base: str = DEFAULT_BASE) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if shot_ids:
        body["shot_ids"] = shot_ids
    return _request("POST", f"/projects/{project_id}/render", body, base=base)


def stitch_project(project_id: str, output_name: str = "master", base: str = DEFAULT_BASE) -> dict[str, Any]:
    return _request("POST", f"/projects/{project_id}/stitch", {"output_name": output_name}, base=base)