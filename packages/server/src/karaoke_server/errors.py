"""Errors the API answers with: a status, a stable code the web translates, and a message."""

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, detail: str, **extra: Any) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail
        self.extra = extra


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return JSONResponse({"detail": exc.detail, "code": exc.code, **exc.extra}, exc.status)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """A body or a parameter that does not fit the API: the same shape as every other error."""
    assert isinstance(exc, RequestValidationError)
    issues = [
        {"path": ".".join(str(part) for part in error.get("loc", ())), "message": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        {"detail": "The request is not valid", "code": "invalid_request", "issues": issues}, 422
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Routing errors (no such path, wrong method), with a code like the API's own."""
    assert isinstance(exc, HTTPException)
    codes = {404: "not_found", 405: "method_not_allowed"}
    return JSONResponse(
        {"detail": str(exc.detail), "code": codes.get(exc.status_code, "http_error")},
        exc.status_code,
        headers=exc.headers,
    )
