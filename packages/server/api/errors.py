"""Unified error handling for API."""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ..storage.models import ErrorResponse, ErrorDetail


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with unified format."""
    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_ERROR",
    }

    error = ErrorResponse(
        error=ErrorDetail(
            code=error_codes.get(exc.status_code, "ERROR"),
            message=str(exc.detail),
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = exc.errors()
    first_error = errors[0] if errors else {"msg": "Validation error"}

    error = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message=first_error.get("msg", "Validation error"),
            details={
                "field": ".".join(str(loc) for loc in first_error.get("loc", [])),
                "errors": errors,
            },
        )
    )
    return JSONResponse(
        status_code=422,
        content=error.model_dump(),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    error = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        )
    )
    return JSONResponse(
        status_code=500,
        content=error.model_dump(),
    )
