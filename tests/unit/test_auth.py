"""Unit tests for auth scaffolding."""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable
from unittest.mock import MagicMock

import pytest
from fastapi import Request
from starlette.responses import Response

from backend.auth import APIKeyMiddleware


async def _noop_call_next(request: Request) -> Response:
    return Response(content=b"ok")


def _dispatch(middleware: APIKeyMiddleware, req: Request) -> Response:
    return asyncio.get_event_loop().run_until_complete(
        middleware.dispatch(req, _noop_call_next)
    )


class TestAuthMiddleware:
    def test_no_api_key_set_allows_all(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("backend.auth.API_KEY", None)
        req = MagicMock(spec=Request)
        req.url.path = "/projects"
        req.headers = {}
        middleware = APIKeyMiddleware(app=MagicMock())
        resp = _dispatch(middleware, req)
        assert resp.status_code == 200

    def test_api_key_required_missing_header(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("backend.auth.API_KEY", "secret123")
        req = MagicMock(spec=Request)
        req.url.path = "/projects"
        req.headers = {}
        middleware = APIKeyMiddleware(app=MagicMock())
        resp = _dispatch(middleware, req)
        assert resp.status_code == 401

    def test_api_key_required_valid_header(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("backend.auth.API_KEY", "secret123")
        req = MagicMock(spec=Request)
        req.url.path = "/projects"
        req.headers = {"X-API-Key": "secret123"}
        middleware = APIKeyMiddleware(app=MagicMock())
        resp = _dispatch(middleware, req)
        assert resp.status_code == 200

    def test_health_endpoint_exempt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("backend.auth.API_KEY", "secret123")
        req = MagicMock(spec=Request)
        req.url.path = "/health"
        req.headers = {}
        middleware = APIKeyMiddleware(app=MagicMock())
        resp = _dispatch(middleware, req)
        assert resp.status_code == 200
