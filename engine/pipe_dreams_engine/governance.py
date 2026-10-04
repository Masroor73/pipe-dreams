"""Governance rules for Pipe Dreams inspection planning.

Governance is deliberately separate from predictive ranking.

Responsibilities:
- minimal diameter-based consequence proxy;
- evidence-quality components;
- validation-derived confidence thresholds;
- HIGH / MEDIUM / LOW_VERIFY assignment;
- VERIFY / INSPECT / CONDITION_ASSESS / MONITOR actions;
- escalation routing;
- explicit not-covered records.

Governance outputs must not feed back into the frozen V1/C1-C4
validation gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd


CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW_VERIFY = "LOW_VERIFY"

VALID_CONFIDENCE = {
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW_VERIFY,
}

CONSEQUENCE_T1 = "T1"
CONSEQUENCE_T2 = "T2"
CONSEQUENCE_T3 = "T3"

VALID_CONSEQUENCE_TIERS = {
    CONSEQUENCE_T1,
    CONSEQUENCE_T2,
    CONSEQUENCE_T3,
}

ACTION_VERIFY = "VERIFY"
ACTION_CONDITION_ASSESS = "CONDITION_ASSESS"
ACTION_INSPECT = "INSPECT"
ACTION_MONITOR = "MONITOR"

ESCALATION_OWNER = "Water Integrity Lead"
ESCALATION_REQUIRED_ACTION = "Verify asset record before scheduling"

# Frozen before corrected final test.
T1_MIN_DIAMETER_MM = 600.0
T2_MIN_DIAMETER_MM = 300.0


@dataclass(frozen=True)
class ConfidenceThresholds:
    """Validation-derived evidence-quality thresholds."""

    low_to_medium: float
    medium_to_high: float
    source: str = "validation_only"

    def __post_init__(self):
        if not np.isfinite(self.low_to_medium):
            raise ValueError(
                "low_to_medium must be finite"
            )

        if not np.isfinite(self.medium_to_high):
            raise ValueError(
                "medium_to_high must be finite"
            )

        if self.low_to_medium < 0:
            raise ValueError(
                "low_to_medium cannot be negative"
            )

        if self.medium_to_high > 1:
            raise ValueError(
                "medium_to_high cannot exceed 1"
            )

        if self.low_to_medium > self.medium_to_high:
            raise ValueError(
                "confidence thresholds are out of order"
            )


def consequence_tier(
    diameter,
) -> pd.Series:
    """Assign the frozen diameter-based consequence proxy.

    T1:
        diameter >= 600 mm

    T2:
        300 <= diameter < 600 mm

    T3:
        0 < diameter < 300 mm

    Missing, zero, negative, or non-numeric diameters are returned as NA
    so they can be explicitly routed to verification rather than silently
    treated as low consequence.
    """
    values = pd.to_numeric(
        pd.Series(diameter),
        errors="coerce",
    )

    result = pd.Series(
        pd.NA,
        index=values.index,
        dtype="object",
    )

    valid = (
        values.notna()
        & np.isfinite(
            values.to_numpy(dtype=float)
        )
        & (values > 0)
    )

    result.loc[
        valid
        & (values >= T1_MIN_DIAMETER_MM)
    ] = CONSEQUENCE_T1

    result.loc[
        valid
        & (values >= T2_MIN_DIAMETER_MM)
        & (values < T1_MIN_DIAMETER_MM)
    ] = CONSEQUENCE_T2

    result.loc[
        valid
        & (values < T2_MIN_DIAMETER_MM)
    ] = CONSEQUENCE_T3

    result.name = "consequence_tier"

    return result


def association_quality(
    frame: pd.DataFrame,
) -> pd.Series:
    """Calculate an auditable historical attribution-quality component.

    Uses only cutoff-safe historical evidence already present in the
    evidence snapshot.

    Quality combines:
    - ambiguity share among historically attributed breaks; and
    - mean nearest-line match distance.

    Distance quality declines linearly from 1 at 0 m to 0 at the frozen
    30 m attribution threshold.

    Assets with no historical attributed breaks receive 0.5 rather than
    an artificially perfect score: there is simply limited direct
    attribution evidence.
    """
    required = {
        "historical_break_count",
        "historical_ambiguous_break_count",
        "historical_mean_match_distance_m",
    }

    missing = required - set(
        frame.columns
    )

    if missing:
        raise ValueError(
            "association quality frame missing "
            f"required columns: {sorted(missing)}"
        )

    count = pd.to_numeric(
        frame["historical_break_count"],
        errors="coerce",
    )

    ambiguous = pd.to_numeric(
        frame[
            "historical_ambiguous_break_count"
        ],
        errors="coerce",
    )

    distance = pd.to_numeric(
        frame[
            "historical_mean_match_distance_m"
        ],
        errors="coerce",
    )

    if count.isna().any():
        raise ValueError(
            "historical_break_count contains invalid values"
        )

    if ambiguous.isna().any():
        raise ValueError(
            "historical_ambiguous_break_count contains invalid values"
        )

    if (count < 0).any() or (ambiguous < 0).any():
        raise ValueError(
            "historical evidence counts cannot be negative"
        )

    if (ambiguous > count).any():
        raise ValueError(
            "ambiguous break count cannot exceed "
            "historical break count"
        )

    quality = np.full(
        len(frame),
        0.5,
        dtype=float,
    )

    has_history = (
        count.to_numpy(dtype=float)
        > 0
    )

    if has_history.any():
        count_values = count.to_numpy(
            dtype=float
        )
        ambiguous_values = ambiguous.to_numpy(
            dtype=float
        )
        distance_values = distance.to_numpy(
            dtype=float
        )

        ambiguity_quality = np.ones(
            len(frame),
            dtype=float,
        )

        ambiguity_quality[
            has_history
        ] = (
            1.0
            - (
                ambiguous_values[
                    has_history
                ]
                / count_values[
                    has_history
                ]
            )
        )

        distance_quality = np.zeros(
            len(frame),
            dtype=float,
        )

        finite_distance = (
            has_history
            & np.isfinite(
                distance_values
            )
        )

        distance_quality[
            finite_distance
        ] = np.clip(
            1.0
            - (
                distance_values[
                    finite_distance
                ]
                / 30.0
            ),
            0.0,
            1.0,
        )

        # A historical match with missing distance metadata is not
        # treated as high quality.
        distance_quality[
            has_history
            & ~np.isfinite(
                distance_values
            )
        ] = 0.0

        quality[
            has_history
        ] = (
            ambiguity_quality[
                has_history
            ]
            + distance_quality[
                has_history
            ]
        ) / 2.0

    return pd.Series(
        np.clip(
            quality,
            0.0,
            1.0,
        ),
        index=frame.index,
        name="association_quality",
        dtype=float,
    )


def evidence_quality_score(
    association_quality_values: pd.Series,
    rank_stability_values: pd.Series,
) -> pd.Series:
    """Combine evidence components conservatively.

    Confidence is constrained by the weaker of:
    - historical attribution quality; and
    - ranking stability.

    This is an evidence-quality score, not a failure probability.
    """
    if not association_quality_values.index.equals(
        rank_stability_values.index
    ):
        raise ValueError(
            "association quality and rank stability "
            "indexes must match exactly"
        )

    association = pd.to_numeric(
        association_quality_values,
        errors="coerce",
    )

    stability = pd.to_numeric(
        rank_stability_values,
        errors="coerce",
    )

    if association.isna().any():
        raise ValueError(
            "association quality contains invalid values"
        )

    if stability.isna().any():
        raise ValueError(
            "rank stability contains invalid values"
        )

    if (
        (association < 0).any()
        or (association > 1).any()
        or (stability < 0).any()
        or (stability > 1).any()
    ):
        raise ValueError(
            "evidence components must be within [0, 1]"
        )

    values = np.minimum(
        association.to_numpy(dtype=float),
        stability.to_numpy(dtype=float),
    )

    return pd.Series(
        values,
        index=association.index,
        name="evidence_quality_score",
        dtype=float,
    )


def derive_confidence_thresholds(
    validation_quality_scores: pd.Series,
) -> ConfidenceThresholds:
    """Derive confidence thresholds from validation evidence only.

    Frozen rule:
    - lower tercile boundary: 1/3 quantile;
    - upper tercile boundary: 2/3 quantile.

    The caller is responsible for supplying validation-only assets.
    The corrected final-test assets must never be included here.
    """
    scores = pd.to_numeric(
        validation_quality_scores,
        errors="coerce",
    )

    if len(scores) == 0:
        raise ValueError(
            "validation quality scores cannot be empty"
        )

    if scores.isna().any():
        raise ValueError(
            "validation quality scores contain invalid values"
        )

    if (
        (scores < 0).any()
        or (scores > 1).any()
    ):
        raise ValueError(
            "validation quality scores must be within [0, 1]"
        )

    lower = float(
        scores.quantile(
            1.0 / 3.0
        )
    )
    upper = float(
        scores.quantile(
            2.0 / 3.0
        )
    )

    return ConfidenceThresholds(
        low_to_medium=lower,
        medium_to_high=upper,
    )


def assign_evidence_confidence(
    quality_scores: pd.Series,
    thresholds: ConfidenceThresholds,
) -> pd.Series:
    """Apply previously frozen confidence thresholds."""
    scores = pd.to_numeric(
        quality_scores,
        errors="coerce",
    )

    if scores.isna().any():
        raise ValueError(
            "quality scores contain invalid values"
        )

    if (
        (scores < 0).any()
        or (scores > 1).any()
    ):
        raise ValueError(
            "quality scores must be within [0, 1]"
        )

    result = pd.Series(
        CONFIDENCE_LOW_VERIFY,
        index=scores.index,
        dtype="object",
    )

    result.loc[
        scores
        >= thresholds.low_to_medium
    ] = CONFIDENCE_MEDIUM

    result.loc[
        scores
        >= thresholds.medium_to_high
    ] = CONFIDENCE_HIGH

    result.name = (
        "evidence_confidence"
    )

    return result


def recommended_action(
    evidence_confidence: str,
    selected: bool,
    consequence: str | None,
) -> str:
    """Return the frozen governance action."""
    if (
        evidence_confidence
        not in VALID_CONFIDENCE
    ):
        raise ValueError(
            "invalid evidence confidence "
            f"{evidence_confidence!r}"
        )

    if consequence is not None and consequence not in (
        VALID_CONSEQUENCE_TIERS
    ):
        raise ValueError(
            f"invalid consequence tier {consequence!r}"
        )

    if (
        evidence_confidence
        == CONFIDENCE_LOW_VERIFY
    ):
        return ACTION_VERIFY

    if not selected:
        return ACTION_MONITOR

    if consequence == CONSEQUENCE_T1:
        return ACTION_CONDITION_ASSESS

    return ACTION_INSPECT


def build_evidence_basis(
    frame: pd.DataFrame,
) -> pd.Series:
    """Create concise human-readable evidence descriptions."""
    required = {
        "historical_break_count",
        "historical_ambiguous_break_count",
        "historical_mean_match_distance_m",
    }

    missing = required - set(
        frame.columns
    )

    if missing:
        raise ValueError(
            f"evidence basis missing columns: "
            f"{sorted(missing)}"
        )

    output = []

    for _, row in frame.iterrows():
        count = int(
            row[
                "historical_break_count"
            ]
        )

        ambiguous = int(
            row[
                "historical_ambiguous_break_count"
            ]
        )

        distance = row[
            "historical_mean_match_distance_m"
        ]

        if count == 0:
            output.append(
                "No directly attributed historical breaks "
                "in the policy history window."
            )
            continue

        if pd.isna(distance):
            distance_text = (
                "mean match distance unavailable"
            )
        else:
            distance_text = (
                f"mean match distance "
                f"{float(distance):.1f} m"
            )

        output.append(
            f"{count} attributed historical breaks; "
            f"{ambiguous} ambiguous; "
            f"{distance_text}."
        )

    return pd.Series(
        output,
        index=frame.index,
        name="evidence_basis",
        dtype="object",
    )


def apply_governance(
    frame: pd.DataFrame,
    *,
    rank_stability: pd.Series,
    thresholds: ConfidenceThresholds,
    selected_column: str = "selected",
) -> pd.DataFrame:
    """Attach physical/governance fields to a planned asset frame."""
    required = {
        "diameter",
        selected_column,
    }

    missing = required - set(
        frame.columns
    )

    if missing:
        raise ValueError(
            f"governance frame missing columns: "
            f"{sorted(missing)}"
        )

    if not rank_stability.index.equals(
        frame.index
    ):
        raise ValueError(
            "rank stability index must exactly match frame index"
        )

    out = frame.copy()

    out["consequence_tier"] = consequence_tier(
        out["diameter"]
    )

    out["association_quality"] = (
        association_quality(out)
    )

    out["rank_stability"] = pd.to_numeric(
        rank_stability,
        errors="coerce",
    )

    quality = evidence_quality_score(
        out["association_quality"],
        out["rank_stability"],
    )

    out["evidence_confidence"] = (
        assign_evidence_confidence(
            quality,
            thresholds,
        )
    )

    # Invalid diameter is explicitly routed to verification.
    invalid_diameter = (
        out["consequence_tier"]
        .isna()
    )

    out.loc[
        invalid_diameter,
        "evidence_confidence",
    ] = CONFIDENCE_LOW_VERIFY

    out["evidence_basis"] = (
        build_evidence_basis(out)
    )

    selected = out[
        selected_column
    ].astype(bool)

    out["recommended_action"] = [
        recommended_action(
            conf,
            bool(sel),
            None
            if pd.isna(tier)
            else str(tier),
        )
        for conf, sel, tier
        in zip(
            out[
                "evidence_confidence"
            ],
            selected,
            out[
                "consequence_tier"
            ],
            strict=True,
        )
    ]

    return out


def build_escalation_rows(
    governed_plan: pd.DataFrame,
    *,
    start_date: date,
    last_reviewed: date,
) -> pd.DataFrame:
    """Build escalation.csv-compatible rows.

    Frozen escalation rule:
        T1 + LOW_VERIFY

    This is a governance routing rule, not a validated prediction.
    """
    required = {
        "asset_id",
        "rank",
        "consequence_tier",
        "evidence_confidence",
    }

    missing = required - set(
        governed_plan.columns
    )

    if missing:
        raise ValueError(
            f"escalation frame missing columns: "
            f"{sorted(missing)}"
        )

    selected = governed_plan[
        (
            governed_plan[
                "consequence_tier"
            ]
            == CONSEQUENCE_T1
        )
        & (
            governed_plan[
                "evidence_confidence"
            ]
            == CONFIDENCE_LOW_VERIFY
        )
    ].sort_values(
        [
            "rank",
            "asset_id",
        ]
    )

    rows = []

    for i, (_, row) in enumerate(
        selected.iterrows()
    ):
        rows.append(
            {
                "asset_id": row["asset_id"],
                "priority_rank": int(
                    row["rank"]
                ),
                "consequence_tier": (
                    row[
                        "consequence_tier"
                    ]
                ),
                "evidence_confidence": (
                    row[
                        "evidence_confidence"
                    ]
                ),
                "escalation_reason": (
                    "high consequence, low evidence confidence"
                ),
                "owner": ESCALATION_OWNER,
                "required_action": (
                    ESCALATION_REQUIRED_ACTION
                ),
                "response_deadline": (
                    start_date
                    + timedelta(
                        days=7 * i
                    )
                ).isoformat(),
                "status": "OPEN",
                "last_reviewed": (
                    last_reviewed.isoformat()
                ),
            }
        )

    columns = [
        "asset_id",
        "priority_rank",
        "consequence_tier",
        "evidence_confidence",
        "escalation_reason",
        "owner",
        "required_action",
        "response_deadline",
        "status",
        "last_reviewed",
    ]

    return pd.DataFrame(
        rows,
        columns=columns,
    )


def build_not_covered_records() -> pd.DataFrame:
    """Return explicit known coverage limitations for the real prototype."""
    rows = [
        {
            "coverage_issue_id": "NC-01",
            "scope": "retired_or_replaced_assets",
            "description": (
                "The current public pipe snapshot does not reconstruct "
                "all historically retired or replaced mains."
            ),
            "why_not_covered": (
                "Present-day geometry creates survivorship limitations "
                "for historical break attribution."
            ),
            "required_evidence": (
                "Historical asset-version or retirement inventory"
            ),
            "ui_severity": "HIGH",
            "source_note": (
                "Known limitation of current Calgary open-data snapshot."
            ),
        },
        {
            "coverage_issue_id": "NC-02",
            "scope": "hydraulic_connectivity",
            "description": (
                "Nearby break activity is spatial context only."
            ),
            "why_not_covered": (
                "The prototype does not contain a validated hydraulic "
                "network/topology model."
            ),
            "required_evidence": (
                "Authoritative hydraulic topology and connectivity model"
            ),
            "ui_severity": "MEDIUM",
            "source_note": (
                "Do not interpret proximity as hydraulic connectivity."
            ),
        },
        {
            "coverage_issue_id": "NC-03",
            "scope": "service_criticality",
            "description": (
                "Consequence is represented only by a diameter-based proxy."
            ),
            "why_not_covered": (
                "Population served, critical facilities, hydraulic "
                "importance, and outage consequences are not validated "
                "inputs in this prototype."
            ),
            "required_evidence": (
                "Validated service-criticality and consequence datasets"
            ),
            "ui_severity": "MEDIUM",
            "source_note": (
                "No invented people-served or savings estimates are used."
            ),
        },
        {
            "coverage_issue_id": "NC-04",
            "scope": "invalid_diameter",
            "description": (
                "Some source pipe records have non-positive or unusable "
                "diameter values."
            ),
            "why_not_covered": (
                "A valid diameter consequence tier cannot be assigned."
            ),
            "required_evidence": (
                "Verified asset diameter from authoritative utility records"
            ),
            "ui_severity": "MEDIUM",
            "source_note": (
                "Invalid diameter records are routed to LOW_VERIFY."
            ),
        },
    ]

    return pd.DataFrame(rows)
    