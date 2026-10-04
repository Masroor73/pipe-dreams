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

    # Eligible network totals 1.0 km:
    # C1 = 0.1 km, C2 = 0.4 km, C3 = 0.5 km.
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
                    (100, 100),
                    (200, 100),
                ]
            ),
            LineString(
                [
                    (1100, 100),
                    (1500, 100),
                ]
            ),
            LineString(
                [
                    (2100, 100),
                    (2600, 100),
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
    def test_network_budget_captures_future_events(self):
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
            budget_pct=10,
        )

        self.assertEqual(
            result["communities_evaluated"],
            3,
        )

        self.assertEqual(
            result["selected_community_count"],
            1,
        )

        self.assertAlmostEqual(
            result["selected_pipe_length_km"],
            0.1,
            places=6,
        )

        self.assertAlmostEqual(
            result["eligible_pipe_length_km"],
            1.0,
            places=6,
        )

        self.assertAlmostEqual(
            result["actual_network_share"],
            0.10,
            places=6,
        )

        self.assertEqual(
            result["future_break_events"],
            4,
        )

        self.assertEqual(
            result["future_break_events_assigned"],
            4,
        )

        self.assertEqual(
            result[
                "future_break_events_in_eligible_network"
            ],
            4,
        )

        self.assertEqual(
            result["selected_future_break_events"],
            3,
        )

        self.assertAlmostEqual(
            result["event_capture"],
            0.75,
            places=6,
        )

        self.assertAlmostEqual(
            result["lift_vs_network_share"],
            7.5,
            places=6,
        )

    def test_whole_community_selection_reports_budget_overshoot(
        self,
    ):
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
            budget_pct=25,
        )

        # C1 contributes 10% of network. Adding C2 raises the
        # realized share to 50%, which is explicitly reported.
        self.assertEqual(
            result["selected_community_count"],
            2,
        )

        self.assertAlmostEqual(
            result["actual_network_share"],
            0.50,
            places=6,
        )

        self.assertGreater(
            result["actual_network_share"],
            result["budget_pct"] / 100.0,
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
            budget_pct=10,
        )

        # C1 remains selected from historical evidence even though
        # C3 receives many future events.
        self.assertEqual(
            result["selected_future_break_events"],
            3,
        )

        self.assertEqual(
            result["future_break_events"],
            9,
        )

    def test_outside_future_break_is_reported_not_silently_dropped(
        self,
    ):
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
            budget_pct=10,
        )

        self.assertEqual(
            result["future_break_events"],
            5,
        )

        self.assertEqual(
            result["future_break_events_assigned"],
            4,
        )

        self.assertEqual(
            result["future_break_events_unassigned"],
            1,
        )

        self.assertAlmostEqual(
            result["event_capture"],
            0.75,
            places=6,
        )

    def test_future_events_outside_eligible_network_are_reported(
        self,
    ):
        communities, pipes, breaks = (
            make_validation_inputs()
        )

        pipes = pipes.loc[
            pipes.index != 2
        ].reset_index(drop=True)

        extra_future = gpd.GeoDataFrame(
            {
                "break_year": [2015],
            },
            geometry=[
                Point(2200, 500),
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
            budget_pct=20,
        )

        self.assertEqual(
            result[
                "future_break_events_outside_eligible_network"
            ],
            1,
        )

        self.assertEqual(
            result[
                "future_break_events_in_eligible_network"
            ],
            4,
        )

    def test_rejects_invalid_budget(self):
        communities, pipes, breaks = (
            make_validation_inputs()
        )

        with self.assertRaisesRegex(
            ValueError,
            "budget_pct must be greater than zero and at most 100",
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
                budget_pct=0,
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
                budget_pct=10,
            )


class CommunityRollingValidationTests(
    unittest.TestCase
):
    def test_returns_one_row_per_origin_and_budget(self):
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
            budgets_pct=(10, 20),
        )

        self.assertEqual(
            len(result),
            4,
        )

        self.assertEqual(
            result["origin_cutoff"].tolist(),
            [
                2013,
                2013,
                2016,
                2016,
            ],
        )

        self.assertEqual(
            result["budget_pct"].tolist(),
            [
                10.0,
                20.0,
                10.0,
                20.0,
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
            budgets_pct=(10,),
        )

        expected = {
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
        }

        self.assertEqual(
            set(result.columns),
            expected,
        )


if __name__ == "__main__":
    unittest.main()