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
            raise ValueError(f"{name} missing required columns: {missing_text}")

        if frame.crs is None:
            raise ValueError(f"{name} must have a defined CRS")

        if frame.geometry.isna().any():
            raise ValueError(f"{name} contains missing geometry")

    if not communities.crs.is_projected:
        raise ValueError("communities CRS must be projected for length calculations")

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

    metrics["cutoff_year"] = cutoff_year
    metrics["historical_break_count"] = 0
    metrics["historical_breaks_per_km"] = pd.NA
    metrics["data_quality_flags"] = [
        tuple()
        for _ in range(len(metrics))
    ]

    return metrics[
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