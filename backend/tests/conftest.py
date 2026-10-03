"""Shared fixtures: synthetic artifact dir, app clients, broken artifact copies."""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_DIR = ROOT / "artifacts" / "synthetic"
ENVELOPED_ROUTES = (
    "/api/overview",
    "/api/assets",
    "/api/assets/geojson",
    "/api/assets/seg_000001",
    "/api/rank-changes",
    "/api/audit",
    "/api/escalations",
    "/api/not-covered",
    "/api/data-quality",
)


@pytest.fixture(scope="session")
def synthetic_dir() -> Path:
    return SYNTHETIC_DIR


@pytest.fixture(scope="session")
def client(synthetic_dir: Path) -> TestClient:
    return TestClient(create_app(synthetic_dir))


@pytest.fixture
def make_client() -> Callable[[Path], TestClient]:
    def _make(artifact_dir: Path) -> TestClient:
        return TestClient(create_app(artifact_dir))

    return _make


@pytest.fixture
def broken_copy(tmp_path: Path) -> Path:
    """A writable copy of the synthetic artifact dir that tests may corrupt."""
    dest = tmp_path / "artifacts"
    shutil.copytree(SYNTHETIC_DIR, dest)
    return dest
