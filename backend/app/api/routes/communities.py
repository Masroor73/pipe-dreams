from fastapi import APIRouter

from app.api.deps import CommunityService, Service
from app.schemas import (
    CommunitiesData,
    CommunityFeatureCollection,
    Envelope,
)

router = APIRouter()


@router.get(
    "/communities",
    response_model=Envelope[CommunitiesData],
)
def list_communities(
    service: Service,
    community_service: CommunityService,
    cutoff_year: int | None = None,
):
    return {
        "meta": service.meta,
        "data": community_service.list_communities(
            cutoff_year
        ),
    }


@router.get(
    "/communities/geojson",
    response_model=Envelope[
        CommunityFeatureCollection
    ],
)
def communities_geojson(
    service: Service,
    community_service: CommunityService,
    cutoff_year: int | None = None,
):
    return {
        "meta": service.meta,
        "data": community_service.geojson(
            cutoff_year
        ),
    }