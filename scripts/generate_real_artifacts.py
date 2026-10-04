"""Generate the 10 real Pipe Dreams backend artifacts.

This script does not tune or re-select the model.

Frozen experiment:
- V1 = full history + no recency + per-asset ranking
- V2 = C3 = full history + no recency + per-metre ranking
- planning cutoff = 2022
- model training cutoff = 2019, outcomes 2020-2022
- displayed operational capacity = 5% of eligible network length
- evidence-confidence thresholds frozen before final test

The validation/final result JSON files are outputs of the separately
frozen runners and are used here only for reporting/audit tables.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.ops import transform as shapely_transform

from pipe_dreams_engine.agent import (
    CANDIDATE_POLICIES,
    V1_POLICY,
)
from pipe_dreams_engine.evidence import (
    attach_future_outcomes,
    build_evidence_snapshot,
)
from pipe_dreams_engine.governance import (
    ConfidenceThresholds,
    apply_governance,
    build_escalation_rows,
    build_not_covered_records,
)
from pipe_dreams_engine.matching import associate_breaks
from pipe_dreams_engine.model import (
    count_baseline_scores,
    fit_pipe_model,
    score_pipe_model,
)
from pipe_dreams_engine.planner import build_capacity_plan
from pipe_dreams_engine.real_data import load_real_inputs


ROOT = Path(__file__).resolve().parents[1]

BREAKS_PATH = (
    ROOT / "data" / "audit_working" / "data" / "breaks_raw.json"
)
PIPES_PATH = (
    ROOT / "data" / "audit_working" / "data" / "pipes_raw.json"
)
COMMUNITIES_PATH = (
    ROOT / "data" / "external" / "community_boundaries.csv"
)

CONFIG_PATH = (
    ROOT / "config" / "policy_config.DRAFT.yaml"
)
FREEZE_PATH = (
    ROOT / "config" / "pre_final_freeze.json"
)

VALIDATION_JSON = (
    ROOT
    / "data"
    / "audit_working"
    / "pipe_validation_preview.json"
)
FINAL_JSON = (
    ROOT
    / "data"
    / "audit_working"
    / "pipe_final_results.json"
)

DEFAULT_OUT = (
    ROOT
    / "data"
    / "artifacts"
    / "real"
)

TRAINING_CUTOFF = 2019
PLAN_CUTOFF = 2022
HORIZON_YEARS = 3
HISTORY_MAX_YEAR = 2022

DISPLAY_BUDGET_SHARE = 0.05
BUDGETS_PCT = [1, 2, 5, 10]

LOW_TO_MEDIUM = 0.879155211367
MEDIUM_TO_HIGH = 0.978232477144

FREEZE_TAG = "pre-final-freeze-2026-10-04"

PLAN_COLUMNS = (
    "asset_id",
    "source_segment_ids",
    "length_m",
    "consequence_tier",
    "evidence_confidence",
    "association_quality",
    "rank_stability",
    "evidence_basis",
    "latitude",
    "longitude",
    "geometry_wkt",
    "rank",
    "selected",
    "likelihood_score",
    "priority_score",
    "recommended_action",
    "revision_reason",
)

BASELINE_COLUMNS = (
    "asset_id",
    "baseline_name",
    "rank",
    "selected",
    "score",
    "length_m",
)

VALIDATION_COLUMNS = (
    "split",
    "origin_cutoff",
    "policy_id",
    "policy_type",
    "budget_pct",
    "asset_capture",
    "event_capture",
    "lift_vs_count_only",
    "ci_low",
    "ci_high",
    "matched_break_share",
    "pooled_gate_score",
    "accepted_vs_v1",
    "notes",
)

RANK_CHANGE_COLUMNS = (
    "asset_id",
    "rank_v1",
    "rank_v2",
    "delta_rank",
    "action_v1",
    "action_v2",
    "reason_1",
    "reason_2",
    "show_in_demo",
)

ESCALATION_COLUMNS = (
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
)

NOT_COVERED_COLUMNS = (
    "coverage_issue_id",
    "scope",
    "description",
    "why_not_covered",
    "required_evidence",
    "ui_severity",
    "source_note",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def verify_frozen_inputs() -> dict[str, Any]:
    freeze = json.loads(
        FREEZE_PATH.read_text()
    )

    if freeze["selected_policy_id"] != "C3":
        raise RuntimeError(
            "freeze does not select C3"
        )

    if freeze["v1_policy_id"] != "V1":
        raise RuntimeError(
            "freeze does not define V1 correctly"
        )

    if sha256(CONFIG_PATH) != freeze["config_sha256"]:
        raise RuntimeError(
            "policy config hash differs from pre-final freeze"
        )

    data_paths = {
        "breaks_raw": BREAKS_PATH,
        "pipes_raw": PIPES_PATH,
        "community_boundaries": COMMUNITIES_PATH,
    }

    for name, path in data_paths.items():
        actual = sha256(path)
        expected = freeze[
            "data_sha256"
        ][name]
        if actual != expected:
            raise RuntimeError(
                f"{name} differs from pre-final freeze"
            )

    tag_commit = git(
        "rev-list",
        "-n",
        "1",
        FREEZE_TAG,
    )
    if not tag_commit:
        raise RuntimeError(
            "pre-final freeze tag cannot be resolved"
        )

    return freeze


def load_frozen_results():
    if not VALIDATION_JSON.is_file():
        raise FileNotFoundError(
            "Missing validation output. Run "
            "scripts/run_real_pipe_validation.py "
            "--bootstrap-reps 1000 first."
        )

    if not FINAL_JSON.is_file():
        raise FileNotFoundError(
            "Missing final output. Run "
            "scripts/run_real_pipe_final.py first."
        )

    validation = json.loads(
        VALIDATION_JSON.read_text()
    )
    final = json.loads(
        FINAL_JSON.read_text()
    )

    if validation.get(
        "bootstrap_reps"
    ) != 1000:
        raise RuntimeError(
            "validation JSON is not the frozen "
            "1000-rep run"
        )

    if validation.get(
        "max_break_year_used"
    ) != 2022:
        raise RuntimeError(
            "validation JSON safety boundary mismatch"
        )

    if validation.get(
        "revision_gate",
        {},
    ).get(
        "selected_policy_id"
    ) != "C3":
        raise RuntimeError(
            "validation JSON does not select C3"
        )

    if not final.get(
        "final_test_executed"
    ):
        raise RuntimeError(
            "final JSON does not contain completed final test"
        )

    if final[
        "final_test"
    ][
        "outcome_years"
    ] != [
        2023,
        2024,
        2025,
    ]:
        raise RuntimeError(
            "final JSON outcome period mismatch"
        )

    return validation, final


def percentile_rank(
    scores: pd.Series,
) -> pd.Series:
    numeric = pd.to_numeric(
        scores,
        errors="coerce",
    )

    if numeric.isna().any():
        raise ValueError(
            "model scores contain invalid values"
        )

    return numeric.rank(
        method="average",
        pct=True,
    ).astype(float)


def rank_stability(
    frame: pd.DataFrame,
    fitted_models: list,
) -> pd.Series:
    percentile_columns = []

    for fitted in fitted_models:
        scores = score_pipe_model(
            fitted,
            frame,
        )
        percentile_columns.append(
            percentile_rank(scores)
        )

    ranks = pd.concat(
        percentile_columns,
        axis=1,
    )

    stability = (
        1.0
        - (
            ranks.max(axis=1)
            - ranks.min(axis=1)
        )
    ).clip(
        lower=0.0,
        upper=1.0,
    )

    stability.name = "rank_stability"
    return stability


def history_frame(
    *,
    cutoff: int,
    pipes: pd.DataFrame,
    breaks: pd.DataFrame,
    associations: pd.DataFrame,
) -> pd.DataFrame:
    return build_evidence_snapshot(
        pipes,
        breaks,
        associations,
        cutoff_year=cutoff,
        history_start_year=None,
        recency="none",
    )


def train_at(
    *,
    cutoff: int,
    pipes: pd.DataFrame,
    breaks: pd.DataFrame,
    associations: pd.DataFrame,
):
    snapshot = history_frame(
        cutoff=cutoff,
        pipes=pipes,
        breaks=breaks,
        associations=associations,
    )

    training = attach_future_outcomes(
        snapshot,
        pipes,
        breaks,
        associations,
        cutoff_year=cutoff,
        horizon_years=HORIZON_YEARS,
    )

    return fit_pipe_model(
        training
    )


def normalized_priority(
    ranks: pd.Series,
) -> pd.Series:
    r = pd.to_numeric(
        ranks,
        errors="raise",
    ).astype(float)

    n = len(r)
    if n == 0:
        raise ValueError(
            "cannot normalize empty ranking"
        )

    if n == 1:
        return pd.Series(
            1.0,
            index=r.index,
            dtype=float,
        )

    return (
        1.0
        - (
            (r - 1.0)
            / float(n - 1)
        )
    ).clip(
        lower=0.0,
        upper=1.0,
    )


def plan_with_governance(
    *,
    frame: pd.DataFrame,
    scores: pd.Series,
    stability: pd.Series,
    ranking_mode: str,
    revision_reason: str,
    thresholds: ConfidenceThresholds,
) -> pd.DataFrame:
    planned, _summary = build_capacity_plan(
        frame,
        scores,
        budget_share=DISPLAY_BUDGET_SHARE,
        ranking_mode=ranking_mode,
    )

    # Preserve all eligible assets and align to the original asset frame.
    planned = planned.copy()

    if "rank" not in planned.columns:
        raise RuntimeError(
            "planner output is missing rank"
        )

    if "selected" not in planned.columns:
        raise RuntimeError(
            "planner output is missing selected"
        )

    if set(planned.index) != set(frame.index):
        raise RuntimeError(
            "planner output does not contain "
            "the complete eligible asset set"
        )

    planned = planned.reindex(
        frame.index
    )

    governed_input = frame.copy()
    governed_input["rank"] = (
        planned["rank"]
    )
    governed_input["selected"] = (
        planned["selected"]
        .astype(bool)
    )
    governed_input["likelihood_score"] = (
        scores.reindex(
            frame.index
        ).astype(float)
    )

    governed = apply_governance(
        governed_input,
        rank_stability=(
            stability.reindex(
                frame.index
            )
        ),
        thresholds=thresholds,
        selected_column="selected",
    )

    # Governance should retain planning fields, but enforce them if the
    # implementation deliberately returns a reduced/copied frame.
    governed["rank"] = (
        governed_input["rank"]
    )
    governed["selected"] = (
        governed_input["selected"]
    )
    governed["likelihood_score"] = (
        governed_input[
            "likelihood_score"
        ]
    )

    governed["priority_score"] = (
        normalized_priority(
            governed["rank"]
        )
    )

    governed["revision_reason"] = (
        revision_reason
    )

    return governed


def source_segment_ids(
    frame: pd.DataFrame,
) -> pd.Series:
    if "source_segment_ids" in frame.columns:
        def clean(v):
            if isinstance(
                v,
                (list, tuple, np.ndarray),
            ):
                return [
                    str(x)
                    for x in v
                ]
            if v is None or (
                isinstance(v, float)
                and np.isnan(v)
            ):
                return []
            return [str(v)]

        return frame[
            "source_segment_ids"
        ].map(clean)

    return frame[
        "asset_id"
    ].map(
        lambda v: [str(v)]
    )


def evidence_basis_string(
    value: Any,
) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        str,
    ):
        return value

    if isinstance(
        value,
        (dict, list, tuple),
    ):
        return json.dumps(
            value,
            sort_keys=True,
            default=str,
        )

    return str(value)


def geographic_coordinates(
    geometries: pd.Series,
) -> tuple[list[float], list[float]]:
    transformer = Transformer.from_crs(
        "EPSG:3776",
        "EPSG:4326",
        always_xy=True,
    )

    xs = []
    ys = []

    for geom in geometries:
        if geom is None or getattr(
            geom,
            "is_empty",
            True,
        ):
            xs.append(np.nan)
            ys.append(np.nan)
            continue

        centroid = geom.centroid
        projected = shapely_transform(
            transformer.transform,
            centroid,
        )

        xs.append(
            float(projected.x)
        )
        ys.append(
            float(projected.y)
        )

    return xs, ys


def backend_plan(
    governed: pd.DataFrame,
) -> pd.DataFrame:
    result = governed.copy()

    result[
        "source_segment_ids"
    ] = source_segment_ids(
        result
    )

    if (
        "evidence_basis"
        not in result.columns
    ):
        raise RuntimeError(
            "governance output is missing evidence_basis"
        )

    result[
        "evidence_basis"
    ] = result[
        "evidence_basis"
    ].map(
        evidence_basis_string
    )

    # Invalid/missing diameter has no defensible consequence tier.
    # Keep that explicit rather than fabricating T1/T2/T3.
    result[
        "consequence_tier"
    ] = (
        result[
            "consequence_tier"
        ]
        .astype("object")
        .where(
            result[
                "consequence_tier"
            ].notna(),
            "UNVERIFIED",
        )
        .map(str)
    )

    longitude, latitude = (
        geographic_coordinates(
            result["geometry"]
        )
    )
    result["longitude"] = longitude
    result["latitude"] = latitude

    result["geometry_wkt"] = (
        result["geometry"].map(
            lambda g: g.wkt
        )
    )

    result["asset_id"] = (
        result["asset_id"].map(str)
    )

    result["rank"] = pd.to_numeric(
        result["rank"],
        errors="raise",
    ).astype(int)

    result["selected"] = (
        result["selected"]
        .astype(bool)
    )

    result[
        "association_quality"
    ] = pd.to_numeric(
        result[
            "association_quality"
        ],
        errors="raise",
    ).astype(float)

    result[
        "rank_stability"
    ] = pd.to_numeric(
        result[
            "rank_stability"
        ],
        errors="raise",
    ).astype(float)

    result[
        "likelihood_score"
    ] = pd.to_numeric(
        result[
            "likelihood_score"
        ],
        errors="raise",
    ).astype(float)

    result[
        "priority_score"
    ] = pd.to_numeric(
        result[
            "priority_score"
        ],
        errors="raise",
    ).astype(float)

    result["length_m"] = pd.to_numeric(
        result["length_m"],
        errors="raise",
    ).astype(float)

    missing = [
        col
        for col in PLAN_COLUMNS
        if col not in result.columns
    ]
    if missing:
        raise RuntimeError(
            "plan is missing columns: "
            f"{missing}"
        )

    result = (
        result.loc[
            :,
            list(PLAN_COLUMNS),
        ]
        .sort_values(
            "rank"
        )
        .reset_index(
            drop=True
        )
    )

    expected_ranks = list(
        range(
            1,
            len(result) + 1,
        )
    )
    if (
        result[
            "rank"
        ].tolist()
        != expected_ranks
    ):
        raise RuntimeError(
            "plan ranks are not exactly 1..N"
        )

    return result


def baseline_frame(
    *,
    frame: pd.DataFrame,
) -> pd.DataFrame:
    scores = count_baseline_scores(
        frame
    )

    planned, _summary = (
        build_capacity_plan(
            frame,
            scores,
            budget_share=(
                DISPLAY_BUDGET_SHARE
            ),
            ranking_mode="per_asset",
        )
    )

    planned = planned.reindex(
        frame.index
    )

    result = pd.DataFrame(
        {
            "asset_id": (
                frame[
                    "asset_id"
                ].map(str)
            ),
            "baseline_name": (
                "count_only"
            ),
            "rank": pd.to_numeric(
                planned["rank"],
                errors="raise",
            ).astype(int),
            "selected": (
                planned[
                    "selected"
                ].astype(bool)
            ),
            "score": (
                scores.reindex(
                    frame.index
                ).astype(float)
            ),
            "length_m": pd.to_numeric(
                frame[
                    "length_m"
                ],
                errors="raise",
            ).astype(float),
        }
    )

    return (
        result.loc[
            :,
            list(BASELINE_COLUMNS),
        ]
        .sort_values("rank")
        .reset_index(drop=True)
    )


def validation_results_frame(
    validation: dict,
    final: dict,
) -> pd.DataFrame:
    rows = []

    baseline_by_origin_budget = {}

    for origin in validation[
        "count_only"
    ]:
        cutoff = int(
            origin[
                "cutoff_year"
            ]
        )
        for budget in origin[
            "budgets"
        ]:
            key = (
                cutoff,
                int(
                    budget[
                        "budget_pct"
                    ]
                ),
            )
            baseline_by_origin_budget[
                key
            ] = float(
                budget[
                    "breaking_asset_capture"
                ]
            )

    decisions = {
        row[
            "candidate_id"
        ]: row
        for row in validation[
            "revision_gate"
        ][
            "decisions"
        ]
    }

    pooled = validation[
        "pooled_scores"
    ]

    reachability = {
        int(row["cutoff_year"]): row
        for row in validation[
            "outcome_reachability"
        ]
    }

    for policy_id, origins in validation[
        "results"
    ].items():
        for origin in origins:
            cutoff = int(
                origin[
                    "cutoff_year"
                ]
            )

            for budget in origin[
                "budgets"
            ]:
                budget_pct = int(
                    budget[
                        "budget_pct"
                    ]
                )
                capture = float(
                    budget[
                        "breaking_asset_capture"
                    ]
                )
                count_capture = (
                    baseline_by_origin_budget[
                        (
                            cutoff,
                            budget_pct,
                        )
                    ]
                )

                decision = (
                    decisions.get(
                        policy_id
                    )
                )

                rows.append(
                    {
                        "split": "validation",
                        "origin_cutoff": cutoff,
                        "policy_id": policy_id,
                        "policy_type": "policy",
                        "budget_pct": budget_pct,
                        "asset_capture": capture,
                        "event_capture": float(
                            budget[
                                "event_capture"
                            ]
                        ),
                        "lift_vs_count_only": (
                            capture
                            - count_capture
                        ),
                        "ci_low": np.nan,
                        "ci_high": np.nan,
                        "matched_break_share": float(
                            reachability[
                                cutoff
                            ][
                                "reachable_share"
                            ]
                        ),
                        "pooled_gate_score": float(
                            pooled[
                                policy_id
                            ]
                        ),
                        "accepted_vs_v1": (
                            decision[
                                "decision"
                            ]
                            == "ACCEPT"
                            if decision
                            is not None
                            else np.nan
                        ),
                        "notes": (
                            "Primary metric is breaking-asset "
                            "capture at constrained network-length "
                            "budget. Gate uncertainty uses pooled "
                            "paired 1 km spatial bootstrap SE."
                        ),
                    }
                )

    for origin in validation[
        "count_only"
    ]:
        cutoff = int(
            origin[
                "cutoff_year"
            ]
        )

        for budget in origin[
            "budgets"
        ]:
            rows.append(
                {
                    "split": "validation",
                    "origin_cutoff": cutoff,
                    "policy_id": "count_only",
                    "policy_type": "baseline",
                    "budget_pct": int(
                        budget[
                            "budget_pct"
                        ]
                    ),
                    "asset_capture": float(
                        budget[
                            "breaking_asset_capture"
                        ]
                    ),
                    "event_capture": float(
                        budget[
                            "event_capture"
                        ]
                    ),
                    "lift_vs_count_only": 0.0,
                    "ci_low": np.nan,
                    "ci_high": np.nan,
                    "matched_break_share": float(
                        reachability[
                            cutoff
                        ][
                            "reachable_share"
                        ]
                    ),
                    "pooled_gate_score": float(
                        pooled[
                            "count_only"
                        ]
                    ),
                    "accepted_vs_v1": np.nan,
                    "notes": (
                        "Count-only segment baseline."
                    ),
                }
            )

    final_results = final[
        "results"
    ]

    final_count = {
        int(x["budget_pct"]): float(
            x[
                "breaking_asset_capture"
            ]
        )
        for x in final_results[
            "count_only"
        ][
            "budgets"
        ]
    }

    final_reach = float(
        final[
            "outcome_reachability"
        ][
            "reachable_share"
        ]
    )

    for policy_id in (
        "V1",
        "C3",
    ):
        result = final_results[
            policy_id
        ]

        for budget in result[
            "budgets"
        ]:
            budget_pct = int(
                budget[
                    "budget_pct"
                ]
            )
            capture = float(
                budget[
                    "breaking_asset_capture"
                ]
            )

            rows.append(
                {
                    "split": "final",
                    "origin_cutoff": 2022,
                    "policy_id": policy_id,
                    "policy_type": "policy",
                    "budget_pct": budget_pct,
                    "asset_capture": capture,
                    "event_capture": float(
                        budget[
                            "event_capture"
                        ]
                    ),
                    "lift_vs_count_only": (
                        capture
                        - final_count[
                            budget_pct
                        ]
                    ),
                    "ci_low": np.nan,
                    "ci_high": np.nan,
                    "matched_break_share": (
                        final_reach
                    ),
                    "pooled_gate_score": (
                        float(
                            pooled[
                                policy_id
                            ]
                        )
                    ),
                    "accepted_vs_v1": (
                        True
                        if policy_id
                        == "C3"
                        else np.nan
                    ),
                    "notes": (
                        "Corrected frozen final test; "
                        "2023-2025 outcomes. No tuning "
                        "performed after final evaluation."
                    ),
                }
            )

    count_result = final_results[
        "count_only"
    ]

    for budget in count_result[
        "budgets"
    ]:
        rows.append(
            {
                "split": "final",
                "origin_cutoff": 2022,
                "policy_id": "count_only",
                "policy_type": "baseline",
                "budget_pct": int(
                    budget[
                        "budget_pct"
                    ]
                ),
                "asset_capture": float(
                    budget[
                        "breaking_asset_capture"
                    ]
                ),
                "event_capture": float(
                    budget[
                        "event_capture"
                    ]
                ),
                "lift_vs_count_only": 0.0,
                "ci_low": np.nan,
                "ci_high": np.nan,
                "matched_break_share": (
                    final_reach
                ),
                "pooled_gate_score": np.nan,
                "accepted_vs_v1": np.nan,
                "notes": (
                    "Count-only baseline on corrected "
                    "2023-2025 final test."
                ),
            }
        )

    return pd.DataFrame(
        rows,
        columns=VALIDATION_COLUMNS,
    )


def candidate_payload(
    row: dict,
) -> dict:
    return {
        "candidate_id": row[
            "candidate_id"
        ],
        "origin_wins": int(
            row[
                "origin_wins"
            ]
        ),
        "n_origins": int(
            row[
                "n_origins"
            ]
        ),
        "pooled_v1_score": float(
            row[
                "pooled_v1_score"
            ]
        ),
        "pooled_candidate_score": float(
            row[
                "pooled_candidate_score"
            ]
        ),
        "difference": float(
            row[
                "difference"
            ]
        ),
        "bootstrap_se": float(
            row[
                "bootstrap_se"
            ]
        ),
        "required_delta": float(
            row[
                "required_delta"
            ]
        ),
        "decision": row[
            "decision"
        ],
        "reason": row[
            "reason"
        ],
    }


def agent_log_rows(
    validation: dict,
) -> list[dict]:
    timestamp = (
        "2026-10-04T01:00:00-06:00"
    )

    rows = [
        {
            "seq": 1,
            "event_type": "PLAN_V1",
            "timestamp": timestamp,
            "summary": (
                "Construct frozen V1 ranking policy."
            ),
            "candidate": None,
            "details": {
                "policy_id": "V1",
                "history_window": "full",
                "recency_decay": "none",
                "ranking_normalization": "per_asset",
            },
        },
        {
            "seq": 2,
            "event_type": "EVALUATE",
            "timestamp": timestamp,
            "summary": (
                "Evaluate V1 and challengers at "
                "2013/2016/2019 rolling origins."
            ),
            "candidate": None,
            "details": {
                "budgets_pct": BUDGETS_PCT,
                "bootstrap_reps": 1000,
                "bootstrap_block_km": 1.0,
            },
        },
    ]

    seq = 3

    for decision in validation[
        "revision_gate"
    ][
        "decisions"
    ]:
        cand = candidate_payload(
            decision
        )

        rows.append(
            {
                "seq": seq,
                "event_type": "TEST_CANDIDATE",
                "timestamp": timestamp,
                "summary": (
                    f"Test {cand['candidate_id']} "
                    "against frozen revision gate."
                ),
                "candidate": cand,
                "details": {},
            }
        )
        seq += 1

        rows.append(
            {
                "seq": seq,
                "event_type": (
                    cand[
                        "decision"
                    ]
                ),
                "timestamp": timestamp,
                "summary": (
                    f"{cand['candidate_id']} "
                    f"{cand['decision'].lower()}ed "
                    "by frozen gate."
                ),
                "candidate": cand,
                "details": {},
            }
        )
        seq += 1

    rows.append(
        {
            "seq": seq,
            "event_type": "PLAN_V2",
            "timestamp": timestamp,
            "summary": (
                "Select C3 as V2 because it is the "
                "highest-scoring challenger that passed "
                "the frozen revision gate."
            ),
            "candidate": None,
            "details": {
                "selected_policy_id": "C3",
                "v2_equals_v1": False,
            },
        }
    )

    return rows


def rank_changes_frame(
    v1: pd.DataFrame,
    v2: pd.DataFrame,
) -> pd.DataFrame:
    a = v1.set_index(
        "asset_id"
    )
    b = v2.set_index(
        "asset_id"
    )

    rows = pd.DataFrame(
        {
            "asset_id": a.index,
            "rank_v1": (
                a["rank"].astype(int)
            ),
            "rank_v2": (
                b.loc[
                    a.index,
                    "rank"
                ].astype(int)
            ),
            "action_v1": (
                a[
                    "recommended_action"
                ].astype(str)
            ),
            "action_v2": (
                b.loc[
                    a.index,
                    "recommended_action"
                ].astype(str)
            ),
        }
    ).reset_index(drop=True)

    # Positive delta means the asset moved upward under V2.
    rows[
        "delta_rank"
    ] = (
        rows["rank_v1"]
        - rows["rank_v2"]
    )

    rows["reason_1"] = (
        "V1 ranks the frozen model score per asset."
    )
    rows["reason_2"] = (
        "C3 ranks the same frozen model score per metre "
        "of pipe, aligning ranking with constrained "
        "inspection capacity."
    )

    rows[
        "show_in_demo"
    ] = False

    demo_idx = (
        rows[
            "delta_rank"
        ]
        .abs()
        .nlargest(8)
        .index
    )

    rows.loc[
        demo_idx,
        "show_in_demo",
    ] = True

    rows = rows.sort_values(
        [
            "show_in_demo",
            "delta_rank",
        ],
        ascending=[
            False,
            False,
        ],
    ).reset_index(drop=True)

    return rows.loc[
        :,
        list(RANK_CHANGE_COLUMNS),
    ]


def era_match_rates(
    breaks: pd.DataFrame,
    associations: pd.DataFrame,
) -> tuple[dict, dict]:
    years = pd.to_numeric(
        breaks["break_year"],
        errors="coerce",
    )

    bins = [
        -np.inf,
        1979,
        1999,
        2015,
        2025,
    ]
    labels = [
        "through_1979",
        "1980_1999",
        "2000_2015",
        "2016_2025",
    ]

    eras = pd.cut(
        years,
        bins=bins,
        labels=labels,
    )

    matched = associations[
        "associated"
    ].astype(bool)

    rates = {}
    unmatched = {}

    for label in labels:
        mask = eras == label
        n = int(
            mask.sum()
        )

        if n == 0:
            rates[label] = None
            unmatched[label] = None
            continue

        rate = float(
            matched.loc[
                mask
            ].mean()
        )

        rates[label] = rate
        unmatched[label] = (
            1.0 - rate
        )

    return rates, unmatched


def match_rate_by_origin(
    validation: dict,
) -> dict:
    return {
        str(
            item[
                "cutoff_year"
            ]
        ): float(
            item[
                "reachable_share"
            ]
        )
        for item in validation[
            "outcome_reachability"
        ]
    }


def diagnostic_count(
    diagnostics: dict,
    *names: str,
) -> int:
    for name in names:
        if name in diagnostics:
            try:
                return int(
                    diagnostics[
                        name
                    ]
                )
            except (
                TypeError,
                ValueError,
            ):
                pass
    return 0


def ensure_dataframe(
    value: Any,
) -> pd.DataFrame:
    if isinstance(
        value,
        pd.DataFrame,
    ):
        return value.copy()

    return pd.DataFrame(
        value
    )


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.write_text(
        json.dumps(
            value,
            indent=2,
            default=str,
        )
        + "\n"
    )


def write_jsonl(
    path: Path,
    rows: list[dict],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    default=str,
                )
                + "\n"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
    )
    args = parser.parse_args()

    out = args.out
    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "PIPE DREAMS REAL ARTIFACT GENERATOR"
    )
    print()

    freeze = verify_frozen_inputs()
    validation, final = (
        load_frozen_results()
    )

    print(
        "Frozen config/data checksums verified."
    )
    print(
        "Selected V2: C3"
    )
    print(
        "Displayed capacity: 5% network length"
    )
    print()

    (
        communities,
        pipes,
        all_breaks,
        diagnostics,
    ) = load_real_inputs(
        breaks_path=BREAKS_PATH,
        pipes_path=PIPES_PATH,
        communities_path=COMMUNITIES_PATH,
    )

    pipes = (
        pipes.copy()
        .reset_index(drop=True)
    )

    safe_breaks = (
        all_breaks.loc[
            pd.to_numeric(
                all_breaks[
                    "break_year"
                ],
                errors="coerce",
            )
            <= HISTORY_MAX_YEAR
        ]
        .copy()
        .reset_index(drop=True)
    )

    print(
        f"Pipes: {len(pipes):,}"
    )
    print(
        f"History-safe breaks through 2022: "
        f"{len(safe_breaks):,}"
    )

    associations = associate_breaks(
        safe_breaks,
        pipes,
    )

    print(
        "Associated history-safe breaks:",
        f"{int(associations['associated'].sum()):,}",
    )

    # ---------------------------------------------------------- frozen model
    print()
    print(
        "Fitting frozen 2019 model..."
    )

    final_model = train_at(
        cutoff=TRAINING_CUTOFF,
        pipes=pipes,
        breaks=safe_breaks,
        associations=associations,
    )

    planning_frame = history_frame(
        cutoff=PLAN_CUTOFF,
        pipes=pipes,
        breaks=safe_breaks,
        associations=associations,
    )

    likelihood = score_pipe_model(
        final_model,
        planning_frame,
    )

    print(
        f"2022 eligible assets: "
        f"{len(planning_frame):,}"
    )

    # ---------------------------------------------------------- rank stability
    print(
        "Computing validation-derived rank stability..."
    )

    historical_models = [
        train_at(
            cutoff=cutoff,
            pipes=pipes,
            breaks=safe_breaks,
            associations=associations,
        )
        for cutoff in (
            2010,
            2013,
            2016,
        )
    ]

    stability = rank_stability(
        planning_frame,
        historical_models,
    )

    thresholds = ConfidenceThresholds(
        low_to_medium=LOW_TO_MEDIUM,
        medium_to_high=MEDIUM_TO_HIGH,
        source="validation_only",
    )

    # ---------------------------------------------------------- plans
    print(
        "Building V1 and V2 plans..."
    )

    v1_governed = plan_with_governance(
        frame=planning_frame,
        scores=likelihood,
        stability=stability,
        ranking_mode="per_asset",
        revision_reason=(
            "Frozen V1: full history, no recency, "
            "per-asset ranking."
        ),
        thresholds=thresholds,
    )

    c3 = next(
        p
        for p in CANDIDATE_POLICIES
        if p.policy_id == "C3"
    )

    if (
        c3.history_window != "full"
        or c3.recency_decay != "none"
        or c3.ranking_normalization
        != "per_meter"
    ):
        raise RuntimeError(
            "C3 no longer matches the frozen definition"
        )

    v2_governed = plan_with_governance(
        frame=planning_frame,
        scores=likelihood,
        stability=stability,
        ranking_mode="per_metre",
        revision_reason=(
            "Frozen V2=C3: selected by the validation "
            "gate; same likelihood model as V1 with "
            "per-metre capacity normalization."
        ),
        thresholds=thresholds,
    )

    plan_v1 = backend_plan(
        v1_governed
    )
    plan_v2 = backend_plan(
        v2_governed
    )

    # Physical evidence must be exactly shared.
    physical = [
        "asset_id",
        "source_segment_ids",
        "length_m",
        "consequence_tier",
        "evidence_confidence",
        "association_quality",
        "rank_stability",
        "evidence_basis",
        "latitude",
        "longitude",
        "geometry_wkt",
    ]

    p1 = (
        plan_v1[
            physical
        ]
        .sort_values("asset_id")
        .reset_index(drop=True)
    )
    p2 = (
        plan_v2[
            physical
        ]
        .sort_values("asset_id")
        .reset_index(drop=True)
    )

    if not p1.equals(p2):
        raise RuntimeError(
            "V1/V2 physical evidence columns differ"
        )

    baseline = baseline_frame(
        frame=planning_frame
    )

    # ---------------------------------------------------------- rank changes
    rank_changes = (
        rank_changes_frame(
            plan_v1,
            plan_v2,
        )
    )

    # ---------------------------------------------------------- escalation
    print(
        "Building governance escalation records..."
    )

    escalation = ensure_dataframe(
        build_escalation_rows(
            v2_governed,
            start_date=date(
                2026,
                10,
                4,
            ),
            last_reviewed=date(
                2026,
                10,
                4,
            ),
        )
    )

    if escalation.empty:
        escalation = pd.DataFrame(
            columns=ESCALATION_COLUMNS
        )
    else:
        # Fixed response SLA from the review date.
        # Do not schedule escalation deadlines sequentially by row/rank.
        reviewed = pd.to_datetime(
            escalation["last_reviewed"],
            errors="raise",
        )
        escalation["response_deadline"] = (
            reviewed + pd.Timedelta(days=7)
        ).dt.date.astype(str)

        missing = [
            col
            for col in ESCALATION_COLUMNS
            if col
            not in escalation.columns
        ]
        if missing:
            raise RuntimeError(
                "escalation output missing "
                f"columns: {missing}"
            )

        escalation = escalation.loc[
            :,
            list(
                ESCALATION_COLUMNS
            ),
        ]

    # ---------------------------------------------------------- not covered
    not_covered = ensure_dataframe(
        build_not_covered_records()
    )

    if not_covered.empty:
        not_covered = pd.DataFrame(
            columns=NOT_COVERED_COLUMNS
        )
    else:
        missing = [
            col
            for col
            in NOT_COVERED_COLUMNS
            if col
            not in not_covered.columns
        ]
        if missing:
            raise RuntimeError(
                "not-covered output missing "
                f"columns: {missing}"
            )

        not_covered = (
            not_covered.loc[
                :,
                list(
                    NOT_COVERED_COLUMNS
                ),
            ]
        )

    # ---------------------------------------------------------- validation CSV
    validation_results = (
        validation_results_frame(
            validation,
            final,
        )
    )

    # ---------------------------------------------------------- audit log
    agent_log = agent_log_rows(
        validation
    )

    # ---------------------------------------------------------- data quality
    all_through_2025 = (
        all_breaks.loc[
            pd.to_numeric(
                all_breaks[
                    "break_year"
                ],
                errors="coerce",
            )
            <= 2025
        ]
        .copy()
        .reset_index(drop=True)
    )

    assoc_through_2025 = associate_breaks(
        all_through_2025,
        pipes,
    )

    by_era, unmatched_by_era = (
        era_match_rates(
            all_through_2025,
            assoc_through_2025,
        )
    )

    final_reach = float(
        final[
            "outcome_reachability"
        ][
            "reachable_share"
        ]
    )

    data_quality = {
        "rows_dropped_missing_coordinates": (
            diagnostic_count(
                diagnostics,
                "rows_dropped_missing_coordinates",
                "break_rows_dropped_missing_coordinates",
            )
        ),
        "match_rate_by_origin": (
            match_rate_by_origin(
                validation
            )
        ),
        "match_rate_by_era": by_era,
        "unmatched_share_by_era": (
            unmatched_by_era
        ),
        "unreachable_final_test_share": (
            1.0 - final_reach
        ),
        "future_year_pipe_rows_excluded": (
            diagnostic_count(
                diagnostics,
                "future_year_pipe_rows_excluded",
                "future_pipe_rows_excluded",
            )
        ),
        "planned_rows_excluded": (
            diagnostic_count(
                diagnostics,
                "planned_rows_excluded",
                "planned_pipe_rows_excluded",
            )
        ),
        "inactive_sensitivity": {
            "used_in_model": False,
            "reason": (
                "Present-day asset status was not used "
                "as a historical predictive feature "
                "because historical validity at earlier "
                "cutoffs was not established."
            ),
        },
        "retired_status_strata": {
            "used_in_model": False,
            "reason": (
                "Present-day retired/inactive status "
                "was excluded from time-safe model "
                "features."
            ),
        },
        "notes": [
            (
                "Break-to-pipe attribution requires "
                "install_year < break_year and distance "
                "within the frozen association threshold."
            ),
            (
                "Validation origins are 2013, 2016, "
                "and 2019 with three-year outcomes."
            ),
            (
                "Corrected final test is 2022 -> "
                "2023-2025 and was run only after the "
                "pre-final freeze."
            ),
            (
                "Era summaries are descriptive QA bins "
                "only and are not model features."
            ),
        ],
    }

    # ---------------------------------------------------------- audit summary
    current_commit = git(
        "rev-parse",
        "HEAD",
    )

    audit_summary = {
        "synthetic": False,
        "config_hash": (
            freeze[
                "config_sha256"
            ]
        ),
        "git_commit": current_commit,
        "git_tag": FREEZE_TAG,
        "data_checksums": (
            freeze[
                "data_sha256"
            ]
        ),
        "selected_policy_id": "C3",
        "v1_policy_id": "V1",
        "v2_equals_v1": False,
        "budgets_pct": BUDGETS_PCT,
        "revision_gate": {
            "min_origin_wins": 2,
            "n_origins": 3,
            "min_improvement_in_se": 1.0,
            "bootstrap_block_km": 1.0,
        },
        "final_test": {
            "cutoff_year": 2022,
            "outcome_years": [
                2023,
                2024,
                2025,
            ],
            "previously_viewed": True,
        },
        "data_quality": {
            "final_reachable_share": (
                final_reach
            ),
            "display_budget_pct": 5,
            "evidence_threshold_source": (
                "validation_only"
            ),
            "final_c3_relative_lift_vs_v1": (
                float(
                    final[
                        "comparison"
                    ][
                        "c3_relative_lift_vs_v1"
                    ]
                )
            ),
        },
    }

    # ---------------------------------------------------------- write
    print()
    print(
        f"Writing artifacts to {out}"
    )

    plan_v1.to_parquet(
        out / "plan_v1.parquet",
        index=False,
    )
    plan_v2.to_parquet(
        out / "plan_v2.parquet",
        index=False,
    )
    baseline.to_parquet(
        out / "baseline.parquet",
        index=False,
    )

    validation_results.to_csv(
        out / "validation_results.csv",
        index=False,
    )
    rank_changes.to_csv(
        out / "rank_changes.csv",
        index=False,
    )
    escalation.to_csv(
        out / "escalation.csv",
        index=False,
    )
    not_covered.to_csv(
        out / "not_covered.csv",
        index=False,
    )

    write_jsonl(
        out / "agent_log.jsonl",
        agent_log,
    )
    write_json(
        out / "audit_summary.json",
        audit_summary,
    )
    write_json(
        out / "data_quality.json",
        data_quality,
    )

    print()
    print(
        "Generated:"
    )

    for path in sorted(
        out.iterdir()
    ):
        if path.is_file():
            print(
                f"  {path.name}: "
                f"{path.stat().st_size:,} bytes"
            )

    print()
    print(
        "V1 selected assets:",
        int(
            plan_v1[
                "selected"
            ].sum()
        ),
    )
    print(
        "V2 selected assets:",
        int(
            plan_v2[
                "selected"
            ].sum()
        ),
    )
    print(
        "Escalations:",
        len(escalation),
    )
    print(
        "Demo rank changes:",
        int(
            rank_changes[
                "show_in_demo"
            ].sum()
        ),
    )

    print()
    print(
        "REAL ARTIFACT GENERATION COMPLETE"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
