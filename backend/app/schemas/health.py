"""GET /api/health response (not enveloped)."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    artifacts_loaded: bool
    artifact_dir: str
    synthetic: bool | None
