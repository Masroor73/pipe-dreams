"""GET /api/audit response models."""

from typing import Any

from pydantic import BaseModel

from app.schemas.common import AuditEventType, CandidateDecision


class Candidate(BaseModel):
    candidate_id: str
    origin_wins: int
    n_origins: int
    pooled_v1_score: float
    pooled_candidate_score: float
    difference: float
    bootstrap_se: float
    required_delta: float
    decision: CandidateDecision
    reason: str


class AuditEvent(BaseModel):
    seq: int
    event_type: AuditEventType
    timestamp: str
    summary: str
    candidate: Candidate | None
    details: dict[str, Any]


class AuditData(BaseModel):
    events: list[AuditEvent]
