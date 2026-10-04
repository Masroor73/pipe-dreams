"""Run the frozen Pipe Dreams rolling validation on real Calgary data.

VALIDATION ONLY.

This script deliberately refuses to evaluate the corrected final test.
It truncates the break table to <= 2022 before break-to-pipe matching.

Validation origins:
    2013 -> outcomes 2014-2016
    2016 -> outcomes 2017-2019
    2019 -> outcomes 2020-2022

Training design:
    evaluation T -> train at T-3 using outcomes through T

No 2023+ outcome is available to this runner.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipe_dreams_engine.agent import (
    CANDIDATE_POLICIES,
    V1_POLICY,
    PolicySpec,
    evaluate_revision_gate,
)
from pipe_dreams_engine.evaluation import (
    evaluate_policy_origin,
    pooled_validation_score,
)
from pipe_dreams_engine.evidence import (
    attach_future_outcomes,
    build_evidence_snapshot,
)
from pipe_dreams_engine.matching import associate_breaks
from pipe_dreams_engine.model import (
    count_baseline_scores,
    fit_pipe_model,
    score_pipe_model,
)
from pipe_dreams_engine.real_data import load_real_inputs


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BREAKS = (
    ROOT
    / "data"
    / "audit_working"
    / "data"
    / "breaks_raw.json"
)

DEFAULT_PIPES = (
    ROOT
    / "data"
    / "audit_working"
    / "data"
    / "pipes_raw.json"
)

DEFAULT_COMMUNITIES = (
    ROOT
    / "data"
    / "external"
    / "community_boundaries.csv"
)

DEFAULT_OUT = (
    ROOT
    / "data"
    / "audit_working"
    / "pipe_validation_preview.json"
)

VALIDATION_ORIGINS = (
    2013,
    2016,
    2019,
)

TRAINING_LAG_YEARS = 3
HORIZON_YEARS = 3

# Hard safety boundary.
MAX_VALIDATION_OUTCOME_YEAR = 2022

BUDGET_SHARES = (
    0.01,
    0.02,
    0.05,
    0.10,
)


def history_start_year(
    policy: PolicySpec,
) -> int | None:
    """Translate frozen history-window labels."""
    mapping = {
        "full": None,
        "2000_plus": 2000,
        "2016_plus": 2016,
    }

    if policy.history_window not in mapping:
        raise ValueError(
            "unknown history window "
            f"{policy.history_window!r}"
        )

    return mapping[
        policy.history_window
    ]


def planner_ranking_mode(
    policy: PolicySpec,
) -> str:
    """Translate config spelling to planner spelling."""
    mapping = {
        "per_asset": "per_asset",
        "per_meter": "per_metre",
        "per_metre": "per_metre",
    }

    if policy.ranking_normalization not in mapping:
        raise ValueError(
            "unknown ranking normalization "
            f"{policy.ranking_normalization!r}"
        )

    return mapping[
        policy.ranking_normalization
    ]


def policy_payload(
    policy: PolicySpec,
) -> dict[str, object]:
    return {
        "policy_id": policy.policy_id,
        "history_window": policy.history_window,
        "recency_decay": policy.recency_decay,
        "ranking_normalization": (
            policy.ranking_normalization
        ),
    }


def reachable_outcome_share(
    *,
    cutoff_year: int,
    pipes: pd.DataFrame,
    breaks: pd.DataFrame,
    associations: pd.DataFrame,
) -> dict[str, object]:
    """Measure matched/reachable break-event share for one origin.

    A future break is reachable when it:
    - lies in the three-year outcome period;
    - is associated to a pipe; and
    - the associated pipe already existed at the planning cutoff.
    """
    years = pd.to_numeric(
        breaks["break_year"],
        errors="coerce",
    ).to_numpy(dtype=float)

    outcome_mask = (
        np.isfinite(years)
        & (years > cutoff_year)
        & (
            years
            <= cutoff_year + HORIZON_YEARS
        )
    )

    n_outcome = int(
        outcome_mask.sum()
    )

    if n_outcome == 0:
        return {
            "cutoff_year": cutoff_year,
            "outcome_break_events": 0,
            "associated_break_events": 0,
            "reachable_break_events": 0,
            "matched_share": None,
            "reachable_share": None,
        }

    associated = (
        associations[
            "associated"
        ].to_numpy(dtype=bool)
        & outcome_mask
    )

    n_associated = int(
        associated.sum()
    )

    reachable = np.zeros(
        len(breaks),
        dtype=bool,
    )

    associated_positions = np.flatnonzero(
        associated
    )

    if len(associated_positions):
        pipe_positions = (
            associations.iloc[
                associated_positions
            ][
                "nearest_segment_idx"
            ]
            .to_numpy(dtype=int)
        )

        if (
            (pipe_positions < 0).any()
            or (
                pipe_positions
                >= len(pipes)
            ).any()
        ):
            raise ValueError(
                "invalid associated pipe position"
            )

        install_years = (
            pd.to_numeric(
                pipes.iloc[
                    pipe_positions
                ][
                    "install_year"
                ],
                errors="coerce",
            )
            .to_numpy(dtype=float)
        )

        reachable[
            associated_positions
        ] = (
            install_years
            <= cutoff_year
        )

    n_reachable = int(
        reachable.sum()
    )

    return {
        "cutoff_year": cutoff_year,
        "outcome_break_events": n_outcome,
        "associated_break_events": n_associated,
        "reachable_break_events": n_reachable,
        "matched_share": (
            n_associated
            / n_outcome
        ),
        "reachable_share": (
            n_reachable
            / n_outcome
        ),
    }


def evaluation_payload(
    evaluation,
) -> dict[str, object]:
    rows = []

    for _, row in (
        evaluation.budget_results
        .iterrows()
    ):
        rows.append(
            {
                "budget_pct": int(
                    round(
                        float(
                            row[
                                "budget_share"
                            ]
                        )
                        * 100
                    )
                ),
                "breaking_asset_capture": float(
                    row[
                        "breaking_asset_capture"
                    ]
                ),
                "event_capture": float(
                    row[
                        "event_capture"
                    ]
                ),
                "selected_assets": int(
                    row[
                        "selected_assets"
                    ]
                ),
                "selected_network_m": float(
                    row[
                        "selected_network_m"
                    ]
                ),
                "selected_network_share": float(
                    row[
                        "selected_network_share"
                    ]
                ),
                "future_breaking_assets": int(
                    row[
                        "future_breaking_assets"
                    ]
                ),
                "future_events": float(
                    row[
                        "future_events"
                    ]
                ),
            }
        )

    return {
        "cutoff_year": int(
            evaluation.cutoff_year
        ),
        "ranking_mode": (
            evaluation.ranking_mode
        ),
        "per_origin_score": float(
            evaluation.per_origin_score
        ),
        "budgets": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--breaks",
        type=Path,
        default=DEFAULT_BREAKS,
    )

    parser.add_argument(
        "--pipes",
        type=Path,
        default=DEFAULT_PIPES,
    )

    parser.add_argument(
        "--communities",
        type=Path,
        default=DEFAULT_COMMUNITIES,
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
    )

    parser.add_argument(
        "--bootstrap-reps",
        type=int,
        default=1000,
    )

    args = parser.parse_args()

    if args.bootstrap_reps <= 0:
        raise ValueError(
            "--bootstrap-reps must be positive"
        )

    if max(
        cutoff + HORIZON_YEARS
        for cutoff in VALIDATION_ORIGINS
    ) > MAX_VALIDATION_OUTCOME_YEAR:
        raise RuntimeError(
            "validation configuration crosses "
            "the frozen 2022 safety boundary"
        )

    print(
        "PIPE DREAMS REAL VALIDATION"
    )
    print(
        "Safety boundary: break_year <= 2022"
    )
    print()

    (
        communities,
        pipes,
        all_breaks,
        diagnostics,
    ) = load_real_inputs(
        breaks_path=args.breaks,
        pipes_path=args.pipes,
        communities_path=args.communities,
    )

    # CRITICAL:
    # The corrected final period begins in 2023.
    # Remove those rows before matching so this runner cannot
    # accidentally inspect final-test outcomes.
    breaks = (
        all_breaks.loc[
            all_breaks[
                "break_year"
            ]
            <= MAX_VALIDATION_OUTCOME_YEAR
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    pipes = (
        pipes.copy()
        .reset_index(
            drop=True
        )
    )

    print(
        f"eligible pipes: {len(pipes):,}"
    )
    print(
        "validation-safe breaks "
        f"(<=2022): {len(breaks):,}"
    )
    print(
        f"communities loaded: {len(communities):,}"
    )
    print()

    print(
        "Associating validation-safe breaks "
        "to historically attributable pipes..."
    )

    associations = associate_breaks(
        breaks,
        pipes,
    )

    print(
        "associated:",
        f"{int(associations['associated'].sum()):,}",
    )
    print(
        "ambiguous:",
        f"{int(associations['ambiguous'].sum()):,}",
    )
    print()

    policies = (
        V1_POLICY,
        *CANDIDATE_POLICIES,
    )

    snapshot_cache: dict[
        tuple[int, int | None, str],
        pd.DataFrame,
    ] = {}

    outcome_cache: dict[
        tuple[int, int | None, str],
        pd.DataFrame,
    ] = {}

    model_cache = {}

    def snapshot_for(
        cutoff_year: int,
        policy: PolicySpec,
    ) -> pd.DataFrame:
        history_start = (
            history_start_year(
                policy
            )
        )

        key = (
            cutoff_year,
            history_start,
            policy.recency_decay,
        )

        if key not in snapshot_cache:
            snapshot_cache[
                key
            ] = build_evidence_snapshot(
                pipes,
                breaks,
                associations,
                cutoff_year=cutoff_year,
                history_start_year=history_start,
                recency=policy.recency_decay,
            )

        return snapshot_cache[
            key
        ]

    def outcomes_for(
        cutoff_year: int,
        policy: PolicySpec,
    ) -> pd.DataFrame:
        if (
            cutoff_year
            + HORIZON_YEARS
            > MAX_VALIDATION_OUTCOME_YEAR
        ):
            raise RuntimeError(
                "attempted to attach outcomes "
                "beyond validation safety boundary"
            )

        history_start = (
            history_start_year(
                policy
            )
        )

        key = (
            cutoff_year,
            history_start,
            policy.recency_decay,
        )

        if key not in outcome_cache:
            outcome_cache[
                key
            ] = attach_future_outcomes(
                snapshot_for(
                    cutoff_year,
                    policy,
                ),
                pipes,
                breaks,
                associations,
                cutoff_year=cutoff_year,
                horizon_years=HORIZON_YEARS,
            )

        return outcome_cache[
            key
        ]

    evaluations: dict[
        str,
        list,
    ] = {
        policy.policy_id: []
        for policy in policies
    }

    training_diagnostics: list[
        dict[str, object]
    ] = []

    print(
        "Running frozen rolling origins..."
    )

    for cutoff_year in VALIDATION_ORIGINS:
        training_cutoff = (
            cutoff_year
            - TRAINING_LAG_YEARS
        )

        print()
        print(
            f"=== ORIGIN {cutoff_year} ==="
        )
        print(
            "training cutoff:",
            training_cutoff,
        )
        print(
            "evaluation outcomes:",
            f"{cutoff_year + 1}-"
            f"{cutoff_year + HORIZON_YEARS}",
        )

        for policy in policies:
            history_start = (
                history_start_year(
                    policy
                )
            )

            model_key = (
                training_cutoff,
                history_start,
                policy.recency_decay,
            )

            training_frame = (
                outcomes_for(
                    training_cutoff,
                    policy,
                )
            )

            if model_key not in model_cache:
                model_cache[
                    model_key
                ] = fit_pipe_model(
                    training_frame
                )

            fitted = model_cache[
                model_key
            ]

            evaluation_frame = (
                outcomes_for(
                    cutoff_year,
                    policy,
                )
            )

            scores = score_pipe_model(
                fitted,
                evaluation_frame,
            )

            result = evaluate_policy_origin(
                evaluation_frame,
                scores,
                cutoff_year=cutoff_year,
                ranking_mode=(
                    planner_ranking_mode(
                        policy
                    )
                ),
                budget_shares=(
                    BUDGET_SHARES
                ),
            )

            evaluations[
                policy.policy_id
            ].append(
                result
            )

            training_diagnostics.append(
                {
                    "policy_id": (
                        policy.policy_id
                    ),
                    "evaluation_cutoff": (
                        cutoff_year
                    ),
                    "training_cutoff": (
                        training_cutoff
                    ),
                    "training_rows": (
                        fitted.n_training_rows
                    ),
                    "training_positive": (
                        fitted.n_positive
                    ),
                    "training_positive_rate": (
                        fitted.positive_rate
                    ),
                    "evaluation_rows": (
                        len(
                            evaluation_frame
                        )
                    ),
                    "evaluation_future_breaking_assets": int(
                        evaluation_frame[
                            "future_break_label"
                        ].sum()
                    ),
                }
            )

            print(
                f"{policy.policy_id}: "
                f"{result.per_origin_score:.4f}"
            )

    print()
    print(
        "Running count-only baseline..."
    )

    baseline_evaluations = []

    for cutoff_year in VALIDATION_ORIGINS:
        # Count-only baseline uses the same full-history,
        # non-recency snapshot as V1.
        frame = outcomes_for(
            cutoff_year,
            V1_POLICY,
        )

        baseline_scores = (
            count_baseline_scores(
                frame
            )
        )

        baseline_result = (
            evaluate_policy_origin(
                frame,
                baseline_scores,
                cutoff_year=cutoff_year,
                ranking_mode="per_asset",
                budget_shares=(
                    BUDGET_SHARES
                ),
            )
        )

        baseline_evaluations.append(
            baseline_result
        )

        print(
            f"{cutoff_year}: "
            f"{baseline_result.per_origin_score:.4f}"
        )

    print()
    print(
        "Running autonomous revision gate..."
    )

    candidate_origin_map = {
        policy.policy_id: tuple(
            evaluations[
                policy.policy_id
            ]
        )
        for policy in CANDIDATE_POLICIES
    }

    selection = evaluate_revision_gate(
        tuple(
            evaluations["V1"]
        ),
        candidate_origin_map,
        bootstrap_reps=(
            args.bootstrap_reps
        ),
        bootstrap_seed=0,
    )

    print()
    print(
        "POOLED VALIDATION SCORES"
    )

    pooled_scores = {}

    for policy in policies:
        score = pooled_validation_score(
            evaluations[
                policy.policy_id
            ]
        )

        pooled_scores[
            policy.policy_id
        ] = float(score)

        print(
            f"{policy.policy_id}: "
            f"{score:.4f}"
        )

    baseline_pooled = (
        pooled_validation_score(
            baseline_evaluations
        )
    )

    print(
        "count_only:",
        f"{baseline_pooled:.4f}",
    )

    print()
    print(
        "AUTONOMOUS GATE"
    )

    for decision in selection.decisions:
        print(
            f"{decision.candidate_id}: "
            f"{decision.decision} | "
            f"wins={decision.origin_wins}/"
            f"{decision.n_origins} | "
            f"delta={decision.difference:.6f} | "
            f"SE={decision.bootstrap_se:.6f} | "
            f"required={decision.required_delta:.6f}"
        )

    print()
    print(
        "selected V2 policy:",
        selection.selected_policy_id,
    )
    print(
        "V2 equals V1:",
        selection.v2_equals_v1,
    )

    outcome_reachability = [
        reachable_outcome_share(
            cutoff_year=cutoff,
            pipes=pipes,
            breaks=breaks,
            associations=associations,
        )
        for cutoff in VALIDATION_ORIGINS
    ]

    payload = {
        "validation_only": True,
        "max_break_year_used": (
            MAX_VALIDATION_OUTCOME_YEAR
        ),
        "final_test_executed": False,
        "origins": list(
            VALIDATION_ORIGINS
        ),
        "training_lag_years": (
            TRAINING_LAG_YEARS
        ),
        "horizon_years": (
            HORIZON_YEARS
        ),
        "bootstrap_reps": (
            args.bootstrap_reps
        ),
        "data_diagnostics": (
            diagnostics
        ),
        "validation_break_rows": int(
            len(breaks)
        ),
        "association_diagnostics": {
            "associated_breaks": int(
                associations[
                    "associated"
                ].sum()
            ),
            "ambiguous_breaks": int(
                associations[
                    "ambiguous"
                ].sum()
            ),
            "association_share": float(
                associations[
                    "associated"
                ].mean()
            ),
        },
        "outcome_reachability": (
            outcome_reachability
        ),
        "policies": [
            policy_payload(policy)
            for policy in policies
        ],
        "training": (
            training_diagnostics
        ),
        "results": {
            policy.policy_id: [
                evaluation_payload(
                    item
                )
                for item in evaluations[
                    policy.policy_id
                ]
            ]
            for policy in policies
        },
        "count_only": [
            evaluation_payload(
                item
            )
            for item in baseline_evaluations
        ],
        "pooled_scores": {
            **pooled_scores,
            "count_only": float(
                baseline_pooled
            ),
        },
        "revision_gate": {
            "selected_policy_id": (
                selection.selected_policy_id
            ),
            "v1_policy_id": (
                selection.v1_policy_id
            ),
            "v2_equals_v1": (
                selection.v2_equals_v1
            ),
            "decisions": [
                decision.to_candidate_payload()
                for decision
                in selection.decisions
            ],
        },
    }

    args.out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.out.write_text(
        json.dumps(
            payload,
            indent=2,
        )
        + "\n"
    )

    print()
    print(
        "Validation preview written to:"
    )
    print(
        args.out
    )

    print()
    print(
        "FINAL TEST WAS NOT EXECUTED."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
