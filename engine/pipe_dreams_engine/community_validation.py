"""Historical rolling evaluation for community infrastructure burden.

This module evaluates whether cutoff-safe historical community burden
identifies communities that contain a larger share of future water-main
break events than their share of eligible pipe-network length.

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

DEFAULT_NETWORK_BUDGETS_PCT = (5, 10, 20)


def _validate_origin(
    origin: CommunityValidationOrigin,
    budget_pct: float,
) -> None:
    """Validate one rolling-origin evaluation definition."""

    if isinstance(budget_pct, bool) or not isinstance(
        budget_pct,
        (int, float),
    ):
        raise TypeError("budget_pct must be numeric")

    if budget_pct <= 0 or budget_pct > 100:
        raise ValueError(
            "budget_pct must be greater than zero and at most 100"
        )

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


def _rank_eligible_communities(
    historical_metrics: pd.DataFrame,
) -> pd.DataFrame:
    """Rank communities using cutoff-safe historical burden only."""

    eligible = historical_metrics.loc[
        historical_metrics["pipe_length_km"] > 0
    ].copy()

    return (
        eligible.sort_values(
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


def _select_to_network_budget(
    ranked_communities: pd.DataFrame,
    budget_pct: float,
) -> tuple[set[str], int, float, float, float]:
    """Select whole communities in rank order until budget is reached.

    Communities are atomic decision units, so the final selected
    community may cause the realized network share to exceed the
    requested budget slightly. Both requested and realized shares are
    reported explicitly.
    """

    eligible_pipe_length_km = float(
        ranked_communities["pipe_length_km"].sum()
    )

    if eligible_pipe_length_km <= 0:
        return set(), 0, 0.0, 0.0, 0.0

    target_pipe_length_km = (
        eligible_pipe_length_km
        * float(budget_pct)
        / 100.0
    )

    cumulative_length_km = 0.0
    selected_ids: set[str] = set()

    for row in ranked_communities.itertuples(index=False):
        if cumulative_length_km >= target_pipe_length_km:
            break

        selected_ids.add(str(row.community_id))
        cumulative_length_km += float(row.pipe_length_km)

    actual_network_share = (
        cumulative_length_km
        / eligible_pipe_length_km
    )

    return (
        selected_ids,
        len(selected_ids),
        cumulative_length_km,
        eligible_pipe_length_km,
        actual_network_share,
    )


def evaluate_community_origin(
    communities: gpd.GeoDataFrame,
    pipes: gpd.GeoDataFrame,
    breaks: gpd.GeoDataFrame,
    origin: CommunityValidationOrigin,
    budget_pct: float = 10,
) -> dict[str, object]:
    """Evaluate one historical community-ranking origin.

    Communities are ranked using information available only through the
    historical cutoff.

    Whole communities are selected in rank order until the requested
    fraction of eligible pipe-network length is reached.

    Event capture is measured among uniquely assigned future break events
    occurring in communities that had eligible pipe network at the
    historical cutoff. Geographic assignment coverage and events outside
    the eligible historical network are reported separately.
    """

    _validate_origin(
        origin=origin,
        budget_pct=budget_pct,
    )

    historical_metrics = build_community_metrics(
        communities=communities,
        pipes=pipes,
        breaks=breaks,
        cutoff_year=origin.cutoff_year,
    )

    eligible_communities = _rank_eligible_communities(
        historical_metrics
    )

    communities_evaluated = len(
        eligible_communities
    )

    (
        selected_ids,
        selected_count,
        selected_pipe_length_km,
        eligible_pipe_length_km,
        actual_network_share,
    ) = _select_to_network_budget(
        ranked_communities=eligible_communities,
        budget_pct=budget_pct,
    )

    eligible_ids = set(
        eligible_communities["community_id"]
        .astype(str)
        .tolist()
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

    eligible_future = assignments.loc[
        assignments["community_id"]
        .astype(str)
        .isin(eligible_ids)
    ]

    future_events_in_eligible_network = len(
        eligible_future
    )

    future_events_outside_eligible_network = (
        assigned_count
        - future_events_in_eligible_network
    )

    selected_future_events = int(
        eligible_future["community_id"]
        .astype(str)
        .isin(selected_ids)
        .sum()
    )

    if future_events_in_eligible_network == 0:
        event_capture = None
        lift_vs_network_share = None
    else:
        event_capture = (
            selected_future_events
            / future_events_in_eligible_network
        )

        if actual_network_share <= 0:
            lift_vs_network_share = None
        else:
            lift_vs_network_share = (
                event_capture
                / actual_network_share
            )

    return {
        "origin_cutoff": origin.cutoff_year,
        "outcome_start_year": (
            origin.outcome_start_year
        ),
        "outcome_end_year": (
            origin.outcome_end_year
        ),
        "budget_pct": float(budget_pct),
        "communities_evaluated": (
            communities_evaluated
        ),
        "selected_community_count": (
            selected_count
        ),
        "selected_pipe_length_km": (
            selected_pipe_length_km
        ),
        "eligible_pipe_length_km": (
            eligible_pipe_length_km
        ),
        "actual_network_share": (
            actual_network_share
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
        "future_break_events_in_eligible_network": (
            future_events_in_eligible_network
        ),
        "future_break_events_outside_eligible_network": (
            future_events_outside_eligible_network
        ),
        "selected_future_break_events": (
            selected_future_events
        ),
        "event_capture": event_capture,
        "lift_vs_network_share": (
            lift_vs_network_share
        ),
        "notes": (
            "Communities are selected in historical-burden rank order "
            "until the requested pipe-network budget is reached. "
            "Because communities are atomic, realized network share may "
            "exceed the requested budget. Event capture uses uniquely "
            "assigned future events in communities with eligible network "
            "at the historical cutoff; other assignment coverage is "
            "reported separately."
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
    budgets_pct: tuple[
        float,
        ...,
    ] = DEFAULT_NETWORK_BUDGETS_PCT,
) -> pd.DataFrame:
    """Evaluate community burden across origins and network budgets."""

    rows = [
        evaluate_community_origin(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            origin=origin,
            budget_pct=budget_pct,
        )
        for origin in origins
        for budget_pct in budgets_pct
    ]

    return pd.DataFrame(rows)