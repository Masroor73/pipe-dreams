from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.deps import Service
from app.core import constants as c
from app.schemas import (
    AssetDetail,
    AssetListData,
    Envelope,
    FeatureCollection,
    RankChangesData,
)
from app.schemas.common import EvidenceConfidence, PlanId

router = APIRouter()


@router.get("/assets", response_model=Envelope[AssetListData])
def list_assets(
    service: Service,
    plan: PlanId = "v2",
    selected_only: bool = False,
    evidence_confidence: EvidenceConfidence | None = None,
    consequence_tier: str | None = None,
    sort: Literal["rank", "priority_score", "length_m"] = "rank",
    limit: Annotated[int, Query(ge=1, le=c.ASSETS_LIMIT_MAX)] = c.ASSETS_LIMIT_DEFAULT,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    data = service.list_assets(
        plan, selected_only, evidence_confidence, consequence_tier, sort, limit, offset
    )
    return {"meta": service.meta, "data": data}


# Must be registered before /assets/{asset_id}.
@router.get("/assets/geojson", response_model=Envelope[FeatureCollection])
def assets_geojson(service: Service, plan: PlanId = "v2", selected_only: bool = True):
    return {"meta": service.meta, "data": service.geojson(plan, selected_only)}


@router.get("/assets/{asset_id}", response_model=Envelope[AssetDetail])
def asset_detail(asset_id: str, service: Service):
    return {"meta": service.meta, "data": service.asset_detail(asset_id)}


@router.get("/rank-changes", response_model=Envelope[RankChangesData])
def rank_changes(
    service: Service,
    demo_only: bool = True,
    limit: Annotated[int, Query(ge=1, le=c.RANK_CHANGES_LIMIT_MAX)] = c.RANK_CHANGES_LIMIT_DEFAULT,
):
    return {"meta": service.meta, "data": service.rank_changes(demo_only, limit)}
