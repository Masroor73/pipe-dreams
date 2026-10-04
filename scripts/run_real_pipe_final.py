"""Run the single corrected Pipe Dreams final evaluation.

FROZEN DESIGN
-------------
Planning cutoff: 2022
Training cutoff: 2019
Training outcomes: 2020-2022
Final outcomes: 2023-2025

Policies evaluated:
- V1: full history, no recency, per-asset ranking
- V2=C3: full history, no recency, per-metre ranking
- count-only baseline

This script verifies the pre-final freeze before accessing final outcomes.
No 2026 break is used.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from pipe_dreams_engine.agent import (
    CANDIDATE_POLICIES,
    V1_POLICY,
)
from pipe_dreams_engine.evaluation import (
    evaluate_policy_origin,
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
OUT_PATH = (
    ROOT
    / "data"
    / "audit_working"
    / "pipe_final_results.json"
)

TRAINING_CUTOFF = 2019
FINAL_CUTOFF = 2022
HORIZON_YEARS = 3
MAX_FINAL_BREAK_YEAR = 2025

BUDGET_SHARES = (
    0.01,
    0.02,
    0.05,
    0.10,
)

EXPECTED_TAG = "pre-final-freeze-2026-10-04"


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def verify_freeze() -> dict:
    freeze = json.loads(
        FREEZE_PATH.read_text()
    )

    if freeze["freeze_stage"] != "pre_final":
        raise RuntimeError(
            "freeze manifest is not pre_final"
        )

    if freeze["final_test_executed"] is not False:
        raise RuntimeError(
            "freeze manifest does not represent "
            "the untouched final state"
        )

    if freeze["selected_policy_id"] != "C3":
        raise RuntimeError(
            "frozen selected policy is not C3"
        )

    if freeze["v1_policy_id"] != "V1":
        raise RuntimeError(
            "frozen V1 policy mismatch"
        )

    if freeze["final_cutoff_year"] != FINAL_CUTOFF:
        raise RuntimeError(
            "frozen final cutoff mismatch"
        )

    if freeze["final_outcome_years"] != [
        2023,
        2024,
        2025,
    ]:
        raise RuntimeError(
            "frozen final outcome years mismatch"
        )

    config_hash = sha256(
        CONFIG_PATH
    )

    if config_hash != freeze["config_sha256"]:
        raise RuntimeError(
            "policy config changed after pre-final freeze"
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
                f"{name} changed after pre-final freeze"
            )

    tag_commit = subprocess.check_output(
        [
            "git",
            "rev-list",
            "-n",
            "1",
            EXPECTED_TAG,
        ],
        text=True,
        cwd=ROOT,
    ).strip()

    if not tag_commit:
        raise RuntimeError(
            "pre-final freeze tag cannot be resolved"
        )

    print("Pre-final freeze verified.")
    print(
        "methodology commit:",
        freeze["frozen_methodology_commit"],
    )
    print(
        "freeze tag commit:",
        tag_commit,
    )
    print(
        "config sha256:",
        freeze["config_sha256"],
    )

    return freeze


def evaluation_payload(
    evaluation,
) -> dict:
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
                            row["budget_share"]
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
                    row["event_capture"]
                ),
                "selected_assets": int(
                    row["selected_assets"]
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
                    row["future_events"]
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


def outcome_reachability(
    *,
    pipes: pd.DataFrame,
    breaks: pd.DataFrame,
    associations: pd.DataFrame,
) -> dict:
    years = pd.to_numeric(
        breaks["break_year"],
        errors="coerce",
    ).to_numpy(dtype=float)

    outcome_mask = (
        np.isfinite(years)
        & (years > FINAL_CUTOFF)
        & (
            years
            <= FINAL_CUTOFF + HORIZON_YEARS
        )
    )

    total = int(
        outcome_mask.sum()
    )

    associated_mask = (
        outcome_mask
        & associations[
            "associated"
        ].to_numpy(dtype=bool)
    )

    associated = int(
        associated_mask.sum()
    )

    reachable = np.zeros(
        len(breaks),
        dtype=bool,
    )

    positions = np.flatnonzero(
        associated_mask
    )

    if len(positions):
        pipe_positions = (
            associations.iloc[
                positions
            ][
                "nearest_segment_idx"
            ]
            .to_numpy(dtype=int)
        )

        install_year = (
            pd.to_numeric(
                pipes.iloc[
                    pipe_positions
                ]["install_year"],
                errors="coerce",
            )
            .to_numpy(dtype=float)
        )

        reachable[
            positions
        ] = (
            install_year
            <= FINAL_CUTOFF
        )

    reachable_count = int(
        reachable.sum()
    )

    return {
        "outcome_break_events": total,
        "associated_break_events": associated,
        "reachable_break_events": (
            reachable_count
        ),
        "matched_share": (
            associated / total
            if total
            else None
        ),
        "reachable_share": (
            reachable_count / total
            if total
            else None
        ),
    }


def main() -> int:
    print(
        "PIPE DREAMS CORRECTED FINAL EVALUATION"
    )
    print(
        "2022 cutoff -> 2023-2025 outcomes"
    )
    print()

    freeze = verify_freeze()

    print()
    print(
        "Loading frozen source data..."
    )

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

    # Explicitly exclude 2026 YTD from the corrected final test.
    breaks = (
        all_breaks.loc[
            pd.to_numeric(
                all_breaks["break_year"],
                errors="coerce",
            )
            <= MAX_FINAL_BREAK_YEAR
        ]
        .copy()
        .reset_index(drop=True)
    )

    if (
        pd.to_numeric(
            breaks["break_year"],
            errors="coerce",
        ).max()
        > MAX_FINAL_BREAK_YEAR
    ):
        raise RuntimeError(
            "2026 data entered corrected final evaluation"
        )

    print(
        f"eligible pipes: {len(pipes):,}"
    )
    print(
        f"breaks through 2025: {len(breaks):,}"
    )
    print(
        f"communities: {len(communities):,}"
    )

    print()
    print(
        "Associating breaks through 2025..."
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
    print(
        "Building frozen 2019 training snapshot..."
    )

    training_snapshot = (
        build_evidence_snapshot(
            pipes,
            breaks,
            associations,
            cutoff_year=TRAINING_CUTOFF,
            history_start_year=None,
            recency="none",
        )
    )

    training_frame = (
        attach_future_outcomes(
            training_snapshot,
            pipes,
            breaks,
            associations,
            cutoff_year=TRAINING_CUTOFF,
            horizon_years=HORIZON_YEARS,
        )
    )

    fitted = fit_pipe_model(
        training_frame
    )

    print(
        f"training rows: {fitted.n_training_rows:,}"
    )
    print(
        f"training positives: {fitted.n_positive:,}"
    )
    print(
        "training positive rate:",
        f"{fitted.positive_rate:.6f}",
    )

    print()
    print(
        "Building 2022 scoring snapshot..."
    )

    final_snapshot = (
        build_evidence_snapshot(
            pipes,
            breaks,
            associations,
            cutoff_year=FINAL_CUTOFF,
            history_start_year=None,
            recency="none",
        )
    )

    final_frame = (
        attach_future_outcomes(
            final_snapshot,
            pipes,
            breaks,
            associations,
            cutoff_year=FINAL_CUTOFF,
            horizon_years=HORIZON_YEARS,
        )
    )

    scores = score_pipe_model(
        fitted,
        final_frame,
    )

    print(
        f"2022 eligible assets: {len(final_frame):,}"
    )
    print(
        "2023-2025 breaking assets:",
        f"{int(final_frame['future_break_label'].sum()):,}",
    )
    print(
        "2023-2025 matched future events:",
        f"{int(final_frame['future_break_events'].sum()):,}",
    )

    print()
    print(
        "Evaluating V1..."
    )

    v1 = evaluate_policy_origin(
        final_frame,
        scores,
        cutoff_year=FINAL_CUTOFF,
        ranking_mode="per_asset",
        budget_shares=BUDGET_SHARES,
    )

    print(
        "V1 final score:",
        f"{v1.per_origin_score:.4f}",
    )

    print()
    print(
        "Evaluating frozen V2=C3..."
    )

    c3 = next(
        p
        for p in CANDIDATE_POLICIES
        if p.policy_id == "C3"
    )

    if (
        c3.history_window != "full"
        or c3.recency_decay != "none"
        or c3.ranking_normalization != "per_meter"
    ):
        raise RuntimeError(
            "C3 definition changed after freeze"
        )

    v2 = evaluate_policy_origin(
        final_frame,
        scores,
        cutoff_year=FINAL_CUTOFF,
        ranking_mode="per_metre",
        budget_shares=BUDGET_SHARES,
    )

    print(
        "C3 final score:",
        f"{v2.per_origin_score:.4f}",
    )

    print()
    print(
        "Evaluating count-only baseline..."
    )

    baseline_scores = (
        count_baseline_scores(
            final_frame
        )
    )

    baseline = evaluate_policy_origin(
        final_frame,
        baseline_scores,
        cutoff_year=FINAL_CUTOFF,
        ranking_mode="per_asset",
        budget_shares=BUDGET_SHARES,
    )

    print(
        "count-only final score:",
        f"{baseline.per_origin_score:.4f}",
    )

    delta_v2_v1 = (
        v2.per_origin_score
        - v1.per_origin_score
    )

    relative_lift = (
        delta_v2_v1
        / v1.per_origin_score
        if v1.per_origin_score
        else None
    )

    reachability = (
        outcome_reachability(
            pipes=pipes,
            breaks=breaks,
            associations=associations,
        )
    )

    payload = {
        "final_test_executed": True,
        "final_test": {
            "cutoff_year": FINAL_CUTOFF,
            "outcome_years": [
                2023,
                2024,
                2025,
            ],
            "previously_viewed": True,
            "max_break_year_used": (
                MAX_FINAL_BREAK_YEAR
            ),
        },
        "freeze": {
            "selected_policy_id": (
                freeze[
                    "selected_policy_id"
                ]
            ),
            "v1_policy_id": (
                freeze[
                    "v1_policy_id"
                ]
            ),
            "frozen_methodology_commit": (
                freeze[
                    "frozen_methodology_commit"
                ]
            ),
            "git_tag": EXPECTED_TAG,
            "config_sha256": (
                freeze[
                    "config_sha256"
                ]
            ),
        },
        "training": {
            "cutoff_year": TRAINING_CUTOFF,
            "outcome_years": [
                2020,
                2021,
                2022,
            ],
            "rows": int(
                fitted.n_training_rows
            ),
            "positives": int(
                fitted.n_positive
            ),
            "positive_rate": float(
                fitted.positive_rate
            ),
        },
        "outcome_reachability": (
            reachability
        ),
        "results": {
            "V1": evaluation_payload(
                v1
            ),
            "C3": evaluation_payload(
                v2
            ),
            "count_only": (
                evaluation_payload(
                    baseline
                )
            ),
        },
        "comparison": {
            "c3_minus_v1": float(
                delta_v2_v1
            ),
            "c3_relative_lift_vs_v1": (
                float(relative_lift)
                if relative_lift
                is not None
                else None
            ),
            "c3_minus_count_only": float(
                v2.per_origin_score
                - baseline.per_origin_score
            ),
        },
        "data_diagnostics": diagnostics,
    }

    OUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT_PATH.write_text(
        json.dumps(
            payload,
            indent=2,
        )
        + "\n"
    )

    print()
    print(
        "FINAL COMPARISON"
    )
    print(
        "C3 - V1:",
        f"{delta_v2_v1:+.6f}",
    )

    if relative_lift is not None:
        print(
            "C3 relative lift vs V1:",
            f"{relative_lift:+.2%}",
        )

    print(
        "C3 - count-only:",
        f"{v2.per_origin_score - baseline.per_origin_score:+.6f}",
    )

    print()
    print(
        "Outcome reachability:",
        f"{reachability['reachable_share']:.2%}",
    )

    print()
    print(
        "Final results written to:"
    )
    print(
        OUT_PATH
    )

    print()
    print(
        "CORRECTED FINAL TEST COMPLETE."
    )
    print(
        "Do not tune policies or thresholds "
        "from this result."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
