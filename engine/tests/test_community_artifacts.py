import json
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point, Polygon

from pipe_dreams_engine.community_artifacts import (
    COMMUNITY_CSV_COLUMNS,
    COMMUNITY_VALIDATION_COLUMNS,
    write_community_artifacts,
)
from pipe_dreams_engine.community_validation import (
    CommunityValidationOrigin,
)


CRS = "EPSG:3776"


def make_artifact_inputs():
    communities = gpd.GeoDataFrame(
        {
            "community_id": [
                "C1",
                "C2",
            ],
            "community_name": [
                "West",
                "East",
            ],
        },
        geometry=[
            Polygon(
                [
                    (0, 0),
                    (1000, 0),
                    (1000, 1000),
                    (0, 1000),
                    (0, 0),
                ]
            ),
            Polygon(
                [
                    (1000, 0),
                    (2000, 0),
                    (2000, 1000),
                    (1000, 1000),
                    (1000, 0),
                ]
            ),
        ],
        crs=CRS,
    )

    pipes = gpd.GeoDataFrame(
        {
            "install_year": [
                2000,
                2000,
            ],
        },
        geometry=[
            LineString(
                [
                    (0, 100),
                    (1000, 100),
                ]
            ),
            LineString(
                [
                    (1000, 100),
                    (2000, 100),
                ]
            ),
        ],
        crs=CRS,
    )

    breaks = gpd.GeoDataFrame(
        {
            "break_year": [
                2010,
                2011,
                2014,
                2015,
            ],
        },
        geometry=[
            Point(100, 200),
            Point(200, 200),
            Point(300, 300),
            Point(1300, 300),
        ],
        crs=CRS,
    )

    return communities, pipes, breaks


class CommunityArtifactTests(
    unittest.TestCase
):
    def test_writes_expected_artifact_files(self):
        communities, pipes, breaks = (
            make_artifact_inputs()
        )

        with tempfile.TemporaryDirectory() as tmp:
            paths = write_community_artifacts(
                communities=communities,
                pipes=pipes,
                breaks=breaks,
                output_dir=tmp,
                cutoffs=(2013, 2016),
                validation_origins=(
                    CommunityValidationOrigin(
                        cutoff_year=2013,
                        outcome_start_year=2014,
                        outcome_end_year=2016,
                    ),
                ),
                validation_budgets_pct=(10,),
            )

            self.assertTrue(
                Path(
                    paths["communities_csv"]
                ).exists()
            )

            self.assertTrue(
                Path(
                    paths[
                        "community_validation_csv"
                    ]
                ).exists()
            )

            self.assertTrue(
                Path(
                    paths[
                        "communities_2013_geojson"
                    ]
                ).exists()
            )

            self.assertTrue(
                Path(
                    paths[
                        "communities_2016_geojson"
                    ]
                ).exists()
            )

    def test_communities_csv_matches_frozen_schema(self):
        communities, pipes, breaks = (
            make_artifact_inputs()
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_community_artifacts(
                communities=communities,
                pipes=pipes,
                breaks=breaks,
                output_dir=tmp,
                cutoffs=(2013,),
                validation_origins=(
                    CommunityValidationOrigin(
                        cutoff_year=2013,
                        outcome_start_year=2014,
                        outcome_end_year=2016,
                    ),
                ),
                validation_budgets_pct=(10,),
            )

            result = pd.read_csv(
                Path(tmp)
                / "communities.csv"
            )

            self.assertEqual(
                result.columns.tolist(),
                COMMUNITY_CSV_COLUMNS,
            )

            self.assertEqual(
                len(result),
                2,
            )

            self.assertEqual(
                result[
                    "equity_geography_status"
                ].unique().tolist(),
                ["NOT_ASSESSED"],
            )

    def test_flags_are_json_encoded_in_csv(self):
        communities, pipes, breaks = (
            make_artifact_inputs()
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_community_artifacts(
                communities=communities,
                pipes=pipes,
                breaks=breaks,
                output_dir=tmp,
                cutoffs=(2013,),
                validation_origins=(
                    CommunityValidationOrigin(
                        cutoff_year=2013,
                        outcome_start_year=2014,
                        outcome_end_year=2016,
                    ),
                ),
                validation_budgets_pct=(10,),
            )

            result = pd.read_csv(
                Path(tmp)
                / "communities.csv"
            )

            decoded = json.loads(
                result.loc[
                    0,
                    "data_quality_flags",
                ]
            )

            self.assertIsInstance(
                decoded,
                list,
            )

    def test_geojson_is_wgs84_and_contains_properties(self):
        communities, pipes, breaks = (
            make_artifact_inputs()
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_community_artifacts(
                communities=communities,
                pipes=pipes,
                breaks=breaks,
                output_dir=tmp,
                cutoffs=(2013,),
                validation_origins=(
                    CommunityValidationOrigin(
                        cutoff_year=2013,
                        outcome_start_year=2014,
                        outcome_end_year=2016,
                    ),
                ),
                validation_budgets_pct=(10,),
            )

            result = gpd.read_file(
                Path(tmp)
                / "communities_2013.geojson"
            )

            self.assertEqual(
                result.crs.to_epsg(),
                4326,
            )

            self.assertIn(
                "historical_breaks_per_km",
                result.columns,
            )

            self.assertIn(
                "pipe_length_km",
                result.columns,
            )

    def test_validation_csv_matches_frozen_schema(self):
        communities, pipes, breaks = (
            make_artifact_inputs()
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_community_artifacts(
                communities=communities,
                pipes=pipes,
                breaks=breaks,
                output_dir=tmp,
                cutoffs=(2013,),
                validation_origins=(
                    CommunityValidationOrigin(
                        cutoff_year=2013,
                        outcome_start_year=2014,
                        outcome_end_year=2016,
                    ),
                ),
                validation_budgets_pct=(10,),
            )

            result = pd.read_csv(
                Path(tmp)
                / "community_validation.csv"
            )

            self.assertEqual(
                result.columns.tolist(),
                COMMUNITY_VALIDATION_COLUMNS,
            )

            self.assertEqual(
                len(result),
                1,
            )

            self.assertEqual(
                result.loc[
                    0,
                    "origin_cutoff",
                ],
                2013,
            )

            self.assertEqual(
                result.loc[
                    0,
                    "budget_pct",
                ],
                10.0,
            )

            self.assertIn(
                "actual_network_share",
                result.columns,
            )

            self.assertIn(
                "event_capture",
                result.columns,
            )

            self.assertIn(
                "lift_vs_network_share",
                result.columns,
            )


if __name__ == "__main__":
    unittest.main()