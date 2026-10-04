"""Shared route dependencies."""

from typing import Annotated

from fastapi import Depends, Request

from app.services.artifact_service import ArtifactService, ArtifactsUnavailableError


def get_service(request: Request) -> ArtifactService:
    return request.app.state.artifacts


def get_loaded_service(
    service: Annotated[ArtifactService, Depends(get_service)],
) -> ArtifactService:
    if not service.loaded:
        raise ArtifactsUnavailableError(
            "Required artifacts are missing or failed validation; see /api/health."
        )
    return service


Service = Annotated[ArtifactService, Depends(get_loaded_service)]
