"""FastAPI application for bounded, ephemeral financing projections."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.error_mapping import PublicApiError, error_response
from api.resource_limits import RequestBodyLimitMiddleware
from api.routes.financing import router


def create_app() -> FastAPI:
    """Create the public v1 API without attaching framework dependencies to domain."""
    app = FastAPI(
        title="Housing Finance GPS API",
        version="1.0.0",
        description=(
            "Versioned API for bounded ephemeral calculation projections. "
            "It does not create simulation results or replay evidence."
        ),
    )
    app.add_middleware(RequestBodyLimitMiddleware)
    app.include_router(router)

    async def handle_public_error(_: Request, error: Exception) -> JSONResponse:
        if not isinstance(error, PublicApiError):
            return error_response(500, "internal_error")
        return error_response(error.status_code, error.code)

    async def handle_validation_error(_: Request, __: Exception) -> JSONResponse:
        return error_response(422, "invalid_input")

    async def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
        return error_response(500, "internal_error")

    app.add_exception_handler(PublicApiError, handle_public_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
    return app


app = create_app()
