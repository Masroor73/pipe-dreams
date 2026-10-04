"""Autonomous V1-to-V2 policy revision gate.

Authoritative sources:
    docs/EXPERIMENT_PROTOCOL.md
    docs/ARTIFACT_SCHEMAS.md
    docs/DECISIONS.md
    config/policy_config.DRAFT.yaml

The agent does not train models, construct evidence, or inspect the final
test window. It consumes validation-origin evaluations produced elsewhere
and applies the frozen revision gate:

1. candidate beats V1 on at least 2 of 3 validation origins; and
2. pooled candidate improvement is at least one pooled 1-km spatial-block
   bootstrap standard error.

If multiple candidates pass, the one with the highest pooled validation
score becomes V2.

If none pass, V2 equals V1.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

import numpy as np

from pipe_dreams_engine.evaluation import (
    DEFAULT_BOOTSTRAP_REPS,
    DEFAULT_BOOTSTRAP_SEED,
    VALIDATION_CUTOFFS,
    OriginEvaluation,
    paired_spatial_bootstrap_improvement_se,
    pooled_validation_score,
)
from pipe_dreams_engine.planner import (
    RANK_PER_ASSET,
    RANK_PER_METRE,
)


V1_POLICY_ID = "V1"

MIN_ORIGIN_WINS = 2
N_VALIDATION_ORIGINS = 3
MIN_IMPROVEMENT_IN_SE = 1.0
BOOTSTRAP_BLOCK_KM = 1.0


@dataclass(frozen=True)
class PolicySpec:
    """Frozen policy definition."""

    policy_id: str
    history_window: str
    recency_decay: str
    ranking_normalization: str

    @property
    def ranking_mode(self) -> str:
        """Translate config terminology to planner terminology."""
        if self.ranking_normalization == "per_asset":
            return RANK_PER_ASSET

        if self.ranking_normalization == "per_meter":
            return RANK_PER_METRE

        raise ValueError(
            "unsupported ranking normalization "
            f"{self.ranking_normalization!r}"
        )


V1_POLICY = PolicySpec(
    policy_id=V1_POLICY_ID,
    history_window="full",
    recency_decay="none",
    ranking_normalization="per_asset",
)

CANDIDATE_POLICIES = (
    PolicySpec(
        policy_id="C1",
        history_window="2000_plus",
        recency_decay="none",
        ranking_normalization="per_asset",
    ),
    PolicySpec(
        policy_id="C2",
        history_window="full",
        recency_decay="hl10",
        ranking_normalization="per_asset",
    ),
    PolicySpec(
        policy_id="C3",
        history_window="full",
        recency_decay="none",
        ranking_normalization="per_meter",
    ),
    PolicySpec(
        policy_id="C4",
        history_window="2000_plus",
        recency_decay="hl10",
        ranking_normalization="per_asset",
    ),
)

POLICY_BY_ID = {
    V1_POLICY.policy_id: V1_POLICY,
    **{
        policy.policy_id: policy
        for policy in CANDIDATE_POLICIES
    },
}


@dataclass(frozen=True)
class CandidateDecision:
    """Frozen-gate result for one challenger versus V1."""

    candidate_id: str
    origin_wins: int
    n_origins: int
    pooled_v1_score: float
    pooled_candidate_score: float
    difference: float
    bootstrap_se: float
    required_delta: float
    decision: str
    reason: str

    @property
    def accepted(self) -> bool:
        return self.decision == "ACCEPT"

    def to_candidate_payload(self) -> dict:
        """Exact candidate object required by agent_log.jsonl schema."""
        return {
            "candidate_id": self.candidate_id,
            "origin_wins": self.origin_wins,
            "n_origins": self.n_origins,
            "pooled_v1_score": self.pooled_v1_score,
            "pooled_candidate_score": self.pooled_candidate_score,
            "difference": self.difference,
            "bootstrap_se": self.bootstrap_se,
            "required_delta": self.required_delta,
            "decision": self.decision,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class V2Selection:
    """Result of the complete autonomous revision process."""

    selected_policy_id: str
    v1_policy_id: str
    v2_equals_v1: bool
    decisions: tuple[CandidateDecision, ...]


def _origin_map(
    origins,
) -> dict[int, OriginEvaluation]:
    origins = tuple(origins)

    result = {
        origin.cutoff_year: origin
        for origin in origins
    }

    if len(result) != len(origins):
        raise ValueError(
            "duplicate validation cutoff years"
        )

    required = set(VALIDATION_CUTOFFS)

    if set(result) != required:
        missing = sorted(
            required - set(result)
        )
        extra = sorted(
            set(result) - required
        )

        raise ValueError(
            "validation origins must be exactly "
            f"{list(VALIDATION_CUTOFFS)}; "
            f"missing={missing}, extra={extra}"
        )

    return result


def evaluate_candidate_gate(
    candidate_id: str,
    v1_origins,
    candidate_origins,
    *,
    bootstrap_reps: int = DEFAULT_BOOTSTRAP_REPS,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    minimum_origin_wins: int = MIN_ORIGIN_WINS,
    minimum_improvement_in_se: float = MIN_IMPROVEMENT_IN_SE,
) -> CandidateDecision:
    """Evaluate one frozen challenger independently against V1."""
    if candidate_id not in {
        policy.policy_id
        for policy in CANDIDATE_POLICIES
    }:
        raise ValueError(
            f"unknown frozen candidate {candidate_id!r}"
        )

    if minimum_origin_wins < 1:
        raise ValueError(
            "minimum_origin_wins must be positive"
        )

    if minimum_origin_wins > len(
        VALIDATION_CUTOFFS
    ):
        raise ValueError(
            "minimum_origin_wins cannot exceed "
            "number of validation origins"
        )

    if (
        not np.isfinite(
            minimum_improvement_in_se
        )
        or minimum_improvement_in_se < 0
    ):
        raise ValueError(
            "minimum_improvement_in_se must be "
            "finite and non-negative"
        )

    v1_map = _origin_map(
        v1_origins
    )
    candidate_map = _origin_map(
        candidate_origins
    )

    pooled_v1 = pooled_validation_score(
        tuple(v1_map.values())
    )
    pooled_candidate = pooled_validation_score(
        tuple(candidate_map.values())
    )

    origin_wins = sum(
        candidate_map[cutoff].per_origin_score
        > v1_map[cutoff].per_origin_score
        for cutoff in VALIDATION_CUTOFFS
    )

    bootstrap = (
        paired_spatial_bootstrap_improvement_se(
            [
                v1_map[cutoff]
                for cutoff in VALIDATION_CUTOFFS
            ],
            [
                candidate_map[cutoff]
                for cutoff in VALIDATION_CUTOFFS
            ],
            reps=bootstrap_reps,
            seed=bootstrap_seed,
        )
    )

    difference = float(
        pooled_candidate
        - pooled_v1
    )

    required_delta = float(
        minimum_improvement_in_se
        * bootstrap.standard_error
    )

    wins_gate = (
        origin_wins
        >= minimum_origin_wins
    )

    # "Improve pooled mean" means the difference must genuinely be
    # positive even in the degenerate case where bootstrap SE is zero.
    delta_gate = (
        difference > 0
        and difference + 1e-15
        >= required_delta
    )

    accepted = (
        wins_gate
        and delta_gate
    )

    if accepted:
        decision = "ACCEPT"
        reason = (
            f"passed frozen gate: won {origin_wins}/"
            f"{len(VALIDATION_CUTOFFS)} origins and "
            f"pooled improvement {difference:.6f} "
            f">= required delta {required_delta:.6f}"
        )
    else:
        decision = "REJECT"

        failures = []

        if not wins_gate:
            failures.append(
                f"origin wins {origin_wins}/"
                f"{len(VALIDATION_CUTOFFS)} "
                f"< required {minimum_origin_wins}"
            )

        if not delta_gate:
            failures.append(
                f"pooled improvement {difference:.6f} "
                f"< required positive delta "
                f"{required_delta:.6f}"
            )

        reason = (
            "failed frozen gate: "
            + "; ".join(failures)
        )

    return CandidateDecision(
        candidate_id=candidate_id,
        origin_wins=int(origin_wins),
        n_origins=len(
            VALIDATION_CUTOFFS
        ),
        pooled_v1_score=float(
            pooled_v1
        ),
        pooled_candidate_score=float(
            pooled_candidate
        ),
        difference=difference,
        bootstrap_se=float(
            bootstrap.standard_error
        ),
        required_delta=required_delta,
        decision=decision,
        reason=reason,
    )


def evaluate_revision_gate(
    v1_origins,
    candidate_origins: Mapping[
        str,
        tuple[OriginEvaluation, ...]
        | list[OriginEvaluation],
    ],
    *,
    bootstrap_reps: int = DEFAULT_BOOTSTRAP_REPS,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> V2Selection:
    """Run all four frozen candidate revisions and select V2."""
    expected_ids = {
        policy.policy_id
        for policy in CANDIDATE_POLICIES
    }

    supplied_ids = set(
        candidate_origins
    )

    if supplied_ids != expected_ids:
        missing = sorted(
            expected_ids
            - supplied_ids
        )
        extra = sorted(
            supplied_ids
            - expected_ids
        )

        raise ValueError(
            "candidate set must exactly match "
            "the four frozen revisions; "
            f"missing={missing}, extra={extra}"
        )

    decisions = []

    for policy in CANDIDATE_POLICIES:
        decision = evaluate_candidate_gate(
            policy.policy_id,
            v1_origins,
            candidate_origins[
                policy.policy_id
            ],
            bootstrap_reps=bootstrap_reps,
            bootstrap_seed=bootstrap_seed,
        )

        decisions.append(
            decision
        )

    accepted = [
        decision
        for decision in decisions
        if decision.accepted
    ]

    if not accepted:
        selected_policy_id = (
            V1_POLICY_ID
        )
        v2_equals_v1 = True
    else:
        # Frozen rule:
        # highest pooled validation score wins.
        #
        # Candidate ID is a deterministic tie-break only.
        selected = sorted(
            accepted,
            key=lambda decision: (
                -decision.pooled_candidate_score,
                decision.candidate_id,
            ),
        )[0]

        selected_policy_id = (
            selected.candidate_id
        )
        v2_equals_v1 = False

    return V2Selection(
        selected_policy_id=selected_policy_id,
        v1_policy_id=V1_POLICY_ID,
        v2_equals_v1=v2_equals_v1,
        decisions=tuple(decisions),
    )


def _utc_timestamp() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def build_agent_log(
    selection: V2Selection,
    *,
    timestamp: str | None = None,
) -> list[dict]:
    """Build audit-ready agent events matching ARTIFACT_SCHEMAS.md.

    Writing JSONL to disk belongs to the later artifact-generation layer.
    """
    ts = (
        timestamp
        if timestamp is not None
        else _utc_timestamp()
    )

    events = []
    seq = 1

    events.append(
        {
            "seq": seq,
            "event_type": "PLAN_V1",
            "timestamp": ts,
            "summary": (
                "Declared frozen V1 policy."
            ),
            "candidate": None,
            "details": {
                "policy_id": (
                    V1_POLICY.policy_id
                ),
                "history_window": (
                    V1_POLICY.history_window
                ),
                "recency_decay": (
                    V1_POLICY.recency_decay
                ),
                "ranking_normalization": (
                    V1_POLICY.ranking_normalization
                ),
            },
        }
    )
    seq += 1

    for decision in selection.decisions:
        candidate = (
            decision.to_candidate_payload()
        )

        events.append(
            {
                "seq": seq,
                "event_type": (
                    "TEST_CANDIDATE"
                ),
                "timestamp": ts,
                "summary": (
                    f"Tested "
                    f"{decision.candidate_id} "
                    "against frozen V1."
                ),
                "candidate": candidate,
                "details": {},
            }
        )
        seq += 1

        events.append(
            {
                "seq": seq,
                "event_type": (
                    decision.decision
                ),
                "timestamp": ts,
                "summary": (
                    f"{decision.decision}: "
                    f"{decision.candidate_id}."
                ),
                "candidate": candidate,
                "details": {},
            }
        )
        seq += 1

    events.append(
        {
            "seq": seq,
            "event_type": "PLAN_V2",
            "timestamp": ts,
            "summary": (
                "Selected V2 policy "
                f"{selection.selected_policy_id}."
            ),
            "candidate": None,
            "details": {
                "selected_policy_id": (
                    selection.selected_policy_id
                ),
                "v1_policy_id": (
                    selection.v1_policy_id
                ),
                "v2_equals_v1": (
                    selection.v2_equals_v1
                ),
            },
        }
    )

    return events
    