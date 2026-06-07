"""Security headers and rate-limiting middleware for CineForge."""

from __future__ import annotations

import re
import time
from typing import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

# ── Security Headers Middleware ────────────────────────────────

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; connect-src 'self';",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add OWASP-recommended security headers to every response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            # Only add HSTS when the request was served over HTTPS or when
            # running in a production-like environment where TLS is terminated.
            if header == "Strict-Transport-Security":
                if request.url.scheme != "https":
                    continue
            response.headers[header] = value
        return response


# ── Rate Limiting Middleware ───────────────────────────────────

# Simple in-memory bucket; keys are "ip:pattern".
_rate_buckets: dict[str, list[float]] = {}

RATE_LIMITS: list[tuple[re.Pattern[str], int, int]] = [
    # 5 requests per minute for generate* endpoints under /api/
    (re.compile(r"^/api/.*/generate.*"), 5, 60),
    # 20 requests per minute for download endpoints under /api/
    (re.compile(r"^/api/.*/download.*"), 20, 60),
]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Basic dictionary-based rate limiter (no external dependencies)."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        client_ip = self._client_ip(request)
        now = time.time()

        for pattern, max_requests, window_sec in RATE_LIMITS:
            if pattern.match(request.url.path):
                key = f"{client_ip}:{pattern.pattern}"
                timestamps = _rate_buckets.get(key, [])
                # Evict stale entries
                timestamps = [t for t in timestamps if now - t < window_sec]
                if len(timestamps) >= max_requests:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "Rate limit exceeded",
                            "detail": f"Limit {max_requests} requests per {window_sec} seconds for this endpoint",
                        },
                    )
                timestamps.append(now)
                _rate_buckets[key] = timestamps
                break

        return await call_next(request)

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        client = request.client
        return client.host if client else "unknown"


def clear_rate_limits() -> None:
    """Clear all in-memory rate-limit buckets (useful in tests)."""
    _rate_buckets.clear()
