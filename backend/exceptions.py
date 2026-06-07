"""Custom exceptions and global error response formatting for CineForge."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

ENV = os.getenv("CINEFORGE_ENV", "development")


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found", detail: str = "") -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)


class ValidationError(Exception):
    """Raised when input fails business-logic validation."""

    def __init__(self, message: str = "Validation failed", detail: str = "") -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)


class ConflictError(Exception):
    """Raised when an operation conflicts with the current state."""

    def __init__(self, message: str = "Conflict detected", detail: str = "") -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)


def _safe_error_payload(error: str, detail: str | Any = "") -> dict[str, Any]:
    """Return a consistently-shaped error payload."""
    return {"error": error, "detail": detail}


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=_safe_error_payload(exc.message, exc.detail or "Not found"),
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=_safe_error_payload(exc.message, exc.detail or "Bad request"),
    )


async def conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=_safe_error_payload(exc.message, exc.detail or "Conflict"),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Wrap FastAPI HTTPException so the response always includes *error* + *detail*."""
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    error_msg = "Request failed"
    if exc.status_code == 404:
        error_msg = "Not found"
    elif exc.status_code == 400:
        error_msg = "Bad request"
    elif exc.status_code == 401:
        error_msg = "Unauthorized"
    elif exc.status_code == 403:
        error_msg = "Forbidden"
    elif exc.status_code == 409:
        error_msg = "Conflict"
    elif exc.status_code == 429:
        error_msg = "Rate limit exceeded"
    elif exc.status_code == 502:
        error_msg = "Upstream service error"
    elif exc.status_code == 507:
        error_msg = "Insufficient storage"
    elif exc.status_code >= 500:
        error_msg = "Internal server error"
    return JSONResponse(
        status_code=exc.status_code,
        content=_safe_error_payload(error_msg, detail),
        headers=getattr(exc, "headers", None) or {},
    )


async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Standardise Pydantic / FastAPI validation errors."""
    errors = exc.errors()
    first_msg = errors[0]["msg"] if errors else "Validation failed"
    return JSONResponse(
        status_code=422,
        content=_safe_error_payload("Validation failed", first_msg),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: log the exception and return a safe 500 JSON (no stack traces in production)."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    detail = str(exc) if ENV == "development" else "An unexpected error occurred"
    return JSONResponse(
        status_code=500,
        content=_safe_error_payload("Internal server error", detail),
    )
