"""Escalation, not-covered and data-quality response models."""

from pydantic import BaseModel

from app.schemas.common import EvidenceConfidence


class EscalationItem(BaseModel):
    asset_id: str
    priority_rank: int
    consequence_tier: str
    evidence_confidence: EvidenceConfidence
    escalation_reason: str
    owner: str
    required_action: str
    response_deadline: str | None
    status: str
    last_reviewed: str | None


class EscalationsData(BaseModel):
    items: list[EscalationItem]


class NotCoveredItem(BaseModel):
    coverage_issue_id: str
    scope: str
    description: str
    why_not_covered: str
    required_evidence: str
    ui_severity: str
    source_note: str


class NotCoveredData(BaseModel):
    items: list[NotCoveredItem]


class InactiveSensitivity(BaseModel):
    included_capture_5pct: float
    excluded_capture_5pct: float


class DataQualityData(BaseModel):
    rows_dropped_missing_coordinates: int
    match_rate_by_origin: dict[str, float]
    match_rate_by_era: dict[str, float]
    unmatched_share_by_era: dict[str, float]
    unreachable_final_test_share: float
    future_year_pipe_rows_excluded: int
    planned_rows_excluded: int
    inactive_sensitivity: InactiveSensitivity
    retired_status_strata: dict[str, float]
    notes: list[str]
