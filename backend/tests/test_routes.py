"""Every route returns 200 with a schema-valid envelope."""

import pytest
from conftest import ENVELOPED_ROUTES

from app.schemas import (
    AssetDetail,
    AssetListData,
    AuditData,
    DataQualityData,
    Envelope,
    EscalationsData,
    FeatureCollection,
    HealthResponse,
    NotCoveredData,
    OverviewData,
    RankChangesData,
)

SCHEMAS = {
    "/api/overview": OverviewData,
    "/api/assets": AssetListData,
    "/api/assets/geojson": FeatureCollection,
    "/api/assets/seg_000001": AssetDetail,
    "/api/rank-changes": RankChangesData,
    "/api/audit": AuditData,
    "/api/escalations": EscalationsData,
    "/api/not-covered": NotCoveredData,
    "/api/data-quality": DataQualityData,
}

SERIES_KEYS = {
    "split",
    "origin_cutoff",
    "policy_id",
    "policy_type",
    "budget_pct",
    "asset_capture",
    "event_capture",
    "lift_vs_count_only",
    "ci_low",
    "ci_high",
    "matched_break_share",
    "pooled_gate_score",
    "accepted_vs_v1",
    "notes",
}


def test_schema_map_covers_all_routes():
    assert set(SCHEMAS) == set(ENVELOPED_ROUTES)


@pytest.mark.parametrize("route", ENVELOPED_ROUTES)
def test_route_ok_and_schema_valid(client, route):
    resp = client.get(route)
    assert resp.status_code == 200
    env = Envelope[SCHEMAS[route]].model_validate(resp.json())
    assert env.meta.synthetic is True
    assert env.meta.config_hash == "PLACEHOLDER"


@pytest.mark.parametrize("route", ENVELOPED_ROUTES)
def test_envelope_keys(client, route):
    body = client.get(route).json()
    assert set(body) == {"meta", "data"}
    assert body["meta"] == {"synthetic": True, "config_hash": "PLACEHOLDER"}


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "meta" not in body
    health = HealthResponse.model_validate(body)
    assert health.status == "ok"
    assert health.artifacts_loaded is True
    assert health.synthetic is True


def test_asset_detail_null_fields_present_not_omitted(client):
    found_null_reason = False
    for n in range(1, 81):
        data = client.get(f"/api/assets/seg_{n:06d}").json()["data"]
        assert {"revision_reason", "likelihood_score", "priority_score"} <= set(data["v1"])
        assert "rank_change" in data
        if data["v1"]["revision_reason"] is None:
            found_null_reason = True
    assert found_null_reason


def test_overview_series_organizer_cell_asset_capture_null(client):
    series = client.get("/api/overview").json()["data"]["series"]
    cells = [r for r in series if r["policy_id"] == "organizer_cell"]
    assert cells
    for row in cells:
        assert "asset_capture" in row
        assert row["asset_capture"] is None


def test_overview_series_all_keys_present(client):
    series = client.get("/api/overview").json()["data"]["series"]
    assert series
    for row in series:
        assert set(row) == SERIES_KEYS


def test_overview_selected_policy_c2(client):
    data = client.get("/api/overview").json()["data"]
    assert data["selected_policy_id"] == "C2"
