"""Synthetic tests for cutoff-safe pipe evidence construction."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

from pipe_dreams_engine.evidence import (
    attach_future_outcomes,
    build_evidence_snapshot,
    recency_weights,
)
from pipe_dreams_engine.matching import associate_breaks

SYNTHETIC = True


def _pipes():
    return pd.DataFrame(
        {
            "asset_id": [
                "pipe_a",
                "pipe_b",
                "future_pipe",
            ],
            "install_year": [
                2000,
                1990,
                2021,
            ],
            "material": [
                "PVC",
                "CI",
                "PVC",
            ],
            "diameter": [
                200,
                300,
                250,
            ],
            "geometry": [
                LineString(
                    [(0.0, 0.0), (100.0, 0.0)]
                ),
                LineString(
                    [(0.0, 100.0), (100.0, 100.0)]
                ),
                LineString(
                    [(0.0, 300.0), (100.0, 300.0)]
                ),
            ],
        }
    )


def _breaks():
    return pd.DataFrame(
        {
            "break_year": [
                2010,
                2012,
                2021,
                2024,
            ],
            "geometry": [
                Point(50.0, 1.0),
                Point(50.0, 99.0),
                Point(60.0, 2.0),
                Point(70.0, 2.0),
            ],
        }
    )


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.pipes = _pipes()
        self.breaks = _breaks()
        self.associations = associate_breaks(
            self.breaks,
            self.pipes,
        )

    def test_synthetic_fixtures_are_flagged(self):
        self.assertTrue(SYNTHETIC)

    def test_recency_none_is_one(self):
        result = recency_weights(
            [2000, 2010, 2020],
            cutoff_year=2020,
            recency="none",
        )
        np.testing.assert_allclose(
            result,
            [1.0, 1.0, 1.0],
        )

    def test_recency_hl10_has_ten_year_half_life(self):
        result = recency_weights(
            [2000, 2010, 2020],
            cutoff_year=2020,
            recency="hl10",
        )
        np.testing.assert_allclose(
            result,
            [0.25, 0.5, 1.0],
        )

    def test_snapshot_excludes_pipes_installed_after_cutoff(self):
        snapshot = build_evidence_snapshot(
            self.pipes,
            self.breaks,
            self.associations,
            cutoff_year=2020,
        )

        self.assertEqual(
            set(snapshot["asset_id"]),
            {"pipe_a", "pipe_b"},
        )
        self.assertNotIn(
            "future_pipe",
            set(snapshot["asset_id"]),
        )

    def test_snapshot_uses_only_breaks_through_cutoff(self):
        snapshot = build_evidence_snapshot(
            self.pipes,
            self.breaks,
            self.associations,
            cutoff_year=2020,
        )

        row_a = snapshot.loc[
            snapshot["asset_id"] == "pipe_a"
        ].iloc[0]

        self.assertEqual(
            row_a["historical_break_count"],
            1,
        )

    def test_history_start_filters_old_events(self):
        snapshot = build_evidence_snapshot(
            self.pipes,
            self.breaks,
            self.associations,
            cutoff_year=2020,
            history_start_year=2011,
        )

        row_a = snapshot.loc[
            snapshot["asset_id"] == "pipe_a"
        ].iloc[0]
        row_b = snapshot.loc[
            snapshot["asset_id"] == "pipe_b"
        ].iloc[0]

        self.assertEqual(
            row_a["historical_break_count"],
            0,
        )
        self.assertEqual(
            row_b["historical_break_count"],
            1,
        )

    def test_neighbourhood_excludes_self_attributed_break(self):
        snapshot = build_evidence_snapshot(
            self.pipes,
            self.breaks,
            self.associations,
            cutoff_year=2020,
        )

        row_a = snapshot.loc[
            snapshot["asset_id"] == "pipe_a"
        ].iloc[0]

        # pipe_b's 2012 break is within 200 m of pipe_a,
        # while pipe_a's own 2010 attributed break is excluded.
        self.assertEqual(
            row_a["nearby_break_count_200m"],
            1,
        )

    def test_future_outcomes_are_separate_from_evidence(self):
        snapshot = build_evidence_snapshot(
            self.pipes,
            self.breaks,
            self.associations,
            cutoff_year=2020,
        )

        self.assertNotIn(
            "future_break_label",
            snapshot.columns,
        )
        self.assertNotIn(
            "future_break_events",
            snapshot.columns,
        )

        result = attach_future_outcomes(
            snapshot,
            self.pipes,
            self.breaks,
            self.associations,
            cutoff_year=2020,
            horizon_years=3,
        )

        row_a = result.loc[
            result["asset_id"] == "pipe_a"
        ].iloc[0]

        self.assertEqual(
            row_a["future_break_events"],
            1,
        )
        self.assertEqual(
            row_a["future_break_label"],
            1,
        )

    def test_outcomes_stop_at_horizon(self):
        snapshot = build_evidence_snapshot(
            self.pipes,
            self.breaks,
            self.associations,
            cutoff_year=2020,
        )

        result = attach_future_outcomes(
            snapshot,
            self.pipes,
            self.breaks,
            self.associations,
            cutoff_year=2020,
            horizon_years=3,
        )

        row_a = result.loc[
            result["asset_id"] == "pipe_a"
        ].iloc[0]

        # 2021 counts; 2024 is outside the 2021-2023 horizon.
        self.assertEqual(
            row_a["future_break_events"],
            1,
        )

    def test_nonsequential_indexes_preserve_attribution(self):
        pipes = self.pipes.copy()
        pipes.index = [101, 205, 309]

        breaks = self.breaks.copy()
        breaks.index = [11, 22, 33, 44]

        associations = associate_breaks(breaks, pipes)

        snapshot = build_evidence_snapshot(
            pipes,
            breaks,
            associations,
            cutoff_year=2020,
        )

        row_a = snapshot.loc[101]

        self.assertEqual(row_a["asset_id"], "pipe_a")
        self.assertEqual(row_a["historical_break_count"], 1)

        outcomes = attach_future_outcomes(
            snapshot,
            pipes,
            breaks,
            associations,
            cutoff_year=2020,
        )

        self.assertEqual(
            outcomes.loc[101, "future_break_events"],
            1,
        )

    def test_future_breaks_cannot_change_historical_evidence(self):
        original = build_evidence_snapshot(
            self.pipes,
            self.breaks,
            self.associations,
            cutoff_year=2020,
        )

        earlier_breaks = self.breaks[
            self.breaks["break_year"] <= 2020
        ].reset_index(drop=True)

        earlier_associations = associate_breaks(
            earlier_breaks,
            self.pipes,
        )

        historical_only = build_evidence_snapshot(
            self.pipes,
            earlier_breaks,
            earlier_associations,
            cutoff_year=2020,
        )

        columns = [
            "historical_break_count",
            "historical_break_weight",
            "nearby_break_count_200m",
            "nearby_break_weight_200m",
        ]

        pd.testing.assert_frame_equal(
            original[columns],
            historical_only[columns],
        )    


if __name__ == "__main__":
    unittest.main()