"""Historical evaluation and spatial uncertainty for pipe policies.

Authoritative protocol:
    docs/EXPERIMENT_PROTOCOL.md

Primary validation metric:
    mean future-breaking-asset capture across 1%, 2%, 5%, and 10%
    of eligible network length.

Pooled validation score:
    mean of the per-origin scores across cutoffs 2013, 2016, and 2019.

Spatial uncertainty:
    paired 1 km x 1 km block bootstrap in EPSG:3776.

This module evaluates already-generated ranking scores. It does not decide
whether a candidate policy is accepted; the autonomous gate belongs in
``agent.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pipe_dreams_engine.planner import (
    DEFAULT_BUDGET_SHARES,
    RANK_PER_ASSET,
    build_multi_budget_plans,
)


VALIDATION_CUTOFFS = (
    2013,
    2016,
    2019,
)

FINAL_TEST_CUTOFF = 2022

SPATIAL_BLOCK_M = 1000.0
DEFAULT_BOOTSTRAP_REPS = 1000
DEFAULT_BOOTSTRAP_SEED = 0

TARGET_COLUMN = "future_break_label"
EVENT_COLUMN = "future_break_events"


@dataclass(frozen=True)
class OriginEvaluation:
    """Evaluation result for one historical cutoff."""

    cutoff_year: int
    ranking_mode: str
    budget_results: pd.DataFrame
    per_origin_score: float
    selections: dict[float, pd.Series]
    block_ids: pd.Series
    labels: pd.Series
    events: pd.Series


@dataclass(frozen=True)
class BootstrapResult:
    """Paired spatial-block bootstrap summary."""

    standard_error: float
    mean_bootstrap_improvement: float
    reps_requested: int
    reps_used: int
    block_size_m: float
    seed: int


def _validate_outcomes(
    frame: pd.DataFrame,
    *,
    target_column: str,
    event_column: str,
) -> tuple[pd.Series, pd.Series]:
    missing = {
        target_column,
        event_column,
        "geometry",
        "length_m",
        "asset_id",
    } - set(frame.columns)

    if missing:
        raise ValueError(
            f"evaluation frame missing required columns: "
            f"{sorted(missing)}"
        )

    labels = pd.to_numeric(
        frame[target_column],
        errors="coerce",
    )

    if labels.isna().any():
        raise ValueError(
            f"{target_column!r} contains missing or non-numeric values"
        )

    labels = labels.astype(int)

    if not set(labels.unique()).issubset({0, 1}):
        raise ValueError(
            f"{target_column!r} must contain only binary 0/1 labels"
        )

    events = pd.to_numeric(
        frame[event_column],
        errors="coerce",
    )

    if events.isna().any():
        raise ValueError(
            f"{event_column!r} contains missing or non-numeric values"
        )

    if (events < 0).any():
        raise ValueError(
            f"{event_column!r} cannot contain negative values"
        )

    if ((events > 0).astype(int) != labels).any():
        raise ValueError(
            "future_break_label must equal "
            "(future_break_events > 0)"
        )

    return (
        pd.Series(
            labels.to_numpy(dtype=int),
            index=frame.index,
            name=target_column,
        ),
        pd.Series(
            events.to_numpy(dtype=float),
            index=frame.index,
            name=event_column,
        ),
    )


def spatial_block_ids(
    frame: pd.DataFrame,
    *,
    geometry_column: str = "geometry",
    block_size_m: float = SPATIAL_BLOCK_M,
) -> pd.Series:
    """Assign each pipe to a deterministic square spatial block.

    The geometry centroid is used solely to assign the pipe to one
    1 km x 1 km bootstrap block. This does not imply hydraulic connectivity.

    Geometries must already be in a metre-based CRS. The real-data adapter
    uses EPSG:3776.
    """
    if geometry_column not in frame.columns:
        raise ValueError(
            f"frame missing geometry column {geometry_column!r}"
        )

    if not np.isfinite(block_size_m) or block_size_m <= 0:
        raise ValueError(
            "block_size_m must be finite and positive"
        )

    block_ids = []

    for geom in frame[geometry_column]:
        if geom is None or getattr(geom, "is_empty", False):
            raise ValueError(
                "evaluation geometry cannot be missing or empty"
            )

        centroid = geom.centroid

        if centroid is None or getattr(centroid, "is_empty", False):
            raise ValueError(
                "could not calculate geometry centroid"
            )

        x = float(centroid.x)
        y = float(centroid.y)

        if not np.isfinite(x) or not np.isfinite(y):
            raise ValueError(
                "geometry centroid contains non-finite coordinates"
            )

        bx = int(np.floor(x / block_size_m))
        by = int(np.floor(y / block_size_m))

        block_ids.append(f"{bx}:{by}")

    return pd.Series(
        block_ids,
        index=frame.index,
        name="spatial_block_id",
        dtype="object",
    )


def evaluate_policy_origin(
    frame: pd.DataFrame,
    scores: pd.Series,
    *,
    cutoff_year: int,
    ranking_mode: str = RANK_PER_ASSET,
    budget_shares=DEFAULT_BUDGET_SHARES,
    target_column: str = TARGET_COLUMN,
    event_column: str = EVENT_COLUMN,
    block_size_m: float = SPATIAL_BLOCK_M,
) -> OriginEvaluation:
    """Evaluate one policy at one historical cutoff."""
    labels, events = _validate_outcomes(
        frame,
        target_column=target_column,
        event_column=event_column,
    )

    if labels.sum() <= 0:
        raise ValueError(
            "origin contains no future-breaking assets; "
            "breaking-asset capture is undefined"
        )

    plans = build_multi_budget_plans(
        frame,
        scores,
        budget_shares=budget_shares,
        ranking_mode=ranking_mode,
    )

    total_breaking_assets = int(labels.sum())
    total_events = float(events.sum())

    rows = []
    selections: dict[float, pd.Series] = {}

    for share, (plan, summary) in plans.items():
        selected = (
            plan["selected"]
            .reindex(frame.index)
            .astype(bool)
        )

        if selected.isna().any():
            raise AssertionError(
                "planner selection did not align to evaluation frame"
            )

        selections[float(share)] = selected

        selected_breaking_assets = int(
            labels.loc[selected].sum()
        )

        breaking_asset_capture = (
            selected_breaking_assets
            / total_breaking_assets
        )

        selected_events = float(
            events.loc[selected].sum()
        )

        event_capture = (
            selected_events / total_events
            if total_events > 0
            else np.nan
        )

        rows.append(
            {
                "cutoff_year": int(cutoff_year),
                "budget_share": float(share),
                "ranking_mode": ranking_mode,
                "eligible_assets": int(len(frame)),
                "future_breaking_assets": total_breaking_assets,
                "future_events": total_events,
                "selected_assets": int(
                    summary.selected_asset_count
                ),
                "eligible_network_m": float(
                    summary.eligible_network_m
                ),
                "budget_m": float(summary.budget_m),
                "selected_network_m": float(
                    summary.selected_network_m
                ),
                "selected_network_share": float(
                    summary.selected_network_share
                ),
                "selected_breaking_assets": (
                    selected_breaking_assets
                ),
                "selected_events": selected_events,
                "breaking_asset_capture": float(
                    breaking_asset_capture
                ),
                "event_capture": float(event_capture),
            }
        )

    budget_results = (
        pd.DataFrame(rows)
        .sort_values("budget_share")
        .reset_index(drop=True)
    )

    per_origin_score = float(
        budget_results[
            "breaking_asset_capture"
        ].mean()
    )

    blocks = spatial_block_ids(
        frame,
        block_size_m=block_size_m,
    )

    return OriginEvaluation(
        cutoff_year=int(cutoff_year),
        ranking_mode=ranking_mode,
        budget_results=budget_results,
        per_origin_score=per_origin_score,
        selections=selections,
        block_ids=blocks,
        labels=labels,
        events=events,
    )


def pooled_validation_score(
    origins,
    *,
    required_cutoffs=VALIDATION_CUTOFFS,
) -> float:
    """Mean per-origin score across the frozen validation origins."""
    origins = tuple(origins)

    if len(origins) == 0:
        raise ValueError(
            "origins cannot be empty"
        )

    cutoff_map = {
        result.cutoff_year: result
        for result in origins
    }

    if len(cutoff_map) != len(origins):
        raise ValueError(
            "origins contain duplicate cutoff years"
        )

    required = tuple(
        int(value)
        for value in required_cutoffs
    )

    missing = set(required) - set(cutoff_map)

    if missing:
        raise ValueError(
            f"missing required validation cutoffs: "
            f"{sorted(missing)}"
        )

    scores = [
        cutoff_map[cutoff].per_origin_score
        for cutoff in required
    ]

    if not np.isfinite(scores).all():
        raise ValueError(
            "per-origin scores must be finite"
        )

    return float(np.mean(scores))


def origin_score_table(
    origins,
) -> pd.DataFrame:
    """Return a compact table of per-origin protocol scores."""
    rows = [
        {
            "cutoff_year": result.cutoff_year,
            "ranking_mode": result.ranking_mode,
            "per_origin_score": result.per_origin_score,
        }
        for result in origins
    ]

    if not rows:
        return pd.DataFrame(
            columns=[
                "cutoff_year",
                "ranking_mode",
                "per_origin_score",
            ]
        )

    return (
        pd.DataFrame(rows)
        .sort_values("cutoff_year")
        .reset_index(drop=True)
    )


def _validate_paired_origins(
    v1_origins,
    candidate_origins,
) -> list[tuple[OriginEvaluation, OriginEvaluation]]:
    v1_map = {
        result.cutoff_year: result
        for result in v1_origins
    }
    candidate_map = {
        result.cutoff_year: result
        for result in candidate_origins
    }

    if set(v1_map) != set(candidate_map):
        raise ValueError(
            "V1 and candidate must contain the same cutoff years"
        )

    pairs = []

    for cutoff in sorted(v1_map):
        v1 = v1_map[cutoff]
        candidate = candidate_map[cutoff]

        if not v1.labels.index.equals(
            candidate.labels.index
        ):
            raise ValueError(
                f"asset indexes differ at cutoff {cutoff}"
            )

        if not v1.labels.equals(
            candidate.labels
        ):
            raise ValueError(
                f"future labels differ at cutoff {cutoff}"
            )

        if not v1.block_ids.equals(
            candidate.block_ids
        ):
            raise ValueError(
                f"spatial blocks differ at cutoff {cutoff}"
            )

        if set(v1.selections) != set(
            candidate.selections
        ):
            raise ValueError(
                f"budget sets differ at cutoff {cutoff}"
            )

        pairs.append(
            (v1, candidate)
        )

    return pairs


def paired_spatial_bootstrap_improvement_se(
    v1_origins,
    candidate_origins,
    *,
    reps: int = DEFAULT_BOOTSTRAP_REPS,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> BootstrapResult:
    """Estimate pooled candidate-minus-V1 improvement uncertainty.

    For each validation origin independently:

    1. identify the unique 1 km spatial blocks;
    2. sample the same number of blocks with replacement;
    3. give assets the multiplicity of their sampled block;
    4. recompute breaking-asset capture for every frozen budget.

    The replicate statistic is the mean paired candidate-minus-V1 capture
    difference across all origin/budget combinations with at least one
    resampled positive asset.

    The returned standard deviation of replicate improvements is the
    pooled spatial-block-bootstrap standard error used by the acceptance
    heuristic. It is not a formal significance test.
    """
    if not isinstance(reps, int) or reps < 2:
        raise ValueError(
            "reps must be an integer of at least 2"
        )

    pairs = _validate_paired_origins(
        tuple(v1_origins),
        tuple(candidate_origins),
    )

    if not pairs:
        raise ValueError(
            "at least one paired origin is required"
        )

    rng = np.random.default_rng(seed)
    replicate_improvements = []

    for _ in range(reps):
        differences = []

        for v1, candidate in pairs:
            blocks = v1.block_ids
            unique_blocks = np.asarray(
                sorted(blocks.unique()),
                dtype=object,
            )

            if len(unique_blocks) == 0:
                continue

            sampled = rng.choice(
                unique_blocks,
                size=len(unique_blocks),
                replace=True,
            )

            multiplicity = pd.Series(
                sampled
            ).value_counts()

            weights = (
                blocks
                .map(multiplicity)
                .fillna(0)
                .to_numpy(dtype=float)
            )

            labels = v1.labels.to_numpy(
                dtype=float
            )

            positive_weight = float(
                np.sum(weights * labels)
            )

            if positive_weight <= 0:
                continue

            for share in sorted(
                v1.selections
            ):
                v1_selected = (
                    v1.selections[share]
                    .to_numpy(dtype=bool)
                )
                candidate_selected = (
                    candidate.selections[share]
                    .to_numpy(dtype=bool)
                )

                v1_capture = float(
                    np.sum(
                        weights
                        * labels
                        * v1_selected
                    )
                    / positive_weight
                )

                candidate_capture = float(
                    np.sum(
                        weights
                        * labels
                        * candidate_selected
                    )
                    / positive_weight
                )

                differences.append(
                    candidate_capture
                    - v1_capture
                )

        if differences:
            replicate_improvements.append(
                float(np.mean(differences))
            )

    values = np.asarray(
        replicate_improvements,
        dtype=float,
    )

    if len(values) < 2:
        raise ValueError(
            "fewer than two usable bootstrap replicates"
        )

    if not np.isfinite(values).all():
        raise AssertionError(
            "bootstrap produced non-finite improvements"
        )

    return BootstrapResult(
        standard_error=float(
            np.std(values, ddof=1)
        ),
        mean_bootstrap_improvement=float(
            np.mean(values)
        ),
        reps_requested=int(reps),
        reps_used=int(len(values)),
        block_size_m=SPATIAL_BLOCK_M,
        seed=int(seed),
    )
    