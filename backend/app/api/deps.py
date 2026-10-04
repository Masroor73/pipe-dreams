"""Shared route dependencies."""

from typing import Annotated

from fastapi import Depends, Request

from app.services.artifact_service import (
    ArtifactService,
    ArtifactsUnavailableError,
)
from app.services.community_artifact_service import (
    CommunityArtifactService,
    CommunityArtifactsUnavailableError,
)


def get_service(
    request: Request,
) -> ArtifactService:
    return request.app.state.artifacts


def get_loaded_service(
    service: Annotated[
        ArtifactService,
        Depends(get_service),
    ],
) -> ArtifactService:
    if not service.loaded:
        raise ArtifactsUnavailableError(
            "Required artifacts are missing or failed validation; "
            "see /api/health."
        )

    return service


def get_community_service(
    request: Request,
) -> CommunityArtifactService:
    return request.app.state.community_artifacts


def get_loaded_community_service(
    service: Annotated[
        CommunityArtifactService,
        Depends(get_community_service),
    ],
) -> CommunityArtifactService:
    if not service.loaded:
        raise CommunityArtifactsUnavailableError(
            "Community artifacts are missing or failed validation."
        )

    return service


Service = Annotated[
    ArtifactService,
    Depends(get_loaded_service),
]

CommunityService = Annotated[
    CommunityArtifactService,
    Depends(get_loaded_community_service),
]

OptionalCommunityService = Annotated[
    CommunityArtifactService,
    Depends(get_community_service),
]