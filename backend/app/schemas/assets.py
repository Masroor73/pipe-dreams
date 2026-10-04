"""Asset list, GeoJSON, detail and rank-change response models."""

from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.common import EvidenceConfidence, PlanId


class AssetListItem(BaseModel):
    asset_id: str
    rank: int
    selected: bool
    length_m: float
    priority_score: float | None
    consequence_tier: str
    evidence_confidence: EvidenceConfidence
    recommended_action: str
    latitude: float
    longitude: float


class AssetListData(BaseModel):
    plan: PlanId
    total: int
    limit: int
    offset: int
    items: list[AssetListItem]


class FeatureProperties(BaseModel):
    asset_id: str
    rank: int
    selected: bool
    consequence_tier: str
    evidence_confidence: EvidenceConfidence
    recommended_action: str


class Feature(BaseModel):
    type: Literal["Feature"]
    id: str
    geometry: dict[str, Any]
    properties: FeatureProperties


class FeatureCollection(BaseModel):
    type: Literal["FeatureCollection"]
    features: list[Feature]


class PlanFields(BaseModel):
    rank: int
    selected: bool
    likelihood_score: float | None
    priority_score: float | None
    recommended_action: str
    revision_reason: str | None


class RankChangeBrief(BaseModel):
    delta_rank: int
    reason_1: str | None
    reason_2: str | None
    show_in_demo: bool


class AssetDetail(BaseModel):
    asset_id: str
    source_segment_ids: list[str]
    length_m: float
    consequence_tier: str
    evidence_confidence: EvidenceConfidence
    association_quality: float | None
    rank_stability: float | None
    evidence_basis: str | None
    latitude: float
    longitude: float
    geometry: dict[str, Any]
    v1: PlanFields
    v2: PlanFields
    rank_change: RankChangeBrief | None


class RankChangeItem(BaseModel):
    asset_id: str
    rank_v1: int
    rank_v2: int
    delta_rank: int
    action_v1: str
    action_v2: str
    reason_1: str | None
    reason_2: str | None
    show_in_demo: bool


class RankChangesData(BaseModel):
    items: list[RankChangeItem]


__all__ = [
    "AssetDetail",
    "AssetListData",
    "AssetListItem",
    "Feature",
    "FeatureCollection",
    "FeatureProperties",
    "PlanFields",
    "PlanId",
    "RankChangeBrief",
    "RankChangeItem",
    "RankChangesData",
]
