"""GET /api/overview response models."""

from pydantic import BaseModel

from app.schemas.common import BaselineId, PolicyId, Split


class RevisionGate(BaseModel):
    min_origin_wins: int
    n_origins: int
    min_improvement_in_se: float
    bootstrap_block_km: float


class SeriesRow(BaseModel):
    split: Split
    origin_cutoff: str | None
    policy_id: PolicyId | BaselineId
    policy_type: str
    budget_pct: int
    asset_capture: float | None
    event_capture: float | None
    lift_vs_count_only: float | None
    ci_low: float | None
    ci_high: float | None
    matched_break_share: float | None
    pooled_gate_score: float | None
    accepted_vs_v1: bool | None
    notes: str | None


class OverviewData(BaseModel):
    git_commit: str
    git_tag: str
    v1_policy_id: PolicyId
    selected_policy_id: PolicyId
    v2_equals_v1: bool
    final_test_previously_viewed: bool
    budgets_pct: list[int]
    revision_gate: RevisionGate
    series: list[SeriesRow]
