"""Runtime settings (environment-overridable)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PIPE_DREAMS_")

    artifact_dir: Path = Path("artifacts/synthetic")
    cors_origins: list[str] = ["http://localhost:5173"]


def resolve_artifact_dir(p: Path) -> Path:
    """Relative paths are resolved against the repository root."""
    p = Path(p)
    return p if p.is_absolute() else REPO_ROOT / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
