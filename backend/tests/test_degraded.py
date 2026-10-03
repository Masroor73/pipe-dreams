"""Missing/corrupt artifacts: app starts, health degraded, enveloped routes 503."""

from conftest import ENVELOPED_ROUTES


def _assert_degraded(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "degraded"
    assert body["artifacts_loaded"] is False
    for route in ENVELOPED_ROUTES:
        resp = client.get(route)
        assert resp.status_code == 503, route
        assert resp.json()["error"]["code"] == "artifacts_unavailable", route
        assert resp.json()["error"]["message"]


def test_missing_dir(make_client, tmp_path):
    _assert_degraded(make_client(tmp_path / "nope"))


def test_empty_dir(make_client, tmp_path):
    _assert_degraded(make_client(tmp_path))


def test_corrupt_parquet(make_client, broken_copy):
    (broken_copy / "plan_v2.parquet").write_bytes(b"this is not parquet")
    _assert_degraded(make_client(broken_copy))


def test_deleted_audit_summary(make_client, broken_copy):
    (broken_copy / "audit_summary.json").unlink()
    _assert_degraded(make_client(broken_copy))


def test_corrupt_json(make_client, broken_copy):
    (broken_copy / "data_quality.json").write_text("{not json", encoding="utf-8")
    _assert_degraded(make_client(broken_copy))


def test_health_always_200(make_client, tmp_path):
    assert make_client(tmp_path / "nope").get("/api/health").status_code == 200
