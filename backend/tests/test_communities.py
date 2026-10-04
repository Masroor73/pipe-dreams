"""Community API: optional artifacts, cutoff handling and GeoJSON."""

import json
import shutil
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas import (
    CommunitiesData,
    CommunityFeatureCollection,
    Envelope,
)


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


def _community_client(
    tmp_path: Path,
    synthetic_dir: Path,
    *,
    include_assignments: bool = True,
) -> TestClient:
    artifact_dir = (
        tmp_path / "artifacts"
    )

    shutil.copytree(
        synthetic_dir,
        artifact_dir,
    )

    communities = pd.DataFrame(
        [
            {
                "community_id": "C1",
                "community_name": "High Burden",
                "cutoff_year": 2013,
                "pipe_length_km": 10.0,
                "historical_break_count": 20,
                "historical_breaks_per_km": 2.0,
                "population": None,
                "equity_index": None,
                "equity_geography_status": "NOT_ASSESSED",
                "data_quality_flags": "[]",
            },
            {
                "community_id": "C2",
                "community_name": "Lower Burden",
                "cutoff_year": 2013,
                "pipe_length_km": 20.0,
                "historical_break_count": 10,
                "historical_breaks_per_km": 0.5,
                "population": None,
                "equity_index": None,
                "equity_geography_status": "NOT_ASSESSED",
                "data_quality_flags": (
                    '["SMALL_DENOMINATOR"]'
                ),
            },
            {
                "community_id": "C1",
                "community_name": "High Burden",
                "cutoff_year": 2022,
                "pipe_length_km": 12.0,
                "historical_break_count": 30,
                "historical_breaks_per_km": 2.5,
                "population": None,
                "equity_index": None,
                "equity_geography_status": "NOT_ASSESSED",
                "data_quality_flags": "[]",
            },
            {
                "community_id": "C2",
                "community_name": "Lower Burden",
                "cutoff_year": 2022,
                "pipe_length_km": 22.0,
                "historical_break_count": 12,
                "historical_breaks_per_km": (
                    0.5454545
                ),
                "population": None,
                "equity_index": None,
                "equity_geography_status": "NOT_ASSESSED",
                "data_quality_flags": "[]",
            },
        ]
    )

    communities.to_csv(
        artifact_dir
        / "communities.csv",
        index=False,
    )

    if include_assignments:
        plan = pd.read_parquet(
            artifact_dir
            / "plan_v2.parquet"
        )

        asset_ids = (
            plan[
                "asset_id"
            ]
            .astype(str)
            .head(3)
            .tolist()
        )

        assignments = pd.DataFrame(
            [
                {
                    "asset_id": asset_ids[0],
                    "community_id": "C1",
                    "overlap_length_m": 100.0,
                    "asset_length_m": 100.0,
                    "overlap_share": 1.0,
                },
                {
                    "asset_id": asset_ids[1],
                    "community_id": "C1",
                    "overlap_length_m": 50.0,
                    "asset_length_m": 100.0,
                    "overlap_share": 0.5,
                },
                {
                    "asset_id": asset_ids[1],
                    "community_id": "C2",
                    "overlap_length_m": 50.0,
                    "asset_length_m": 100.0,
                    "overlap_share": 0.5,
                },
                {
                    "asset_id": asset_ids[2],
                    "community_id": "C2",
                    "overlap_length_m": 100.0,
                    "asset_length_m": 100.0,
                    "overlap_share": 1.0,
                },
            ]
        )

        assignments.to_csv(
            artifact_dir
            / "asset_community_assignments.csv",
            index=False,
        )

    validation = pd.DataFrame(
        [
            {
                "origin_cutoff": 2013,
                "outcome_start_year": 2014,
                "outcome_end_year": 2016,
                "budget_pct": 10,
                "communities_evaluated": 2,
                "selected_community_count": 1,
                "selected_pipe_length_km": 10.0,
                "eligible_pipe_length_km": 30.0,
                "actual_network_share": (
                    1 / 3
                ),
                "future_break_events": 4,
                "future_break_events_assigned": 4,
                "future_break_events_unassigned": 0,
                "future_break_events_ambiguous": 0,
                "future_break_events_in_eligible_network": 4,
                "future_break_events_outside_eligible_network": 0,
                "selected_future_break_events": 3,
                "event_capture": 0.75,
                "lift_vs_network_share": 2.25,
                "notes": "test",
            }
        ],
        columns=COMMUNITY_VALIDATION_COLUMNS,
    )

    validation.to_csv(
        artifact_dir
        / "community_validation.csv",
        index=False,
    )

    for cutoff in (
        2013,
        2022,
    ):
        rows = communities.loc[
            communities[
                "cutoff_year"
            ]
            == cutoff
        ]

        features = []

        for index, row in (
            rows.reset_index(
                drop=True
            ).iterrows()
        ):
            x = (
                -114.10
                + index * 0.02
            )

            features.append(
                {
                    "type": "Feature",
                    "id": (
                        row[
                            "community_id"
                        ]
                    ),
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [
                                    x,
                                    51.00,
                                ],
                                [
                                    x + 0.01,
                                    51.00,
                                ],
                                [
                                    x + 0.01,
                                    51.01,
                                ],
                                [
                                    x,
                                    51.01,
                                ],
                                [
                                    x,
                                    51.00,
                                ],
                            ]
                        ],
                    },
                    "properties": {
                        "community_id": (
                            row[
                                "community_id"
                            ]
                        ),
                        "community_name": (
                            row[
                                "community_name"
                            ]
                        ),
                        "cutoff_year": cutoff,
                        "pipe_length_km": (
                            row[
                                "pipe_length_km"
                            ]
                        ),
                        "historical_break_count": (
                            row[
                                "historical_break_count"
                            ]
                        ),
                        "historical_breaks_per_km": (
                            row[
                                "historical_breaks_per_km"
                            ]
                        ),
                        "population": None,
                        "equity_index": None,
                        "equity_geography_status": (
                            "NOT_ASSESSED"
                        ),
                        "data_quality_flags": (
                            row[
                                "data_quality_flags"
                            ]
                        ),
                    },
                }
            )

        payload = {
            "type": "FeatureCollection",
            "features": features,
        }

        (
            artifact_dir
            / (
                f"communities_"
                f"{cutoff}.geojson"
            )
        ).write_text(
            json.dumps(
                payload
            ),
            encoding="utf-8",
        )

    return TestClient(
        create_app(
            artifact_dir
        )
    )


def test_missing_optional_community_artifacts_do_not_degrade_core(
    client,
):
    health = client.get(
        "/api/health"
    )

    assert (
        health.status_code
        == 200
    )

    assert (
        health.json()[
            "status"
        ]
        == "ok"
    )

    assets = client.get(
        "/api/assets"
    )

    assert (
        assets.status_code
        == 200
    )

    communities = client.get(
        "/api/communities"
    )

    assert (
        communities.status_code
        == 503
    )

    assert (
        communities.json()[
            "error"
        ][
            "code"
        ]
        == (
            "community_artifacts_unavailable"
        )
    )


def test_communities_defaults_to_latest_cutoff(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    response = client.get(
        "/api/communities"
    )

    assert (
        response.status_code
        == 200
    )

    envelope = Envelope[
        CommunitiesData
    ].model_validate(
        response.json()
    )

    assert (
        envelope.data.cutoff_year
        == 2022
    )

    assert (
        len(
            envelope.data.items
        )
        == 2
    )

    assert (
        envelope.data.items[
            0
        ].community_id
        == "C1"
    )


def test_communities_specific_cutoff(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    response = client.get(
        "/api/communities",
        params={
            "cutoff_year": 2013
        },
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()[
        "data"
    ]

    assert (
        data[
            "cutoff_year"
        ]
        == 2013
    )

    assert (
        len(
            data[
                "items"
            ]
        )
        == 2
    )

    assert (
        "cutoff_year"
        not in data[
            "items"
        ][0]
    )

    assert (
        data[
            "items"
        ][1][
            "data_quality_flags"
        ]
        == [
            "SMALL_DENOMINATOR"
        ]
    )


def test_unknown_cutoff_returns_404(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    response = client.get(
        "/api/communities",
        params={
            "cutoff_year": 1999
        },
    )

    assert (
        response.status_code
        == 404
    )

    assert (
        response.json()[
            "error"
        ][
            "code"
        ]
        == (
            "community_cutoff_not_found"
        )
    )


def test_community_geojson_defaults_to_latest_cutoff(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    response = client.get(
        "/api/communities/geojson"
    )

    assert (
        response.status_code
        == 200
    )

    envelope = Envelope[
        CommunityFeatureCollection
    ].model_validate(
        response.json()
    )

    assert (
        envelope.data.type
        == "FeatureCollection"
    )

    assert (
        len(
            envelope.data.features
        )
        == 2
    )

    assert all(
        feature.id
        == (
            feature.properties
            .community_id
        )
        for feature
        in envelope.data.features
    )


def test_community_geojson_specific_cutoff(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    response = client.get(
        "/api/communities/geojson",
        params={
            "cutoff_year": 2013
        },
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()[
        "data"
    ]

    flags_by_id = {
        feature[
            "properties"
        ][
            "community_id"
        ]: feature[
            "properties"
        ][
            "data_quality_flags"
        ]
        for feature
        in data[
            "features"
        ]
    }

    assert (
        flags_by_id[
            "C1"
        ]
        == []
    )

    assert (
        flags_by_id[
            "C2"
        ]
        == [
            "SMALL_DENOMINATOR"
        ]
    )

    assert (
        len(
            data[
                "features"
            ]
        )
        == 2
    )

    assert all(
        "cutoff_year"
        not in feature[
            "properties"
        ]
        for feature
        in data[
            "features"
        ]
    )


def test_asset_community_assignments_are_loaded(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    service = (
        client.app.state.community_artifacts
    )

    assert (
        service.loaded
        is True
    )

    assert (
        service.asset_assignments_loaded
        is True
    )

    assert (
        service.asset_assignment_errors
        == []
    )


def test_asset_ids_for_community_support_many_to_many_mapping(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    artifact_dir = (
        tmp_path
        / "artifacts"
    )

    plan = pd.read_parquet(
        artifact_dir
        / "plan_v2.parquet"
    )

    asset_ids = (
        plan[
            "asset_id"
        ]
        .astype(str)
        .head(3)
        .tolist()
    )

    service = (
        client.app.state.community_artifacts
    )

    assert (
        service.asset_ids_for_community(
            "C1"
        )
        == {
            asset_ids[0],
            asset_ids[1],
        }
    )

    assert (
        service.asset_ids_for_community(
            "C2"
        )
        == {
            asset_ids[1],
            asset_ids[2],
        }
    )


def test_assets_can_filter_by_community(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    plan = pd.read_parquet(
        tmp_path
        / "artifacts"
        / "plan_v2.parquet"
    )

    mapped_ids = (
        plan[
            "asset_id"
        ]
        .astype(str)
        .head(3)
        .tolist()
    )

    response = client.get(
        "/api/assets",
        params={
            "community_id": "C1",
        },
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()[
        "data"
    ]

    assert (
        data[
            "total"
        ]
        == 2
    )

    returned = {
        item[
            "asset_id"
        ]: item[
            "rank"
        ]
        for item
        in data[
            "items"
        ]
    }

    assert (
        set(
            returned
        )
        == {
            mapped_ids[0],
            mapped_ids[1],
        }
    )

    # Filtering must preserve the original global plan ranks.
    unfiltered = (
        client.get(
            "/api/assets"
        )
        .json()[
            "data"
        ][
            "items"
        ]
    )

    global_ranks = {
        item[
            "asset_id"
        ]: item[
            "rank"
        ]
        for item
        in unfiltered
    }

    assert (
        returned
        == {
            asset_id: global_ranks[
                asset_id
            ]
            for asset_id
            in returned
        }
    )


def test_cross_boundary_asset_appears_in_both_communities(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    plan = pd.read_parquet(
        tmp_path
        / "artifacts"
        / "plan_v2.parquet"
    )

    crossing_id = str(
        plan[
            "asset_id"
        ].iloc[
            1
        ]
    )

    c1 = (
        client.get(
            "/api/assets",
            params={
                "community_id": "C1",
            },
        )
        .json()[
            "data"
        ]
    )

    c2 = (
        client.get(
            "/api/assets",
            params={
                "community_id": "C2",
            },
        )
        .json()[
            "data"
        ]
    )

    assert (
        crossing_id
        in {
            item[
                "asset_id"
            ]
            for item
            in c1[
                "items"
            ]
        }
    )

    assert (
        crossing_id
        in {
            item[
                "asset_id"
            ]
            for item
            in c2[
                "items"
            ]
        }
    )


def test_assets_geojson_community_filter_matches_list(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    list_response = client.get(
        "/api/assets",
        params={
            "community_id": "C1",
            "selected_only": False,
        },
    )

    geojson_response = client.get(
        "/api/assets/geojson",
        params={
            "community_id": "C1",
            "selected_only": False,
        },
    )

    assert (
        list_response.status_code
        == 200
    )

    assert (
        geojson_response.status_code
        == 200
    )

    list_ids = {
        item[
            "asset_id"
        ]
        for item
        in list_response.json()[
            "data"
        ][
            "items"
        ]
    }

    geojson_ids = {
        feature[
            "properties"
        ][
            "asset_id"
        ]
        for feature
        in geojson_response.json()[
            "data"
        ][
            "features"
        ]
    }

    assert (
        geojson_ids
        == list_ids
    )


def test_assets_community_filter_respects_selected_only(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    all_rows = (
        client.get(
            "/api/assets",
            params={
                "community_id": "C1",
                "selected_only": False,
            },
        )
        .json()[
            "data"
        ]
    )

    selected_rows = (
        client.get(
            "/api/assets",
            params={
                "community_id": "C1",
                "selected_only": True,
            },
        )
        .json()[
            "data"
        ]
    )

    assert (
        selected_rows[
            "total"
        ]
        <= all_rows[
            "total"
        ]
    )

    assert all(
        item[
            "selected"
        ]
        for item
        in selected_rows[
            "items"
        ]
    )

    assert {
        item[
            "asset_id"
        ]
        for item
        in selected_rows[
            "items"
        ]
    }.issubset(
        {
            item[
                "asset_id"
            ]
            for item
            in all_rows[
                "items"
            ]
        }
    )


def test_unknown_community_asset_filter_returns_404(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
    )

    response = client.get(
        "/api/assets",
        params={
            "community_id": (
                "DOES_NOT_EXIST"
            ),
        },
    )

    assert (
        response.status_code
        == 404
    )

    assert (
        response.json()[
            "error"
        ][
            "code"
        ]
        == "community_not_found"
    )


def test_asset_filter_without_assignment_mapping_returns_503(
    tmp_path,
    synthetic_dir,
):
    client = _community_client(
        tmp_path,
        synthetic_dir,
        include_assignments=False,
    )

    # Community intelligence remains available.
    communities = client.get(
        "/api/communities"
    )

    assert (
        communities.status_code
        == 200
    )

    # Only the community-to-pipe bridge is unavailable.
    assets = client.get(
        "/api/assets",
        params={
            "community_id": "C1",
        },
    )

    assert (
        assets.status_code
        == 503
    )

    assert (
        assets.json()[
            "error"
        ][
            "code"
        ]
        == (
            "community_artifacts_unavailable"
        )
    )