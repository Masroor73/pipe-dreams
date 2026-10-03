"""Rank changes, audit log, escalations, not-covered, data-quality."""

from app.core.constants import CANDIDATE_EVENT_TYPES, CANDIDATE_KEYS, DATA_QUALITY_KEYS
from app.schemas import (
    AuditData,
    DataQualityData,
    Envelope,
    EscalationsData,
    NotCoveredData,
    RankChangesData,
)


def _rank_changes(client, **params):
    resp = client.get("/api/rank-changes", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["items"]


def test_rank_changes_demo_only_default(client):
    items = _rank_changes(client)
    assert len(items) >= 3
    assert all(i["show_in_demo"] is True for i in items)


def test_rank_changes_all_superset_of_demo(client):
    demo = _rank_changes(client)
    everything = _rank_changes(client, demo_only=False)
    assert len(everything) >= len(demo)
    assert {i["asset_id"] for i in demo} <= {i["asset_id"] for i in everything}


def test_rank_changes_limit(client):
    assert len(_rank_changes(client, limit=1)) == 1
    assert len(_rank_changes(client, demo_only=False, limit=2)) == 2


def test_rank_changes_delta_consistent(client):
    for i in _rank_changes(client, demo_only=False):
        assert i["delta_rank"] == i["rank_v2"] - i["rank_v1"]


def test_rank_changes_invalid_limit_422(client):
    for limit in (0, 501):
        resp = client.get("/api/rank-changes", params={"limit": limit})
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "invalid_query"


def test_rank_changes_null_reason_present(client):
    items = _rank_changes(client, demo_only=False)
    for i in items:
        assert "reason_1" in i
        assert "reason_2" in i
    assert any(i["reason_2"] is None for i in items)


def test_rank_changes_schema(client):
    resp = client.get("/api/rank-changes", params={"demo_only": False})
    Envelope[RankChangesData].model_validate(resp.json())


def test_audit_sorted_by_seq(client):
    resp = client.get("/api/audit")
    events = resp.json()["data"]["events"]
    assert events
    seqs = [e["seq"] for e in events]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)
    Envelope[AuditData].model_validate(resp.json())


def test_audit_candidate_non_null_exactly_on_candidate_events(client):
    events = client.get("/api/audit").json()["data"]["events"]
    for e in events:
        assert "candidate" in e
        if e["event_type"] in CANDIDATE_EVENT_TYPES:
            assert e["candidate"] is not None
            assert set(e["candidate"]) == set(CANDIDATE_KEYS)
        else:
            assert e["candidate"] is None
    assert any(e["candidate"] is not None for e in events)


def test_escalations_shape(client):
    resp = client.get("/api/escalations")
    Envelope[EscalationsData].model_validate(resp.json())
    for row in resp.json()["data"]["items"]:
        assert "response_deadline" in row
        assert "last_reviewed" in row


def test_not_covered_shape(client):
    resp = client.get("/api/not-covered")
    env = Envelope[NotCoveredData].model_validate(resp.json())
    assert len(env.data.items) >= 1


def test_data_quality_keys_exact(client):
    resp = client.get("/api/data-quality")
    assert set(resp.json()["data"]) == set(DATA_QUALITY_KEYS)
    Envelope[DataQualityData].model_validate(resp.json())
