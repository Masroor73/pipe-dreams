"""Adapters for Pipe Dreams real-world source datasets.

This module converts the raw hackathon water-main and break datasets,
plus the external City of Calgary community-boundary dataset, into the
standardized GeoDataFrames consumed by the analytical engine.

Raw-source field names and source-specific parsing belong here rather
than inside community/model logic.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import shape


SOURCE_CRS = "EPSG:4326"
ANALYSIS_CRS = "EPSG:3776"


def load_breaks(
    path: str | Path,
) -> gpd.GeoDataFrame:
    """Load raw hackathon break records into the engine schema."""

    source_path = Path(path)

    rows = json.loads(
        source_path.read_text()
    )

    if not isinstance(rows, list):
        raise ValueError(
            "break dataset must contain a top-level JSON list"
        )

    records: list[dict[str, object]] = []

    for index, row in enumerate(rows):
        try:
            break_date = pd.to_datetime(
                row.get("break_date"),
                errors="raise",
            )

            geometry = shape(
                row["point"]
            )
        except Exception as exc:
            raise ValueError(
                f"invalid break row at index {index}: {exc}"
            ) from exc

        records.append(
            {
                "break_year": int(
                    break_date.year
                ),
                "break_date": break_date,
                "break_type": row.get(
                    "break_type"
                ),
                "status": row.get(
                    "status"
                ),
                "geometry": geometry,
            }
        )

    frame = gpd.GeoDataFrame(
        records,
        geometry="geometry",
        crs=SOURCE_CRS,
    )

    if not frame.geometry.geom_type.eq(
        "Point"
    ).all():
        raise ValueError(
            "break dataset contains non-Point geometry"
        )

    return frame.to_crs(
        ANALYSIS_CRS
    )


def load_pipes(
    path: str | Path,
) -> gpd.GeoDataFrame:
    """Load raw hackathon water-main records into the engine schema."""

    source_path = Path(path)

    rows = json.loads(
        source_path.read_text()
    )

    if not isinstance(rows, list):
        raise ValueError(
            "pipe dataset must contain a top-level JSON list"
        )

    records: list[dict[str, object]] = []

    for index, row in enumerate(rows):
        try:
            install_year = int(
                row["year"]
            )

            geometry = shape(
                row["multilinestring"]
            )
        except Exception as exc:
            raise ValueError(
                f"invalid pipe row at index {index}: {exc}"
            ) from exc

        records.append(
            {
                "asset_id": row.get(
                    "globalid"
                ),
                "install_year": install_year,
                "material": row.get(
                    "material"
                ),
                "diameter": row.get(
                    "diam"
                ),
                "source_length": row.get(
                    "length"
                ),
                "pressure_zone": row.get(
                    "p_zone"
                ),
                "status": row.get(
                    "status_ind"
                ),
                "geometry": geometry,
            }
        )

    frame = gpd.GeoDataFrame(
        records,
        geometry="geometry",
        crs=SOURCE_CRS,
    )

    allowed_types = {
        "LineString",
        "MultiLineString",
    }

    unexpected = set(
        frame.geometry.geom_type.unique()
    ).difference(
        allowed_types
    )

    if unexpected:
        raise ValueError(
            "pipe dataset contains unexpected geometry "
            f"types: {sorted(unexpected)}"
        )

    return frame.to_crs(
        ANALYSIS_CRS
    )


def load_communities(
    path: str | Path,
) -> gpd.GeoDataFrame:
    """Load City of Calgary community boundaries into engine schema."""

    source_path = Path(path)

    raw = pd.read_csv(
        source_path
    )

    required = {
        "COMM_CODE",
        "NAME",
        "MULTIPOLYGON",
    }

    missing = required.difference(
        raw.columns
    )

    if missing:
        missing_text = ", ".join(
            sorted(missing)
        )

        raise ValueError(
            "community dataset missing required "
            f"columns: {missing_text}"
        )

    if raw["COMM_CODE"].duplicated().any():
        raise ValueError(
            "community dataset contains duplicate COMM_CODE"
        )

    geometries = []

    for index, value in raw[
        "MULTIPOLYGON"
    ].items():
        try:
            geometry = wkt.loads(
                value
            )
        except Exception as exc:
            raise ValueError(
                "invalid community geometry "
                f"at row {index}: {exc}"
            ) from exc

        if geometry.is_empty:
            raise ValueError(
                "community dataset contains "
                f"empty geometry at row {index}"
            )

        if geometry.geom_type not in {
            "Polygon",
            "MultiPolygon",
        }:
            raise ValueError(
                "community dataset contains "
                "unexpected geometry type "
                f"{geometry.geom_type} at row {index}"
            )

        geometries.append(
            geometry
        )

    frame = gpd.GeoDataFrame(
        {
            "community_id": raw[
                "COMM_CODE"
            ].astype(str),
            "community_name": raw[
                "NAME"
            ].astype(str),
            "class": raw.get(
                "CLASS"
            ),
            "sector": raw.get(
                "SECTOR"
            ),
            "srg": raw.get(
                "SRG"
            ),
        },
        geometry=geometries,
        crs=SOURCE_CRS,
    )

    return frame.to_crs(
        ANALYSIS_CRS
    )


def load_real_inputs(
    breaks_path: str | Path,
    pipes_path: str | Path,
    communities_path: str | Path,
) -> tuple[
    gpd.GeoDataFrame,
    gpd.GeoDataFrame,
    gpd.GeoDataFrame,
    dict[str, object],
]:
    """Load real datasets and exclude non-eligible pipe rows.

    Raw diagnostics are retained for planned and future-install-year rows,
    while the returned pipe frame contains only assets eligible for the
    analytical engine.
    """

    breaks = load_breaks(
        breaks_path
    )

    pipes = load_pipes(
        pipes_path
    )

    communities = load_communities(
        communities_path
    )

    future_mask = (
        pipes["install_year"]
        > 2026
    )

    planned_mask = (
        pipes["status"]
        == "PLANNED"
    )

    excluded_mask = (
        future_mask
        | planned_mask
    )

    eligible_pipes = (
        pipes.loc[
            ~excluded_mask
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    diagnostics = {
        "analysis_crs": ANALYSIS_CRS,
        "break_rows": len(
            breaks
        ),
        "break_year_min": int(
            breaks["break_year"].min()
        ),
        "break_year_max": int(
            breaks["break_year"].max()
        ),
        "pipe_rows": len(
            pipes
        ),
        "pipe_rows_eligible": len(
            eligible_pipes
        ),
        "pipe_rows_excluded": int(
            excluded_mask.sum()
        ),
        "pipe_install_year_min": int(
            pipes["install_year"].min()
        ),
        "pipe_install_year_max": int(
            pipes["install_year"].max()
        ),
        "pipe_future_after_2026": int(
            future_mask.sum()
        ),
        "pipe_planned_rows": int(
            planned_mask.sum()
        ),
        "community_rows": len(
            communities
        ),
    }

    return (
        communities,
        eligible_pipes,
        breaks,
        diagnostics,
    )
