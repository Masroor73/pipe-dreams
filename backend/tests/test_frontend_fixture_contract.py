"""Cross-stack drift guard: frontend fixtures must have the same shape as live API responses.

The frontend runs on fixtures by default, so a fixture that drifts from the real API hides
contract mismatches until integration. This compares key sets and JSON value kinds, recursively,
between each fixture in frontend/src/fixtures and the corresponding synthetic-artifact response.
"""

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "frontend" / "src" / "fixtures"

# Free-form maps whose keys legitimately differ between datasets.
FREE_FORM_SUFFIXES = (".details", "_by_origin", "_by_era", ".retired_status_strata")

ROUTE_FIXTURES = [
    ("/api/health", "health.json"),
    ("/api/overview", "overview.json"),
    ("/api/assets", "assets.json"),
    ("/api/assets/geojson?plan=v1", "assets_geojson_v1.json"),
    ("/api/assets/geojson?plan=v2", "assets_geojson_v2.json"),
    ("/api/rank-changes", "rank_changes.json"),
    ("/api/audit", "audit.json"),
    ("/api/escalations", "escalations.json"),
    ("/api/not-covered", "not_covered.json"),
    ("/api/data-quality", "data_quality.json"),
]


def _kind(v: object) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int | float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    return "object"


def _diff(api: object, fx: object, path: str, out: list[str]) -> None:
    ka, kf = _kind(api), _kind(fx)
    if "null" in (ka, kf):
        return  # nullable fields may be null on either side
    if ka != kf:
        out.append(f"{path}: api={ka} fixture={kf}")
        return
    if ka == "object":
        if path.endswith(FREE_FORM_SUFFIXES):
            return
        assert isinstance(api, dict) and isinstance(fx, dict)
        for k in sorted(set(api) - set(fx)):
            out.append(f"{path}.{k}: missing in fixture")
        for k in sorted(set(fx) - set(api)):
            out.append(f"{path}.{k}: not in API response")
        for k in set(api) & set(fx):
            _diff(api[k], fx[k], f"{path}.{k}", out)
    elif ka == "array" and api and fx:
        assert isinstance(api, list) and isinstance(fx, list)
        for i, item in enumerate(api):
            _diff(item, fx[min(i, len(fx) - 1)], f"{path}[]", out)


def _load(name: str) -> object:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("route", "fixture"), ROUTE_FIXTURES)
def test_fixture_matches_api_shape(client, route, fixture):
    resp = client.get(route)
    assert resp.status_code == 200
    problems: list[str] = []
    _diff(resp.json(), _load(fixture), route, problems)
    assert not problems, "\n".join(problems)


def test_asset_detail_fixture_matches_api_shape(client):
    details = _load("asset_details.json")
    assert isinstance(details, dict) and details
    problems: list[str] = []
    for asset_id, fx in details.items():
        resp = client.get(f"/api/assets/{asset_id}")
        assert resp.status_code == 200, asset_id
        _diff(resp.json()["data"], fx, f"/api/assets/{asset_id}", problems)
    assert not problems, "\n".join(problems)
