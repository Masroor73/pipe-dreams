"""Asset list, GeoJSON, detail: paging, filters, sorting, validation errors."""

import pytest

from app.schemas import AssetListData, Envelope, FeatureCollection


def _list(client, **params):
    resp = client.get("/api/assets", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_defaults(client):
    data = _list(client)
    assert data["plan"] == "v2"
    assert data["limit"] == 100
    assert data["offset"] == 0
    assert data["total"] == 80
    assert len(data["items"]) == 80
    ranks = [i["rank"] for i in data["items"]]
    assert ranks == sorted(ranks)


def test_paging(client):
    data = _list(client, limit=5, offset=5, sort="rank")
    assert data["limit"] == 5
    assert data["offset"] == 5
    assert data["total"] == 80
    assert [i["rank"] for i in data["items"]] == [6, 7, 8, 9, 10]


def test_offset_past_end_empty(client):
    data = _list(client, offset=1000)
    assert data["items"] == []
    assert data["total"] == 80


def test_selected_only(client):
    data = _list(client, selected_only=True)
    assert 0 < data["total"] < 80
    assert data["total"] == len(data["items"])
    assert all(i["selected"] for i in data["items"])


def test_evidence_confidence_filter(client):
    data = _list(client, evidence_confidence="LOW_VERIFY")
    assert data["total"] > 0
    assert all(i["evidence_confidence"] == "LOW_VERIFY" for i in data["items"])
    others = sum(_list(client, evidence_confidence=e)["total"] for e in ("HIGH", "MEDIUM"))
    assert others + data["total"] == 80


def test_consequence_tier_filter(client):
    data = _list(client, consequence_tier="T1")
    assert data["total"] > 0
    assert all(i["consequence_tier"] == "T1" for i in data["items"])
    assert _list(client, consequence_tier="T99")["total"] == 0


def test_sort_priority_score_desc(client):
    items = _list(client, sort="priority_score")["items"]
    scores = [i["priority_score"] for i in items if i["priority_score"] is not None]
    assert scores == sorted(scores, reverse=True)


def test_sort_length_desc(client):
    items = _list(client, sort="length_m")["items"]
    lengths = [i["length_m"] for i in items]
    assert lengths == sorted(lengths, reverse=True)


def test_plan_v1(client):
    data = _list(client, plan="v1")
    assert data["plan"] == "v1"
    assert data["total"] == 80
    assert [i["rank"] for i in data["items"]] == list(range(1, 81))


def test_plans_differ(client):
    v1 = {i["asset_id"]: i["rank"] for i in _list(client, plan="v1")["items"]}
    v2 = {i["asset_id"]: i["rank"] for i in _list(client, plan="v2")["items"]}
    assert set(v1) == set(v2)
    assert v1 != v2


def test_list_matches_schema(client):
    resp = client.get("/api/assets", params={"limit": 3})
    env = Envelope[AssetListData].model_validate(resp.json())
    assert len(env.data.items) == 3


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 501},
        {"offset": -1},
        {"plan": "v3"},
        {"sort": "bogus"},
        {"evidence_confidence": "NOPE"},
        {"limit": "abc"},
    ],
)
def test_invalid_params_422(client, params):
    resp = client.get("/api/assets", params=params)
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "invalid_query"
    assert body["error"]["message"]


def test_limit_boundaries_ok(client):
    assert client.get("/api/assets", params={"limit": 1}).status_code == 200
    assert client.get("/api/assets", params={"limit": 500}).status_code == 200


# ---- geojson ----


def test_geojson_route_not_captured_by_asset_id(client):
    resp = client.get("/api/assets/geojson")
    assert resp.status_code == 200
    assert resp.json()["data"]["type"] == "FeatureCollection"


def test_geojson_default_selected_only(client):
    resp = client.get("/api/assets/geojson")
    fc = Envelope[FeatureCollection].model_validate(resp.json()).data
    assert 0 < len(fc.features) < 80
    assert all(f.properties.selected for f in fc.features)
    assert all(f.id == f.properties.asset_id for f in fc.features)
    assert len(fc.features) == _list(client, selected_only=True)["total"]


def test_geojson_full_network(client):
    fc = client.get("/api/assets/geojson", params={"selected_only": False}).json()["data"]
    assert len(fc["features"]) == 80


def test_geojson_plan_v1(client):
    resp = client.get("/api/assets/geojson", params={"plan": "v1", "selected_only": False})
    assert resp.status_code == 200
    assert len(resp.json()["data"]["features"]) == 80


def test_geojson_invalid_plan_422(client):
    resp = client.get("/api/assets/geojson", params={"plan": "v3"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_query"


def test_geojson_geometry_lon_lat_order(client):
    fc = client.get("/api/assets/geojson", params={"selected_only": False}).json()["data"]
    for feat in fc["features"]:
        geom = feat["geometry"]
        assert geom["type"] in ("LineString", "MultiLineString")
        coords = geom["coordinates"]
        if geom["type"] == "MultiLineString":
            coords = [pt for line in coords for pt in line]
        for lon, lat in coords:
            assert -114.5 < lon < -113.5
            assert 50.5 < lat < 51.5


# ---- detail ----


def test_detail_seg_000001(client):
    resp = client.get("/api/assets/seg_000001")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["asset_id"] == "seg_000001"
    assert data["v1"]["rank"] >= 1
    assert data["v2"]["rank"] >= 1
    assert data["geometry"]["type"] in ("LineString", "MultiLineString")
    assert all(isinstance(s, str) for s in data["source_segment_ids"])


def test_detail_rank_change_non_null_for_rank_changes_asset(client):
    items = client.get("/api/rank-changes", params={"demo_only": False}).json()["data"]["items"]
    assert items
    item = items[0]
    detail = client.get(f"/api/assets/{item['asset_id']}").json()["data"]
    assert detail["rank_change"] is not None
    assert detail["rank_change"]["delta_rank"] == item["delta_rank"]
    assert detail["rank_change"]["show_in_demo"] == item["show_in_demo"]
    assert detail["v1"]["rank"] == item["rank_v1"]
    assert detail["v2"]["rank"] == item["rank_v2"]


def test_detail_rank_change_null_for_unchanged_asset(client):
    resp = client.get("/api/rank-changes", params={"demo_only": False, "limit": 500})
    changed = {i["asset_id"] for i in resp.json()["data"]["items"]}
    unchanged = next(f"seg_{n:06d}" for n in range(1, 81) if f"seg_{n:06d}" not in changed)
    detail = client.get(f"/api/assets/{unchanged}").json()["data"]
    assert "rank_change" in detail
    assert detail["rank_change"] is None


def test_unknown_asset_404(client):
    resp = client.get("/api/assets/does_not_exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "asset_not_found"
    assert "does_not_exist" in body["error"]["message"]
