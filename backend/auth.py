"""Optional API-key middleware."""

from __future__ import annotations

import os
from typing import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

API_KEY = os.getenv("CINEFORGE_API_KEY")


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path == "/health":
            return await call_next(request)
        if API_KEY:
            header_key = request.headers.get("X-API-Key")
            if header_key != API_KEY:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized", "detail": "Invalid or missing API key"},
                )
        return await call_next(request)
