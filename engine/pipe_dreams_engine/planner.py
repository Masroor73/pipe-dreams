"""Capacity-constrained pipe inspection planning.

The planner converts a pipe-level ranking signal into inspection selections
under fixed network-length capacity budgets.

Important distinction:

- ``per_asset`` ranks directly by the supplied score.
- ``per_metre`` ranks by score / pipe length.

Every policy is still constrained by cumulative inspected network length.
Per-metre normalization changes the ranking key; it does not change the
capacity definition.

This module does not use future outcomes and does not evaluate policy quality.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


RANK_PER_ASSET = "per_asset"
RANK_PER_METRE = "per_metre"
VALID_RANKING_MODES = {
    RANK_PER_ASSET,
    RANK_PER_METRE,
}

DEFAULT_BUDGET_SHARES = (
    0.01,
    0.02,
    0.05,
    0.10,
)


@dataclass(frozen=True)
class CapacityPlanSummary:
    """Metadata describing one capacity-constrained inspection plan."""

    budget_share: float
    ranking_mode: str
    eligible_network_m: float
    budget_m: float
    selected_network_m: float
    selected_network_share: float
    selected_asset_count: int


def _validate_frame(
    frame: pd.DataFrame,
    *,
    length_column: str,
    asset_id_column: str,
) -> None:
    required = {
        length_column,
        asset_id_column,
    }
    missing = required - set(frame.columns)

    if missing:
        raise ValueError(
            f"planner frame missing required columns: {sorted(missing)}"
        )

    if not frame.index.is_unique:
        raise ValueError("planner frame index must be unique")

    asset_ids = frame[asset_id_column]

    if asset_ids.isna().any():
        raise ValueError(
            f"{asset_id_column!r} contains missing values"
        )

    if asset_ids.duplicated().any():
        raise ValueError(
            f"{asset_id_column!r} must be unique"
        )

    lengths = pd.to_numeric(
        frame[length_column],
        errors="coerce",
    )

    if lengths.isna().any():
        raise ValueError(
            f"{length_column!r} contains missing or non-numeric values"
        )

    if not np.isfinite(lengths.to_numpy(dtype=float)).all():
        raise ValueError(
            f"{length_column!r} contains non-finite values"
        )

    if (lengths <= 0).any():
        raise ValueError(
            f"{length_column!r} must contain only positive lengths"
        )


def _validate_scores(
    frame: pd.DataFrame,
    scores: pd.Series,
) -> pd.Series:
    if not isinstance(scores, pd.Series):
        raise TypeError("scores must be a pandas Series")

    if not scores.index.equals(frame.index):
        raise ValueError(
            "scores index must exactly match planner frame index"
        )

    numeric = pd.to_numeric(
        scores,
        errors="coerce",
    )

    if numeric.isna().any():
        raise ValueError(
            "scores contains missing or non-numeric values"
        )

    values = numeric.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError(
            "scores contains non-finite values"
        )

    return pd.Series(
        values,
        index=frame.index,
        name=scores.name or "score",
        dtype=float,
    )


def ranking_key(
    frame: pd.DataFrame,
    scores: pd.Series,
    *,
    ranking_mode: str = RANK_PER_ASSET,
    length_column: str = "length_m",
    asset_id_column: str = "asset_id",
) -> pd.Series:
    """Return the deterministic ranking key for a policy.

    ``per_asset``:
        key = score

    ``per_metre``:
        key = score / pipe_length_m
    """
    _validate_frame(
        frame,
        length_column=length_column,
        asset_id_column=asset_id_column,
    )
    scores = _validate_scores(frame, scores)

    if ranking_mode not in VALID_RANKING_MODES:
        raise ValueError(
            f"unsupported ranking mode {ranking_mode!r}; "
            f"expected one of {sorted(VALID_RANKING_MODES)}"
        )

    if ranking_mode == RANK_PER_ASSET:
        key = scores.to_numpy(dtype=float)
    else:
        lengths = pd.to_numeric(
            frame[length_column],
            errors="raise",
        ).to_numpy(dtype=float)
        key = scores.to_numpy(dtype=float) / lengths

    return pd.Series(
        key,
        index=frame.index,
        name="ranking_key",
        dtype=float,
    )


def rank_assets(
    frame: pd.DataFrame,
    scores: pd.Series,
    *,
    ranking_mode: str = RANK_PER_ASSET,
    length_column: str = "length_m",
    asset_id_column: str = "asset_id",
) -> pd.DataFrame:
    """Return all eligible assets in deterministic ranking order.

    Ties are resolved by asset ID, not random numbers. This keeps historical
    replay reproducible.
    """
    _validate_frame(
        frame,
        length_column=length_column,
        asset_id_column=asset_id_column,
    )
    scores = _validate_scores(frame, scores)

    key = ranking_key(
        frame,
        scores,
        ranking_mode=ranking_mode,
        length_column=length_column,
        asset_id_column=asset_id_column,
    )

    ranked = frame.copy()
    ranked["raw_score"] = scores
    ranked["ranking_key"] = key

    ranked["_asset_id_sort"] = (
        ranked[asset_id_column]
        .astype(str)
    )

    ranked = ranked.sort_values(
        by=[
            "ranking_key",
            "raw_score",
            "_asset_id_sort",
        ],
        ascending=[
            False,
            False,
            True,
        ],
        kind="mergesort",
    ).drop(columns=["_asset_id_sort"])

    ranked["rank"] = np.arange(
        1,
        len(ranked) + 1,
        dtype=int,
    )

    ranked["cumulative_length_m"] = (
        pd.to_numeric(
            ranked[length_column],
            errors="raise",
        )
        .astype(float)
        .cumsum()
    )

    return ranked


def build_capacity_plan(
    frame: pd.DataFrame,
    scores: pd.Series,
    *,
    budget_share: float,
    ranking_mode: str = RANK_PER_ASSET,
    length_column: str = "length_m",
    asset_id_column: str = "asset_id",
) -> tuple[pd.DataFrame, CapacityPlanSummary]:
    """Build one ranked plan under a fixed share of eligible network length.

    Selection is the longest ranked prefix whose cumulative length does not
    exceed the capacity budget. We do not skip a higher-ranked long pipe to
    pack lower-ranked shorter pipes into the remaining capacity.

    That preserves the semantics of "follow the ranking until capacity is
    exhausted" rather than turning the planner into a knapsack optimizer.
    """
    if not np.isfinite(budget_share):
        raise ValueError("budget_share must be finite")

    if budget_share <= 0 or budget_share > 1:
        raise ValueError(
            "budget_share must be greater than 0 and at most 1"
        )

    ranked = rank_assets(
        frame,
        scores,
        ranking_mode=ranking_mode,
        length_column=length_column,
        asset_id_column=asset_id_column,
    )

    eligible_network_m = float(
        pd.to_numeric(
            frame[length_column],
            errors="raise",
        ).sum()
    )
    budget_m = (
        float(budget_share)
        * eligible_network_m
    )

    selected = (
        ranked["cumulative_length_m"]
        <= budget_m + 1e-9
    )

    # Because cumulative length is monotonically increasing, selection must
    # form a prefix of the ranking.
    if selected.any():
        last_selected_position = int(
            np.flatnonzero(
                selected.to_numpy()
            )[-1]
        )
        if selected.iloc[
            last_selected_position + 1 :
        ].any():
            raise AssertionError(
                "capacity selection is not a ranked prefix"
            )

    ranked["selected"] = selected.astype(bool)
    ranked["budget_share"] = float(
        budget_share
    )
    ranked["budget_m"] = float(budget_m)
    ranked["ranking_mode"] = ranking_mode

    selected_network_m = float(
        ranked.loc[
            ranked["selected"],
            length_column,
        ].sum()
    )

    selected_asset_count = int(
        ranked["selected"].sum()
    )

    selected_network_share = (
        selected_network_m
        / eligible_network_m
        if eligible_network_m > 0
        else 0.0
    )

    summary = CapacityPlanSummary(
        budget_share=float(budget_share),
        ranking_mode=ranking_mode,
        eligible_network_m=eligible_network_m,
        budget_m=float(budget_m),
        selected_network_m=selected_network_m,
        selected_network_share=float(
            selected_network_share
        ),
        selected_asset_count=selected_asset_count,
    )

    if selected_network_m > budget_m + 1e-6:
        raise AssertionError(
            "selected network exceeds capacity budget"
        )

    return ranked, summary


def build_multi_budget_plans(
    frame: pd.DataFrame,
    scores: pd.Series,
    *,
    budget_shares=DEFAULT_BUDGET_SHARES,
    ranking_mode: str = RANK_PER_ASSET,
    length_column: str = "length_m",
    asset_id_column: str = "asset_id",
) -> dict[float, tuple[pd.DataFrame, CapacityPlanSummary]]:
    """Build plans for each frozen evaluation capacity."""
    shares = tuple(
        float(value)
        for value in budget_shares
    )

    if len(shares) == 0:
        raise ValueError(
            "budget_shares cannot be empty"
        )

    if len(set(shares)) != len(shares):
        raise ValueError(
            "budget_shares must not contain duplicates"
        )

    plans = {}

    for share in shares:
        plan, summary = build_capacity_plan(
            frame,
            scores,
            budget_share=share,
            ranking_mode=ranking_mode,
            length_column=length_column,
            asset_id_column=asset_id_column,
        )
        plans[share] = (
            plan,
            summary,
        )

    return plans
    