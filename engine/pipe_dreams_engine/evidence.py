"""Cutoff-safe pipe evidence and future outcome construction.

This module deliberately separates:

1. evidence available at a planning cutoff; and
2. future outcomes used only for training/evaluation.

That separation helps prevent temporal leakage.

Geometries are expected to already use a projected metre CRS.
The current real-data adapter uses EPSG:3776.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from shapely import STRtree

from pipe_dreams_engine.matching import eligible_at_cutoff

DEFAULT_NEIGHBORHOOD_M = 200.0
DEFAULT_HORIZON_YEARS = 3

RECENCY_NONE = "none"
RECENCY_HL10 = "hl10"
VALID_RECENCY = {RECENCY_NONE, RECENCY_HL10}


def recency_weights(
    years,
    cutoff_year: int,
    recency: str,
) -> np.ndarray:
    """Return frozen historical-break weights.

    ``none``:
        every historical event receives weight 1.

    ``hl10``:
        exponential decay with a 10-year half-life.

    Only the two recency rules declared in the experiment protocol are
    supported. This function must not be used to tune new half-lives from
    final-window results.
    """
    if recency not in VALID_RECENCY:
        raise ValueError(
            f"unsupported recency mode {recency!r}; "
            f"expected one of {sorted(VALID_RECENCY)}"
        )

    values = np.asarray(
        pd.to_numeric(years, errors="coerce"),
        dtype=float,
    )

    if not np.isfinite(values).all():
        raise ValueError("recency_weights requires finite historical years")

    if np.any(values > cutoff_year):
        raise ValueError(
            "recency_weights received a year after the planning cutoff"
        )

    if recency == RECENCY_NONE:
        return np.ones(len(values), dtype=float)

    return 0.5 ** ((float(cutoff_year) - values) / 10.0)


def _validate_inputs(
    pipes: pd.DataFrame,
    breaks: pd.DataFrame,
    associations: pd.DataFrame,
) -> None:
    required_pipe = {
        "asset_id",
        "install_year",
        "material",
        "diameter",
        "geometry",
    }
    required_break = {
        "break_year",
        "geometry",
    }
    required_assoc = {
        "nearest_segment_idx",
        "nearest_distance_m",
        "associated",
        "ambiguous",
    }

    missing_pipe = required_pipe - set(pipes.columns)
    missing_break = required_break - set(breaks.columns)
    missing_assoc = required_assoc - set(associations.columns)

    if missing_pipe:
        raise ValueError(
            f"pipes missing required columns: {sorted(missing_pipe)}"
        )
    if missing_break:
        raise ValueError(
            f"breaks missing required columns: {sorted(missing_break)}"
        )
    if missing_assoc:
        raise ValueError(
            "associations missing required columns: "
            f"{sorted(missing_assoc)}"
        )

    if len(breaks) != len(associations):
        raise ValueError(
            "breaks and associations must contain the same number of rows"
        )

    if not breaks.index.equals(associations.index):
        raise ValueError(
            "breaks and associations must have identical row indexes"
        )

    if not pipes.index.is_unique:
        raise ValueError("pipes index must be unique")

    if not breaks.index.is_unique:
        raise ValueError("breaks index must be unique")


def _history_mask(
    breaks: pd.DataFrame,
    *,
    cutoff_year: int,
    history_start_year: int | None,
) -> np.ndarray:
    years = np.asarray(
        pd.to_numeric(breaks["break_year"], errors="coerce"),
        dtype=float,
    )

    mask = np.isfinite(years) & (years <= cutoff_year)

    if history_start_year is not None:
        mask &= years >= history_start_year

    return mask


def _historical_association_features(
    *,
    pipes: pd.DataFrame,
    breaks: pd.DataFrame,
    associations: pd.DataFrame,
    cutoff_year: int,
    history_start_year: int | None,
    recency: str,
) -> dict[str, np.ndarray]:
    """Aggregate historical attributed-break evidence by pipe position."""
    n_pipes = len(pipes)

    raw_count = np.zeros(n_pipes, dtype=int)
    weighted_count = np.zeros(n_pipes, dtype=float)
    ambiguous_count = np.zeros(n_pipes, dtype=int)
    distance_sum = np.zeros(n_pipes, dtype=float)

    hist_mask = _history_mask(
        breaks,
        cutoff_year=cutoff_year,
        history_start_year=history_start_year,
    )

    associated = associations["associated"].to_numpy(dtype=bool)
    usable = hist_mask & associated

    if not usable.any():
        return {
            "historical_break_count": raw_count,
            "historical_break_weight": weighted_count,
            "historical_ambiguous_break_count": ambiguous_count,
            "historical_mean_match_distance_m": np.full(
                n_pipes,
                np.nan,
                dtype=float,
            ),
        }

    pipe_pos = associations.loc[
        usable,
        "nearest_segment_idx",
    ].to_numpy(dtype=int)

    if np.any(pipe_pos < 0) or np.any(pipe_pos >= n_pipes):
        raise ValueError(
            "associations contains an invalid nearest_segment_idx"
        )

    years = breaks.loc[usable, "break_year"].to_numpy()
    weights = recency_weights(
        years,
        cutoff_year=cutoff_year,
        recency=recency,
    )

    ambiguity = associations.loc[
        usable,
        "ambiguous",
    ].to_numpy(dtype=bool)

    distances = pd.to_numeric(
        associations.loc[
            usable,
            "nearest_distance_m",
        ],
        errors="coerce",
    ).to_numpy(dtype=float)

    np.add.at(raw_count, pipe_pos, 1)
    np.add.at(weighted_count, pipe_pos, weights)
    np.add.at(
        ambiguous_count,
        pipe_pos,
        ambiguity.astype(int),
    )

    finite_distance = np.isfinite(distances)
    np.add.at(
        distance_sum,
        pipe_pos[finite_distance],
        distances[finite_distance],
    )

    distance_count = np.zeros(n_pipes, dtype=int)
    np.add.at(
        distance_count,
        pipe_pos[finite_distance],
        1,
    )

    mean_distance = np.divide(
        distance_sum,
        distance_count,
        out=np.full(n_pipes, np.nan, dtype=float),
        where=distance_count > 0,
    )

    return {
        "historical_break_count": raw_count,
        "historical_break_weight": weighted_count,
        "historical_ambiguous_break_count": ambiguous_count,
        "historical_mean_match_distance_m": mean_distance,
    }


def _nearby_break_features(
    *,
    pipes: pd.DataFrame,
    breaks: pd.DataFrame,
    associations: pd.DataFrame,
    eligible_positions: np.ndarray,
    cutoff_year: int,
    history_start_year: int | None,
    recency: str,
    neighborhood_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Count historical break activity near, but not attributed to, each pipe.

    This is purely spatial neighbourhood evidence. It must not be described
    as hydraulic connectivity.

    A break attributed to the pipe itself is excluded from that pipe's
    neighbourhood count, matching the recovered audit semantics.
    """
    n_pipes = len(pipes)
    raw = np.zeros(n_pipes, dtype=int)
    weighted = np.zeros(n_pipes, dtype=float)

    hist_mask = _history_mask(
        breaks,
        cutoff_year=cutoff_year,
        history_start_year=history_start_year,
    )
    hist_positions = np.flatnonzero(hist_mask)

    if len(hist_positions) == 0:
        return raw, weighted

    hist_geometries = [
        breaks.iloc[pos]["geometry"]
        for pos in hist_positions
    ]

    tree = STRtree(hist_geometries)

    hist_years = breaks.iloc[
        hist_positions
    ]["break_year"].to_numpy()

    hist_weights = recency_weights(
        hist_years,
        cutoff_year=cutoff_year,
        recency=recency,
    )

    associated = associations["associated"].to_numpy(dtype=bool)
    associated_pipe = associations[
        "nearest_segment_idx"
    ].to_numpy(dtype=int)

    for pipe_pos in eligible_positions:
        geom = pipes.iloc[pipe_pos]["geometry"]

        if geom is None or getattr(geom, "is_empty", False):
            continue

        hits = tree.query(
            geom,
            predicate="dwithin",
            distance=neighborhood_m,
        )

        if len(hits) == 0:
            continue

        hit_local = np.asarray(hits, dtype=int)
        hit_break_positions = hist_positions[hit_local]

        self_attributed = (
            associated[hit_break_positions]
            & (
                associated_pipe[hit_break_positions]
                == pipe_pos
            )
        )

        keep = ~self_attributed

        raw[pipe_pos] = int(keep.sum())

        if keep.any():
            weighted[pipe_pos] = float(
                hist_weights[hit_local[keep]].sum()
            )

    return raw, weighted


def build_evidence_snapshot(
    pipes: pd.DataFrame,
    breaks: pd.DataFrame,
    associations: pd.DataFrame,
    *,
    cutoff_year: int,
    history_start_year: int | None = None,
    recency: str = RECENCY_NONE,
    neighborhood_m: float = DEFAULT_NEIGHBORHOOD_M,
) -> pd.DataFrame:
    """Build features available at the end of ``cutoff_year``.

    No future outcome columns are created here.

    Present-day ``status`` and ``pressure_zone`` are deliberately excluded
    from model features because their historical validity at earlier cutoffs
    has not been established.
    """
    _validate_inputs(pipes, breaks, associations)

    if neighborhood_m <= 0:
        raise ValueError("neighborhood_m must be positive")

    install_year = np.asarray(
        pd.to_numeric(
            pipes["install_year"],
            errors="coerce",
        ),
        dtype=float,
    )

    eligible = np.asarray(
        eligible_at_cutoff(
            install_year,
            cutoff_year,
        ),
        dtype=bool,
    )
    eligible_positions = np.flatnonzero(eligible)

    assoc_features = _historical_association_features(
        pipes=pipes,
        breaks=breaks,
        associations=associations,
        cutoff_year=cutoff_year,
        history_start_year=history_start_year,
        recency=recency,
    )

    nearby_count, nearby_weight = _nearby_break_features(
        pipes=pipes,
        breaks=breaks,
        associations=associations,
        eligible_positions=eligible_positions,
        cutoff_year=cutoff_year,
        history_start_year=history_start_year,
        recency=recency,
        neighborhood_m=neighborhood_m,
    )

    snapshot = pipes.iloc[
        eligible_positions
    ].copy()

    snapshot["cutoff_year"] = int(cutoff_year)
    snapshot["age"] = (
        cutoff_year
        - pd.to_numeric(
            snapshot["install_year"],
            errors="coerce",
        )
    )

    snapshot["length_m"] = [
        float(geom.length)
        if geom is not None
        and not getattr(geom, "is_empty", False)
        else np.nan
        for geom in snapshot["geometry"]
    ]

    snapshot["historical_break_count"] = (
        assoc_features["historical_break_count"][
            eligible_positions
        ]
    )
    snapshot["historical_break_weight"] = (
        assoc_features["historical_break_weight"][
            eligible_positions
        ]
    )
    snapshot["historical_ambiguous_break_count"] = (
        assoc_features[
            "historical_ambiguous_break_count"
        ][eligible_positions]
    )
    snapshot["historical_mean_match_distance_m"] = (
        assoc_features[
            "historical_mean_match_distance_m"
        ][eligible_positions]
    )

    snapshot["nearby_break_count_200m"] = (
        nearby_count[eligible_positions]
    )
    snapshot["nearby_break_weight_200m"] = (
        nearby_weight[eligible_positions]
    )

    snapshot["history_start_year"] = (
        history_start_year
        if history_start_year is not None
        else 0
    )
    snapshot["recency"] = recency

    if (snapshot["age"] < 0).any():
        raise AssertionError(
            "snapshot contains a pipe installed after cutoff"
        )

    return snapshot


def attach_future_outcomes(
    snapshot: pd.DataFrame,
    pipes: pd.DataFrame,
    breaks: pd.DataFrame,
    associations: pd.DataFrame,
    *,
    cutoff_year: int,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
) -> pd.DataFrame:
    """Attach future break labels for training/evaluation only.

    Outcome period:

        cutoff_year < break_year <= cutoff_year + horizon_years

    The returned ``future_break_events`` and ``future_break_label`` columns
    must never be passed to the prediction model as features.
    """
    _validate_inputs(pipes, breaks, associations)

    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")

    years = np.asarray(
        pd.to_numeric(
            breaks["break_year"],
            errors="coerce",
        ),
        dtype=float,
    )

    outcome_mask = (
        np.isfinite(years)
        & (years > cutoff_year)
        & (years <= cutoff_year + horizon_years)
        & associations["associated"].to_numpy(dtype=bool)
    )

    counts = np.zeros(len(pipes), dtype=int)

    if outcome_mask.any():
        pipe_pos = associations.loc[
            outcome_mask,
            "nearest_segment_idx",
        ].to_numpy(dtype=int)

        if np.any(pipe_pos < 0) or np.any(
            pipe_pos >= len(pipes)
        ):
            raise ValueError(
                "associations contains an invalid nearest_segment_idx"
            )

        np.add.at(counts, pipe_pos, 1)

    pipe_index_to_position = {
        index: position
        for position, index in enumerate(pipes.index)
    }

    try:
        snapshot_positions = np.asarray(
            [
                pipe_index_to_position[index]
                for index in snapshot.index
            ],
            dtype=int,
        )
    except KeyError as exc:
        raise ValueError(
            "snapshot contains a pipe index not present in pipes"
        ) from exc

    result = snapshot.copy()
    result["future_break_events"] = counts[
        snapshot_positions
    ]
    result["future_break_label"] = (
        result["future_break_events"] > 0
    ).astype(int)

    result["outcome_start_year"] = cutoff_year + 1
    result["outcome_end_year"] = (
        cutoff_year + horizon_years
    )

    return result