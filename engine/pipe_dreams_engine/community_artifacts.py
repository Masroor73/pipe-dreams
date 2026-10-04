"""Artifact generation for community intelligence outputs.

This module converts community metrics and rolling validation results into
the frozen CSV and GeoJSON artifacts consumed by FastAPI.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from pipe_dreams_engine.community import build_community_metrics
from pipe_dreams_engine.community_validation import (
    DEFAULT_COMMUNITY_VALIDATION_ORIGINS,
    DEFAULT_NETWORK_BUDGETS_PCT,
    CommunityValidationOrigin,
    evaluate_rolling_community_origins,
)

COMMUNITY_CSV_COLUMNS = [
    "community_id",
    "community_name",
    "cutoff_year",
    "pipe_length_km",
    "historical_break_count",
    "historical_breaks_per_km",
    "population",
    "equity_index",
    "equity_geography_status",
    "data_quality_flags",
]

COMMUNITY_VALIDATION_COLUMNS = [
    "origin_cutoff",
    "outcome_start_year",
    "outcome_end_year",
    "budget_pct",
    "communities_evaluated",
    "selected_community_count",
    "selected_pipe_length_km",
    "eligible_pipe_length_km",
    "actual_network_share",
    "future_break_events",
    "future_break_events_assigned",
    "future_break_events_unassigned",
    "future_break_events_ambiguous",
    "future_break_events_in_eligible_network",
    "future_break_events_outside_eligible_network",
    "selected_future_break_events",
    "event_capture",
    "lift_vs_network_share",
    "notes",
]


def _prepare_community_artifact_rows(
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    """Convert engine metrics into the frozen community artifact schema."""

    result = metrics.copy()

    result["population"] = pd.NA
    result["equity_index"] = pd.NA
    result["equity_geography_status"] = "NOT_ASSESSED"

    result["data_quality_flags"] = result[
        "data_quality_flags"
    ].apply(
        lambda flags: json.dumps(list(flags))
    )

    return result[COMMUNITY_CSV_COLUMNS]


def _community_geojson(
    communities: gpd.GeoDataFrame,
    artifact_rows: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """Attach frozen indicators to community polygons for map output."""

    joined = communities[
        [
            "community_id",
            "geometry",
        ]
    ].merge(
        artifact_rows,
        on="community_id",
        how="inner",
    )

    geo = gpd.GeoDataFrame(
        joined,
        geometry="geometry",
        crs=communities.crs,
    )

    return geo.to_crs("EPSG:4326")


def write_community_artifacts(
    communities: gpd.GeoDataFrame,
    pipes: gpd.GeoDataFrame,
    breaks: gpd.GeoDataFrame,
    output_dir: str | Path,
    cutoffs: tuple[int, ...] = (
        2013,
        2016,
        2019,
        2022,
    ),
    validation_origins: tuple[
        CommunityValidationOrigin,
        ...,
    ] = DEFAULT_COMMUNITY_VALIDATION_ORIGINS,
    validation_budgets_pct: tuple[
        float,
        ...,
    ] = DEFAULT_NETWORK_BUDGETS_PCT,
) -> dict[str, Path]:
    """Generate frozen community CSV, GeoJSON and validation artifacts."""

    output_path = Path(output_dir)
    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_rows: list[pd.DataFrame] = []
    written: dict[str, Path] = {}

    for cutoff_year in cutoffs:
        metrics = build_community_metrics(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            cutoff_year=cutoff_year,
        )

        artifact_rows = (
            _prepare_community_artifact_rows(
                metrics
            )
        )

        all_rows.append(artifact_rows)

        geo = _community_geojson(
            communities=communities,
            artifact_rows=artifact_rows,
        )

        geojson_path = (
            output_path
            / f"communities_{cutoff_year}.geojson"
        )

        geo_for_output = geo.set_index(
            "community_id",
            drop=False,
        )

        geojson_path.write_text(
            geo_for_output.to_json(
                drop_id=False,
            ),
            encoding="utf-8",
        )

        written[
            f"communities_{cutoff_year}_geojson"
        ] = geojson_path

    communities_csv = pd.concat(
        all_rows,
        ignore_index=True,
    )

    communities_csv_path = (
        output_path / "communities.csv"
    )

    communities_csv.to_csv(
        communities_csv_path,
        index=False,
    )

    written["communities_csv"] = (
        communities_csv_path
    )

    validation = (
        evaluate_rolling_community_origins(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            origins=validation_origins,
            budgets_pct=validation_budgets_pct,
        )
    )

    validation = validation[
        COMMUNITY_VALIDATION_COLUMNS
    ]

    validation_path = (
        output_path
        / "community_validation.csv"
    )

    validation.to_csv(
        validation_path,
        index=False,
    )

    written["community_validation_csv"] = (
        validation_path
    )

    return written