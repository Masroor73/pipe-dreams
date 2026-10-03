from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_service
from app.schemas import HealthResponse
from app.services.artifact_service import ArtifactService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(service: Annotated[ArtifactService, Depends(get_service)]):
    return service.health()
