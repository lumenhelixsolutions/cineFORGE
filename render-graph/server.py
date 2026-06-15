#!/usr/bin/env python3
"""
CineForge render pipeline LangGraph HTTP sidecar (M16).

  python render-graph/server.py
  RENDER_GRAPH_PORT=7790 python render-graph/server.py
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runner import invoke_graph, load_graph_profiles

HOST = os.environ.get("RENDER_GRAPH_HOST", "127.0.0.1")
PORT = int(os.environ.get("RENDER_GRAPH_PORT", "7790"))
ROOT = Path(__file__).resolve().parent


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class RenderGraphHandler(BaseHTTPRequestHandler):
    server_version = "CineforgeRenderGraph/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        if os.environ.get("RENDER_GRAPH_QUIET") == "1":
            return
        super().log_message(fmt, *args)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/health":
            return _json_response(self, 200, {"status": "ok", "service": "render-graph", "port": PORT})
        if path == "/spec":
            spec_path = ROOT / "graph.spec.json"
            if not spec_path.exists():
                return _json_response(self, 404, {"error": "graph.spec.json missing"})
            return _json_response(self, 200, json.loads(spec_path.read_text(encoding="utf-8")))
        if path == "/profiles":
            return _json_response(self, 200, load_graph_profiles())
        return _json_response(self, 404, {"error": "not found"})

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path != "/run":
            return _json_response(self, 404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            body = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return _json_response(self, 400, {"error": "invalid JSON body"})
        profile_id = str(body.get("profile_id") or body.get("profileId") or "preview-chain").strip()
        project_id = str(body.get("project_id") or body.get("projectId") or "").strip()
        if not project_id:
            return _json_response(self, 400, {"error": "project_id required"})
        try:
            result = invoke_graph(
                profile_id,
                project_id=project_id,
                dry_run_mode=bool(body.get("dry_run") or body.get("dryRun")),
                auto_approve=bool(body.get("auto_approve") or body.get("autoApprove")),
                ingest_payload=body.get("ingest_payload") or body.get("ingestPayload"),
                cineforge_base=body.get("cineforge_base") or body.get("cineforgeBase"),
            )
            status = 200 if result.get("ok") else 422
            return _json_response(self, status, result)
        except Exception as exc:  # noqa: BLE001
            return _json_response(self, 500, {"ok": False, "error": str(exc)})


def main() -> int:
    httpd = ThreadingHTTPServer((HOST, PORT), RenderGraphHandler)
    print(f"[render-graph] listening on http://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[render-graph] stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())