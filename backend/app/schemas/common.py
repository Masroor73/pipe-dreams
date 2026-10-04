"""Shared response models: envelope, errors, enum literals."""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

PolicyId = Literal["V1", "C1", "C2", "C3", "C4"]
BaselineId = Literal["count_only", "organizer_cell"]
PlanId = Literal["v1", "v2"]
Split = Literal["validation", "final", "confirmation"]
EvidenceConfidence = Literal["HIGH", "MEDIUM", "LOW_VERIFY"]
AuditEventType = Literal[
    "PLAN_V1", "EVALUATE", "DIAGNOSE", "TEST_CANDIDATE", "ACCEPT", "REJECT", "PLAN_V2", "ESCALATE"
]
CandidateDecision = Literal["ACCEPT", "REJECT"]

T = TypeVar("T")


class Meta(BaseModel):
    synthetic: bool
    config_hash: str


class Envelope(BaseModel, Generic[T]):
    meta: Meta
    data: T


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
