"""Community-level infrastructure analysis for Pipe Dreams.

This module is responsible for:
- assigning historical break events to communities;
- calculating eligible pipe length within community boundaries;
- calculating cutoff-safe historical breaks per kilometre;
- surfacing community-level data-quality flags.

Community analysis is intentionally separate from the pipe-level
V1/C1-C4 model-selection experiment.
"""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import pandas as pd


COMMUNITY_REQUIRED_COLUMNS = {"community_id", "community_name", "geometry"}
PIPE_REQUIRED_COLUMNS = {"install_year", "geometry"}
BREAK_REQUIRED_COLUMNS = {"break_year", "geometry"}

SMALL_DENOMINATOR_KM = 1.0

ZERO_ELIGIBLE_PIPE_LENGTH = "ZERO_ELIGIBLE_PIPE_LENGTH"
SMALL_DENOMINATOR = "SMALL_DENOMINATOR"


def _validate_inputs(
    communities: gpd.GeoDataFrame,
    pipes: gpd.GeoDataFrame,
    breaks: gpd.GeoDataFrame,
    cutoff_year: int,
) -> None:
    """Validate schemas, CRS metadata, and cutoff before spatial analysis."""

    if not isinstance(cutoff_year, int):
        raise TypeError("cutoff_year must be an integer")

    frames = {
        "communities": (communities, COMMUNITY_REQUIRED_COLUMNS),
        "pipes": (pipes, PIPE_REQUIRED_COLUMNS),
        "breaks": (breaks, BREAK_REQUIRED_COLUMNS),
    }

    for name, (frame, required_columns) in frames.items():
        if not isinstance(frame, gpd.GeoDataFrame):
            raise TypeError(f"{name} must be a GeoDataFrame")

        missing = required_columns.difference(frame.columns)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(
                f"{name} missing required columns: {missing_text}"
            )

        if frame.crs is None:
            raise ValueError(f"{name} must have a defined CRS")

        if frame.geometry.isna().any():
            raise ValueError(f"{name} contains missing geometry")

    if communities["community_id"].duplicated().any():
        raise ValueError("communities must have unique community_id values")

    if not communities.crs.is_projected:
        raise ValueError(
            "communities CRS must be projected for length calculations"
        )

    if pipes.crs != communities.crs:
        raise ValueError("pipes CRS must match communities CRS")

    if breaks.crs != communities.crs:
        raise ValueError("breaks CRS must match communities CRS")


def _eligible_pipes(
    pipes: gpd.GeoDataFrame,
    cutoff_year: int,
) -> gpd.GeoDataFrame:
    """Return pipes installed on or before the historical cutoff."""

    install_year = pd.to_numeric(
        pipes["install_year"],
        errors="coerce",
    )

    eligible_mask = (
        install_year.notna()
        & (install_year <= cutoff_year)
    )

    eligible = pipes.loc[eligible_mask].copy()

    eligible["install_year"] = (
        install_year.loc[eligible.index]
        .astype(int)
    )

    return eligible


def _eligible_breaks(
    breaks: gpd.GeoDataFrame,
    cutoff_year: int,
) -> gpd.GeoDataFrame:
    """Return historical break events on or before the cutoff."""

    break_year = pd.to_numeric(
        breaks["break_year"],
        errors="coerce",
    )

    eligible_mask = (
        break_year.notna()
        & (break_year <= cutoff_year)
    )

    eligible = breaks.loc[eligible_mask].copy()

    eligible["break_year"] = (
        break_year.loc[eligible.index]
        .astype(int)
    )

    return eligible


def _pipe_length_by_community(
    communities: gpd.GeoDataFrame,
    pipes: gpd.GeoDataFrame,
    cutoff_year: int,
) -> pd.DataFrame:
    """Calculate eligible pipe length physically inside each community."""

    eligible = _eligible_pipes(
        pipes=pipes,
        cutoff_year=cutoff_year,
    )

    result = communities[
        ["community_id", "community_name"]
    ].copy()

    result["pipe_length_km"] = 0.0

    if eligible.empty:
        return result

    community_geometry = communities[
        ["community_id", "geometry"]
    ].copy()

    clipped = gpd.overlay(
        eligible[["geometry"]],
        community_geometry,
        how="intersection",
        keep_geom_type=False,
    )

    if clipped.empty:
        return result

    clipped = clipped.loc[
        clipped.geometry.notna()
        & ~clipped.geometry.is_empty
    ].copy()

    if clipped.empty:
        return result

    clipped["length_m"] = clipped.geometry.length

    lengths = (
        clipped.groupby(
            "community_id",
            as_index=False,
        )["length_m"]
        .sum()
    )

    lengths["pipe_length_km"] = (
        lengths["length_m"] / 1000.0
    )

    result = result.merge(
        lengths[
            ["community_id", "pipe_length_km"]
        ],
        on="community_id",
        how="left",
        suffixes=("", "_calculated"),
    )

    result["pipe_length_km"] = (
        result["pipe_length_km_calculated"]
        .fillna(result["pipe_length_km"])
        .astype(float)
    )

    result = result.drop(
        columns=["pipe_length_km_calculated"]
    )

    return result


def _assign_breaks_to_communities(
    communities: gpd.GeoDataFrame,
    breaks: gpd.GeoDataFrame,
    cutoff_year: int,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Assign eligible breaks uniquely to communities.

    Breaks outside all community polygons remain unassigned.

    Breaks that match more than one community are treated as ambiguous
    and remain unassigned rather than being silently double-counted.

    A point exactly on a shared polygon boundary is not considered
    within either polygon and therefore remains unassigned.
    """

    eligible = _eligible_breaks(
        breaks=breaks,
        cutoff_year=cutoff_year,
    ).reset_index(drop=True)

    empty_assignments = pd.DataFrame(
        columns=["break_row_id", "community_id"]
    )

    if eligible.empty:
        quality = {
            "eligible_break_count": 0,
            "assigned_break_count": 0,
            "unassigned_break_count": 0,
            "ambiguous_break_count": 0,
        }
        return empty_assignments, quality

    eligible = eligible.copy()
    eligible["break_row_id"] = range(len(eligible))

    joined = gpd.sjoin(
        eligible[
            ["break_row_id", "geometry"]
        ],
        communities[
            ["community_id", "geometry"]
        ],
        how="left",
        predicate="within",
    )

    matched = joined.loc[
        joined["community_id"].notna(),
        ["break_row_id", "community_id"],
    ].copy()

    if matched.empty:
        quality = {
            "eligible_break_count": len(eligible),
            "assigned_break_count": 0,
            "unassigned_break_count": len(eligible),
            "ambiguous_break_count": 0,
        }
        return empty_assignments, quality

    match_counts = (
        matched.groupby("break_row_id")
        .size()
    )

    ambiguous_ids = set(
        match_counts.loc[
            match_counts > 1
        ].index.tolist()
    )

    assignments = matched.loc[
        ~matched["break_row_id"].isin(ambiguous_ids)
    ].drop_duplicates(
        subset=["break_row_id"],
        keep="first",
    )

    assigned_count = len(assignments)
    eligible_count = len(eligible)
    ambiguous_count = len(ambiguous_ids)

    quality = {
        "eligible_break_count": eligible_count,
        "assigned_break_count": assigned_count,
        "unassigned_break_count": eligible_count - assigned_count,
        "ambiguous_break_count": ambiguous_count,
    }

    return assignments.reset_index(drop=True), quality


def _break_count_by_community(
    communities: gpd.GeoDataFrame,
    breaks: gpd.GeoDataFrame,
    cutoff_year: int,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Count uniquely assigned historical breaks by community."""

    result = communities[
        ["community_id"]
    ].copy()

    result["historical_break_count"] = 0

    assignments, quality = _assign_breaks_to_communities(
        communities=communities,
        breaks=breaks,
        cutoff_year=cutoff_year,
    )

    if assignments.empty:
        return result, quality

    counts = (
        assignments.groupby(
            "community_id",
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "size": "historical_break_count"
            }
        )
    )

    result = result.merge(
        counts,
        on="community_id",
        how="left",
        suffixes=("", "_calculated"),
    )

    result["historical_break_count"] = (
        result["historical_break_count_calculated"]
        .fillna(result["historical_break_count"])
        .astype(int)
    )

    result = result.drop(
        columns=[
            "historical_break_count_calculated"
        ]
    )

    return result, quality


def _community_flags(
    pipe_length_km: float,
) -> tuple[str, ...]:
    """Return deterministic community-level data-quality flags."""

    flags: list[str] = []

    if pipe_length_km <= 0:
        flags.append(ZERO_ELIGIBLE_PIPE_LENGTH)
    elif pipe_length_km < SMALL_DENOMINATOR_KM:
        flags.append(SMALL_DENOMINATOR)

    return tuple(flags)


@dataclass(frozen=True)
class CommunityMetric:
    """Frozen community-level metric for a single historical cutoff."""

    community_id: str
    community_name: str
    cutoff_year: int
    pipe_length_km: float
    historical_break_count: int
    historical_breaks_per_km: float | None
    data_quality_flags: tuple[str, ...]


def build_community_metrics(
    communities: gpd.GeoDataFrame,
    pipes: gpd.GeoDataFrame,
    breaks: gpd.GeoDataFrame,
    cutoff_year: int,
) -> pd.DataFrame:
    """Build cutoff-safe community infrastructure metrics."""

    _validate_inputs(
        communities=communities,
        pipes=pipes,
        breaks=breaks,
        cutoff_year=cutoff_year,
    )

    metrics = _pipe_length_by_community(
        communities=communities,
        pipes=pipes,
        cutoff_year=cutoff_year,
    )

    break_counts, assignment_quality = (
        _break_count_by_community(
            communities=communities,
            breaks=breaks,
            cutoff_year=cutoff_year,
        )
    )

    metrics = metrics.merge(
        break_counts,
        on="community_id",
        how="left",
    )

    metrics["historical_break_count"] = (
        metrics["historical_break_count"]
        .fillna(0)
        .astype(int)
    )

    metrics["historical_breaks_per_km"] = (
        metrics["historical_break_count"]
        .div(metrics["pipe_length_km"])
        .where(metrics["pipe_length_km"] > 0)
    )

    metrics["cutoff_year"] = cutoff_year

    metrics["data_quality_flags"] = (
        metrics["pipe_length_km"]
        .apply(_community_flags)
    )

    metrics = metrics[
        [
            "community_id",
            "community_name",
            "cutoff_year",
            "pipe_length_km",
            "historical_break_count",
            "historical_breaks_per_km",
            "data_quality_flags",
        ]
    ]

    metrics.attrs["data_quality"] = {
        "cutoff_year": cutoff_year,
        "small_denominator_threshold_km": SMALL_DENOMINATOR_KM,
        **assignment_quality,
    }

    return metrics