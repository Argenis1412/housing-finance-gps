"""FastAPI application for bounded, ephemeral financing projections."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.error_mapping import PublicApiError, comparison_error_response, error_response
from api.resource_limits import RequestBodyLimitMiddleware, is_comparison_operation
from api.routes.financing import router
from api.routes.comparisons import router as comparison_router
from api.routes.saved_comparisons import router as saved_comparison_router
from application.saved_comparisons import ComparisonRepository
from infrastructure.sqlite_comparisons import SqliteComparisonRepository


def create_app(*, comparison_repository: ComparisonRepository | None = None) -> FastAPI:
    """Create the public v1 API without attaching framework dependencies to domain."""
    app = FastAPI(
        title="Housing Finance GPS API",
        version="1.2.0",
        description=(
            "Versioned financing projections and explicit transient synthetic "
            "comparison simulations with explicit local evidence persistence. No HTTP replay."
        ),
    )
    app.add_middleware(RequestBodyLimitMiddleware)
    app.include_router(router)
    app.include_router(comparison_router)
    app.include_router(saved_comparison_router)
    app.state.comparison_repository = comparison_repository if comparison_repository is not None else SqliteComparisonRepository()

    def respond(request: Request, status: int, code: str) -> JSONResponse:
        factory = comparison_error_response if is_comparison_operation(request.method, request.url.path) else error_response
        return factory(status, code)

    async def handle_public_error(request: Request, error: Exception) -> JSONResponse:
        if not isinstance(error, PublicApiError):
            return respond(request, 500, "internal_error")
        return respond(request, error.status_code, error.code)

    async def handle_validation_error(request: Request, __: Exception) -> JSONResponse:
        return respond(request, 422, "invalid_input")

    async def handle_unexpected_error(request: Request, __: Exception) -> JSONResponse:
        return respond(request, 500, "internal_error")

    app.add_exception_handler(PublicApiError, handle_public_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
    return app


app = create_app()
