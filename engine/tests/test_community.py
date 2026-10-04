import unittest

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon

from pipe_dreams_engine.community import build_community_metrics


CRS = "EPSG:3776"


def make_valid_inputs():
    communities = gpd.GeoDataFrame(
        {
            "community_id": ["C1"],
            "community_name": ["Test Community"],
        },
        geometry=[
            Polygon(
                [
                    (0, 0),
                    (100, 0),
                    (100, 100),
                    (0, 100),
                    (0, 0),
                ]
            )
        ],
        crs=CRS,
    )

    pipes = gpd.GeoDataFrame(
        {
            "install_year": [2000],
        },
        geometry=[
            LineString(
                [
                    (10, 10),
                    (90, 10),
                ]
            )
        ],
        crs=CRS,
    )

    breaks = gpd.GeoDataFrame(
        {
            "break_year": [2010],
        },
        geometry=[
            Point(50, 10),
        ],
        crs=CRS,
    )

    return communities, pipes, breaks


class CommunityValidationTests(unittest.TestCase):
    def test_rejects_non_integer_cutoff_year(self):
        communities, pipes, breaks = make_valid_inputs()

        with self.assertRaisesRegex(
            TypeError,
            "cutoff_year must be an integer",
        ):
            build_community_metrics(
                communities=communities,
                pipes=pipes,
                breaks=breaks,
                cutoff_year="2022",
            )

    def test_rejects_missing_required_column(self):
        communities, pipes, breaks = make_valid_inputs()
        pipes = pipes.drop(columns=["install_year"])

        with self.assertRaisesRegex(
            ValueError,
            "pipes missing required columns: install_year",
        ):
            build_community_metrics(
                communities=communities,
                pipes=pipes,
                breaks=breaks,
                cutoff_year=2022,
            )

    def test_rejects_missing_crs(self):
        communities, pipes, breaks = make_valid_inputs()
        breaks = breaks.set_crs(None, allow_override=True)

        with self.assertRaisesRegex(
            ValueError,
            "breaks must have a defined CRS",
        ):
            build_community_metrics(
                communities=communities,
                pipes=pipes,
                breaks=breaks,
                cutoff_year=2022,
            )

    def test_rejects_missing_geometry(self):
        communities, pipes, breaks = make_valid_inputs()
        breaks.loc[0, "geometry"] = None

        with self.assertRaisesRegex(
            ValueError,
            "breaks contains missing geometry",
        ):
            build_community_metrics(
                communities=communities,
                pipes=pipes,
                breaks=breaks,
                cutoff_year=2022,
            )


class CommunityPipeLengthTests(unittest.TestCase):
    def test_calculates_pipe_length_inside_community(self):
        communities, pipes, breaks = make_valid_inputs()

        result = build_community_metrics(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            cutoff_year=2022,
        )

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(
            result.loc[0, "pipe_length_km"],
            0.08,
            places=6,
        )

    def test_excludes_pipe_installed_after_cutoff(self):
        communities, pipes, breaks = make_valid_inputs()
        pipes.loc[0, "install_year"] = 2025

        result = build_community_metrics(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            cutoff_year=2022,
        )

        self.assertEqual(
            result.loc[0, "pipe_length_km"],
            0.0,
        )

    def test_clips_pipe_crossing_community_boundary(self):
        communities, pipes, breaks = make_valid_inputs()

        pipes = gpd.GeoDataFrame(
            {
                "install_year": [2000],
            },
            geometry=[
                LineString(
                    [
                        (-50, 50),
                        (150, 50),
                    ]
                )
            ],
            crs=CRS,
        )

        result = build_community_metrics(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            cutoff_year=2022,
        )

        self.assertAlmostEqual(
            result.loc[0, "pipe_length_km"],
            0.1,
            places=6,
        )

    def test_pipe_crossing_two_communities_is_split_correctly(self):
        communities = gpd.GeoDataFrame(
            {
                "community_id": ["C1", "C2"],
                "community_name": ["West", "East"],
            },
            geometry=[
                Polygon(
                    [
                        (0, 0),
                        (100, 0),
                        (100, 100),
                        (0, 100),
                        (0, 0),
                    ]
                ),
                Polygon(
                    [
                        (100, 0),
                        (200, 0),
                        (200, 100),
                        (100, 100),
                        (100, 0),
                    ]
                ),
            ],
            crs=CRS,
        )

        pipes = gpd.GeoDataFrame(
            {
                "install_year": [2000],
            },
            geometry=[
                LineString(
                    [
                        (50, 50),
                        (150, 50),
                    ]
                )
            ],
            crs=CRS,
        )

        breaks = gpd.GeoDataFrame(
            {
                "break_year": [2010],
            },
            geometry=[
                Point(50, 50),
            ],
            crs=CRS,
        )

        result = build_community_metrics(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            cutoff_year=2022,
        ).set_index("community_id")

        self.assertAlmostEqual(
            result.loc["C1", "pipe_length_km"],
            0.05,
            places=6,
        )

        self.assertAlmostEqual(
            result.loc["C2", "pipe_length_km"],
            0.05,
            places=6,
        )


class CommunityBreakMetricTests(unittest.TestCase):
    def test_counts_historical_break_inside_community(self):
        communities, pipes, breaks = make_valid_inputs()

        result = build_community_metrics(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            cutoff_year=2022,
        )

        self.assertEqual(
            result.loc[0, "historical_break_count"],
            1,
        )

    def test_excludes_break_after_cutoff(self):
        communities, pipes, breaks = make_valid_inputs()
        breaks.loc[0, "break_year"] = 2025

        result = build_community_metrics(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            cutoff_year=2022,
        )

        self.assertEqual(
            result.loc[0, "historical_break_count"],
            0,
        )

    def test_break_outside_all_communities_is_not_counted(self):
        communities, pipes, breaks = make_valid_inputs()
        breaks.loc[0, "geometry"] = Point(500, 500)

        result = build_community_metrics(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            cutoff_year=2022,
        )

        self.assertEqual(
            result.loc[0, "historical_break_count"],
            0,
        )

    def test_calculates_historical_breaks_per_km(self):
        communities, pipes, breaks = make_valid_inputs()

        result = build_community_metrics(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            cutoff_year=2022,
        )

        self.assertAlmostEqual(
            result.loc[0, "historical_breaks_per_km"],
            12.5,
            places=6,
        )

    def test_breaks_per_km_is_missing_when_pipe_length_is_zero(self):
        communities, pipes, breaks = make_valid_inputs()
        pipes.loc[0, "install_year"] = 2025

        result = build_community_metrics(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            cutoff_year=2022,
        )

        self.assertTrue(
            result.loc[0, "historical_breaks_per_km"]
            is None
            or gpd.pd.isna(
                result.loc[0, "historical_breaks_per_km"]
            )
        )

    def test_break_on_shared_boundary_is_not_double_counted(self):
        communities = gpd.GeoDataFrame(
            {
                "community_id": ["C1", "C2"],
                "community_name": ["West", "East"],
            },
            geometry=[
                Polygon(
                    [
                        (0, 0),
                        (100, 0),
                        (100, 100),
                        (0, 100),
                        (0, 0),
                    ]
                ),
                Polygon(
                    [
                        (100, 0),
                        (200, 0),
                        (200, 100),
                        (100, 100),
                        (100, 0),
                    ]
                ),
            ],
            crs=CRS,
        )

        pipes = gpd.GeoDataFrame(
            {
                "install_year": [2000],
            },
            geometry=[
                LineString(
                    [
                        (0, 50),
                        (200, 50),
                    ]
                )
            ],
            crs=CRS,
        )

        breaks = gpd.GeoDataFrame(
            {
                "break_year": [2010],
            },
            geometry=[
                Point(100, 50),
            ],
            crs=CRS,
        )

        result = build_community_metrics(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            cutoff_year=2022,
        )

        self.assertEqual(
            result["historical_break_count"].sum(),
            0,
        )


if __name__ == "__main__":
    unittest.main()