"""FastAPI application factory. Thin: serves precomputed artifacts only."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.settings import get_settings, resolve_artifact_dir
from app.services.artifact_service import (
    ArtifactService,
    ArtifactsUnavailableError,
    AssetNotFoundError,
)

logger = logging.getLogger(__name__)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _summarize_validation(exc: RequestValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()) if p != "query")
        parts.append(f"{loc}: {err.get('msg', 'invalid value')}")
    return "; ".join(parts) or "Invalid query parameters."


def create_app(artifact_dir: Path | None = None) -> FastAPI:
    settings = get_settings()
    chosen = artifact_dir if artifact_dir is not None else settings.artifact_dir
    service = ArtifactService(resolve_artifact_dir(chosen))
    for message in service.errors:
        logger.error("artifact load error: %s", message)

    app = FastAPI(title="Pipe Dreams API")
    app.state.artifacts = service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=[],
    )

    @app.exception_handler(RequestValidationError)
    async def _invalid_query(_: Request, exc: RequestValidationError):
        return _error(422, "invalid_query", _summarize_validation(exc))

    @app.exception_handler(ArtifactsUnavailableError)
    async def _unavailable(_: Request, exc: ArtifactsUnavailableError):
        return _error(503, "artifacts_unavailable", str(exc))

    @app.exception_handler(AssetNotFoundError)
    async def _asset_not_found(_: Request, exc: AssetNotFoundError):
        return _error(404, "asset_not_found", f"No asset with id '{exc.asset_id}' in plan v2.")

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return _error(404, "not_found", "Resource not found.")
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(api_router)
    return app


app = create_app()
