import unittest

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon

from pipe_dreams_engine.community_validation import (
    CommunityValidationOrigin,
    evaluate_community_origin,
    evaluate_rolling_community_origins,
)


CRS = "EPSG:3776"


def make_validation_inputs():
    communities = gpd.GeoDataFrame(
        {
            "community_id": [
                "C1",
                "C2",
                "C3",
            ],
            "community_name": [
                "High History",
                "Medium History",
                "Low History",
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
            Polygon(
                [
                    (2000, 0),
                    (3000, 0),
                    (3000, 1000),
                    (2000, 1000),
                    (2000, 0),
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
            LineString(
                [
                    (2000, 100),
                    (3000, 100),
                ]
            ),
        ],
        crs=CRS,
    )

    break_years = [
        # Historical through 2013:
        2010,
        2011,
        2012,
        2013,
        2011,
        2012,
        2013,
        # Future 2014-2016:
        2014,
        2015,
        2016,
        2014,
        # Later events:
        2017,
        2018,
        2020,
        2021,
    ]

    break_points = [
        # C1 historical: 4
        Point(100, 200),
        Point(200, 200),
        Point(300, 200),
        Point(400, 200),

        # C2 historical: 2
        Point(1100, 200),
        Point(1200, 200),

        # C3 historical: 1
        Point(2100, 200),

        # 2014-2016 future:
        # C1 gets 3
        Point(500, 300),
        Point(600, 300),
        Point(700, 300),

        # C2 gets 1
        Point(1300, 300),

        # Later windows:
        Point(1400, 400),
        Point(1500, 400),
        Point(2200, 400),
        Point(2300, 400),
    ]

    breaks = gpd.GeoDataFrame(
        {
            "break_year": break_years,
        },
        geometry=break_points,
        crs=CRS,
    )

    return communities, pipes, breaks


class CommunityOriginValidationTests(
    unittest.TestCase
):
    def test_top_ranked_community_captures_future_events(self):
        communities, pipes, breaks = (
            make_validation_inputs()
        )

        result = evaluate_community_origin(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            origin=CommunityValidationOrigin(
                cutoff_year=2013,
                outcome_start_year=2014,
                outcome_end_year=2016,
            ),
            top_n=1,
        )

        self.assertEqual(
            result["communities_evaluated"],
            3,
        )

        self.assertEqual(
            result["future_break_events"],
            4,
        )

        self.assertEqual(
            result[
                "future_break_events_assigned"
            ],
            4,
        )

        self.assertEqual(
            result[
                "top_community_future_break_events"
            ],
            3,
        )

        self.assertAlmostEqual(
            result[
                "top_community_event_capture"
            ],
            0.75,
            places=6,
        )

    def test_future_events_do_not_affect_historical_ranking(self):
        communities, pipes, breaks = (
            make_validation_inputs()
        )

        extra_future = gpd.GeoDataFrame(
            {
                "break_year": [
                    2014,
                    2015,
                    2016,
                    2016,
                    2016,
                ]
            },
            geometry=[
                Point(2100, 500),
                Point(2200, 500),
                Point(2300, 500),
                Point(2400, 500),
                Point(2500, 500),
            ],
            crs=CRS,
        )

        breaks = gpd.GeoDataFrame(
            gpd.pd.concat(
                [
                    breaks,
                    extra_future,
                ],
                ignore_index=True,
            ),
            geometry="geometry",
            crs=CRS,
        )

        result = evaluate_community_origin(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            origin=CommunityValidationOrigin(
                cutoff_year=2013,
                outcome_start_year=2014,
                outcome_end_year=2016,
            ),
            top_n=1,
        )

        # C1 remains the historical top-ranked community even
        # though C3 receives many future events.
        self.assertEqual(
            result[
                "top_community_future_break_events"
            ],
            3,
        )

        self.assertEqual(
            result["future_break_events"],
            9,
        )

    def test_outside_future_break_is_reported_not_silently_dropped(self):
        communities, pipes, breaks = (
            make_validation_inputs()
        )

        outside = gpd.GeoDataFrame(
            {
                "break_year": [2015],
            },
            geometry=[
                Point(5000, 5000),
            ],
            crs=CRS,
        )

        breaks = gpd.GeoDataFrame(
            gpd.pd.concat(
                [
                    breaks,
                    outside,
                ],
                ignore_index=True,
            ),
            geometry="geometry",
            crs=CRS,
        )

        result = evaluate_community_origin(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            origin=CommunityValidationOrigin(
                cutoff_year=2013,
                outcome_start_year=2014,
                outcome_end_year=2016,
            ),
            top_n=1,
        )

        self.assertEqual(
            result["future_break_events"],
            5,
        )

        self.assertEqual(
            result[
                "future_break_events_assigned"
            ],
            4,
        )

        self.assertEqual(
            result[
                "future_break_events_unassigned"
            ],
            1,
        )

        self.assertAlmostEqual(
            result[
                "top_community_event_capture"
            ],
            0.75,
            places=6,
        )

    def test_rejects_invalid_top_n(self):
        communities, pipes, breaks = (
            make_validation_inputs()
        )

        with self.assertRaisesRegex(
            ValueError,
            "top_n must be greater than zero",
        ):
            evaluate_community_origin(
                communities=communities,
                pipes=pipes,
                breaks=breaks,
                origin=CommunityValidationOrigin(
                    cutoff_year=2013,
                    outcome_start_year=2014,
                    outcome_end_year=2016,
                ),
                top_n=0,
            )

    def test_rejects_outcome_window_before_cutoff(self):
        communities, pipes, breaks = (
            make_validation_inputs()
        )

        with self.assertRaisesRegex(
            ValueError,
            "outcome_start_year must be after cutoff_year",
        ):
            evaluate_community_origin(
                communities=communities,
                pipes=pipes,
                breaks=breaks,
                origin=CommunityValidationOrigin(
                    cutoff_year=2013,
                    outcome_start_year=2013,
                    outcome_end_year=2016,
                ),
                top_n=1,
            )


class CommunityRollingValidationTests(
    unittest.TestCase
):
    def test_returns_one_row_per_origin(self):
        communities, pipes, breaks = (
            make_validation_inputs()
        )

        origins = (
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
        )

        result = evaluate_rolling_community_origins(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            origins=origins,
            top_n=1,
        )

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[
                "origin_cutoff"
            ].tolist(),
            [
                2013,
                2016,
            ],
        )

    def test_default_result_columns_match_artifact_needs(self):
        communities, pipes, breaks = (
            make_validation_inputs()
        )

        origins = (
            CommunityValidationOrigin(
                cutoff_year=2013,
                outcome_start_year=2014,
                outcome_end_year=2016,
            ),
        )

        result = evaluate_rolling_community_origins(
            communities=communities,
            pipes=pipes,
            breaks=breaks,
            origins=origins,
            top_n=1,
        )

        expected = {
            "origin_cutoff",
            "outcome_start_year",
            "outcome_end_year",
            "communities_evaluated",
            "future_break_events",
            "future_break_events_assigned",
            "future_break_events_unassigned",
            "future_break_events_ambiguous",
            "top_community_count",
            "top_community_future_break_events",
            "top_community_event_capture",
            "notes",
        }

        self.assertEqual(
            set(result.columns),
            expected,
        )


if __name__ == "__main__":
    unittest.main()