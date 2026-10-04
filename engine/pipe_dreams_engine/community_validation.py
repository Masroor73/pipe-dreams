"""Historical rolling evaluation for community infrastructure burden.

This module evaluates whether cutoff-safe historical community burden
identifies communities that contain a larger share of future water-main
break events.

Community validation is intentionally separate from the pipe-level
V1/C1-C4 autonomous revision gate.
"""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import pandas as pd

from pipe_dreams_engine.community import build_community_metrics


@dataclass(frozen=True)
class CommunityValidationOrigin:
    """One historical community validation origin."""

    cutoff_year: int
    outcome_start_year: int
    outcome_end_year: int


DEFAULT_COMMUNITY_VALIDATION_ORIGINS = (
    CommunityValidationOrigin(
        cutoff_year=2013,
        outcome_start_year=2014,
        outcome_end_year=2016,
    ),
    CommunityValidationOrigin(
        cutoff_year=2016,
        outcome_start_year=2017,
        outcome_end_year=2019,
    ),
    CommunityValidationOrigin(
        cutoff_year=2019,
        outcome_start_year=2020,
        outcome_end_year=2022,
    ),
)


def _validate_origin(
    origin: CommunityValidationOrigin,
    top_n: int,
) -> None:
    """Validate a rolling-origin evaluation definition."""

    if not isinstance(top_n, int):
        raise TypeError("top_n must be an integer")

    if top_n <= 0:
        raise ValueError("top_n must be greater than zero")

    if origin.outcome_start_year <= origin.cutoff_year:
        raise ValueError(
            "outcome_start_year must be after cutoff_year"
        )

    if origin.outcome_end_year < origin.outcome_start_year:
        raise ValueError(
            "outcome_end_year must be on or after outcome_start_year"
        )


def _future_breaks(
    breaks: gpd.GeoDataFrame,
    start_year: int,
    end_year: int,
) -> gpd.GeoDataFrame:
    """Return break events inside an evaluation outcome window."""

    break_year = pd.to_numeric(
        breaks["break_year"],
        errors="coerce",
    )

    mask = (
        break_year.notna()
        & (break_year >= start_year)
        & (break_year <= end_year)
    )

    future = breaks.loc[mask].copy()

    future["break_year"] = (
        break_year.loc[future.index]
        .astype(int)
    )

    return future.reset_index(drop=True)


def _assign_future_breaks(
    communities: gpd.GeoDataFrame,
    breaks: gpd.GeoDataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Assign future break events uniquely to community polygons.

    Breaks outside all communities, on shared boundaries, or inside
    overlapping polygons are not silently assigned.

    Ambiguous events are excluded from event-capture calculations.
    """

    if breaks.empty:
        quality = {
            "future_break_events": 0,
            "future_break_events_assigned": 0,
            "future_break_events_unassigned": 0,
            "future_break_events_ambiguous": 0,
        }

        return pd.DataFrame(
            columns=[
                "break_row_id",
                "community_id",
            ]
        ), quality

    future = breaks.copy()
    future["break_row_id"] = range(len(future))

    joined = gpd.sjoin(
        future[
            [
                "break_row_id",
                "geometry",
            ]
        ],
        communities[
            [
                "community_id",
                "geometry",
            ]
        ],
        how="left",
        predicate="within",
    )

    matched = joined.loc[
        joined["community_id"].notna(),
        [
            "break_row_id",
            "community_id",
        ],
    ].copy()

    total_events = len(future)

    if matched.empty:
        quality = {
            "future_break_events": total_events,
            "future_break_events_assigned": 0,
            "future_break_events_unassigned": total_events,
            "future_break_events_ambiguous": 0,
        }

        return pd.DataFrame(
            columns=[
                "break_row_id",
                "community_id",
            ]
        ), quality

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
        ~matched["break_row_id"].isin(
            ambiguous_ids
        )
    ].drop_duplicates(
        subset=["break_row_id"],
        keep="first",
    )

    assigned_events = len(assignments)

    quality = {
        "future_break_events": total_events,
        "future_break_events_assigned": assigned_events,
        "future_break_events_unassigned": (
            total_events - assigned_events
        ),
        "future_break_events_ambiguous": len(
            ambiguous_ids
        ),
    }

    return assignments.reset_index(drop=True), quality


def evaluate_community_origin(
    communities: gpd.GeoDataFrame,
    pipes: gpd.GeoDataFrame,
    breaks: gpd.GeoDataFrame,
    origin: CommunityValidationOrigin,
    top_n: int = 5,
) -> dict[str, object]:
    """Evaluate one historical community-ranking origin.

    Communities are ranked using only information available through the
    origin cutoff. Future event capture is then measured in the declared
    outcome period.

    Event capture uses uniquely assigned future events as its denominator.
    Geographic assignment coverage is reported separately.
    """

    _validate_origin(
        origin=origin,
        top_n=top_n,
    )

    historical_metrics = build_community_metrics(
        communities=communities,
        pipes=pipes,
        breaks=breaks,
        cutoff_year=origin.cutoff_year,
    )

    eligible_communities = historical_metrics.loc[
        historical_metrics[
            "pipe_length_km"
        ] > 0
    ].copy()

    eligible_communities = (
        eligible_communities.sort_values(
            by=[
                "historical_breaks_per_km",
                "historical_break_count",
                "community_id",
            ],
            ascending=[
                False,
                False,
                True,
            ],
            na_position="last",
        )
        .reset_index(drop=True)
    )

    communities_evaluated = len(
        eligible_communities
    )

    selected_count = min(
        top_n,
        communities_evaluated,
    )

    selected_ids = set(
        eligible_communities.head(
            selected_count
        )["community_id"].tolist()
    )

    future = _future_breaks(
        breaks=breaks,
        start_year=origin.outcome_start_year,
        end_year=origin.outcome_end_year,
    )

    assignments, assignment_quality = (
        _assign_future_breaks(
            communities=communities,
            breaks=future,
        )
    )

    assigned_count = assignment_quality[
        "future_break_events_assigned"
    ]

    if assigned_count == 0:
        capture = None
        selected_future_events = 0
    else:
        selected_future_events = int(
            assignments[
                "community_id"
            ].isin(
                selected_ids
            ).sum()
        )

        capture = (
            selected_future_events
            / assigned_count
        )

    return {
        "origin_cutoff": origin.cutoff_year,
        "outcome_start_year": (
            origin.outcome_start_year
        ),
        "outcome_end_year": (
            origin.outcome_end_year
        ),
        "communities_evaluated": (
            communities_evaluated
        ),
        "future_break_events": (
            assignment_quality[
                "future_break_events"
            ]
        ),
        "future_break_events_assigned": (
            assigned_count
        ),
        "future_break_events_unassigned": (
            assignment_quality[
                "future_break_events_unassigned"
            ]
        ),
        "future_break_events_ambiguous": (
            assignment_quality[
                "future_break_events_ambiguous"
            ]
        ),
        "top_community_count": selected_count,
        "top_community_future_break_events": (
            selected_future_events
        ),
        "top_community_event_capture": capture,
        "notes": (
            "Capture denominator is uniquely assigned "
            "future break events only; unassigned and "
            "ambiguous events are reported separately."
        ),
    }


def evaluate_rolling_community_origins(
    communities: gpd.GeoDataFrame,
    pipes: gpd.GeoDataFrame,
    breaks: gpd.GeoDataFrame,
    origins: tuple[
        CommunityValidationOrigin,
        ...,
    ] = DEFAULT_COMMUNITY_VALIDATION_ORIGINS,
    top_n: int = 5,
) -> pd.DataFrame:
    """Evaluate community burden across multiple historical origins."""

    rows = [
        evaluate_community_origin(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            origin=origin,
            top_n=top_n,
        )
        for origin in origins
    ]

    return pd.DataFrame(rows)