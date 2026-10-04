"""Community intelligence response models."""

from typing import Any, Literal

from pydantic import BaseModel


class CommunityItem(BaseModel):
    community_id: str
    community_name: str
    pipe_length_km: float
    historical_break_count: int
    historical_breaks_per_km: float | None
    population: float | None
    equity_index: float | None
    equity_geography_status: Literal[
        "NOT_ASSESSED",
        "DIRECT",
        "AREA_WEIGHTED",
        "UNAVAILABLE",
    ]
    data_quality_flags: list[str]


class CommunitiesData(BaseModel):
    cutoff_year: int
    items: list[CommunityItem]


class CommunityFeatureProperties(BaseModel):
    community_id: str
    community_name: str
    pipe_length_km: float
    historical_break_count: int
    historical_breaks_per_km: float | None
    population: float | None
    equity_index: float | None
    equity_geography_status: Literal[
        "NOT_ASSESSED",
        "DIRECT",
        "AREA_WEIGHTED",
        "UNAVAILABLE",
    ]
    data_quality_flags: list[str]


class CommunityFeature(BaseModel):
    type: Literal["Feature"]
    id: str
    geometry: dict[str, Any]
    properties: CommunityFeatureProperties


class CommunityFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"]
    features: list[CommunityFeature]


__all__ = [
    "CommunitiesData",
    "CommunityFeature",
    "CommunityFeatureCollection",
    "CommunityFeatureProperties",
    "CommunityItem",
]