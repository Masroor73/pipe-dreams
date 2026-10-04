"""Settings env overrides and CORS behaviour."""

from conftest import SYNTHETIC_DIR

from app.core.settings import REPO_ROOT, Settings, resolve_artifact_dir

ALLOWED = "http://localhost:5173"
FOREIGN = "http://evil.example.com"


def test_env_override_artifact_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("PIPE_DREAMS_ARTIFACT_DIR", str(tmp_path))
    assert Settings().artifact_dir == tmp_path


def test_default_artifact_dir(monkeypatch):
    monkeypatch.delenv("PIPE_DREAMS_ARTIFACT_DIR", raising=False)
    assert resolve_artifact_dir(Settings().artifact_dir) == SYNTHETIC_DIR


def test_relative_path_resolves_under_repo_root():
    resolved = resolve_artifact_dir("artifacts/synthetic")
    assert resolved == REPO_ROOT / "artifacts" / "synthetic"
    assert resolved.is_absolute()


def test_absolute_path_unchanged(tmp_path):
    assert resolve_artifact_dir(tmp_path) == tmp_path


def test_default_cors_origins(monkeypatch):
    monkeypatch.delenv("PIPE_DREAMS_CORS_ORIGINS", raising=False)
    origins = Settings().cors_origins
    assert ALLOWED in origins
    assert "*" not in origins


def test_cors_origins_env_json(monkeypatch):
    monkeypatch.setenv("PIPE_DREAMS_CORS_ORIGINS", '["http://a.test"]')
    assert Settings().cors_origins == ["http://a.test"]


def test_cors_allowed_origin_get(client):
    resp = client.get("/api/health", headers={"Origin": ALLOWED})
    assert resp.headers.get("access-control-allow-origin") == ALLOWED


def test_cors_foreign_origin_get(client):
    resp = client.get("/api/health", headers={"Origin": FOREIGN})
    assert "access-control-allow-origin" not in resp.headers


def test_cors_preflight_allowed(client):
    resp = client.options(
        "/api/assets",
        headers={"Origin": ALLOWED, "Access-Control-Request-Method": "GET"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == ALLOWED


def test_cors_preflight_foreign(client):
    resp = client.options(
        "/api/assets",
        headers={"Origin": FOREIGN, "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in resp.headers
