"""Synthetic tests for pipe-policy historical evaluation."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd
from shapely.geometry import LineString

from pipe_dreams_engine.evaluation import (
    VALIDATION_CUTOFFS,
    evaluate_policy_origin,
    origin_score_table,
    paired_spatial_bootstrap_improvement_se,
    pooled_validation_score,
    spatial_block_ids,
)
from pipe_dreams_engine.planner import (
    DEFAULT_BUDGET_SHARES,
    RANK_PER_ASSET,
)

SYNTHETIC = True


def _frame():
    rows = []

    # 20 equal-length assets = 1,000 m total.
    # Each asset is placed into a deterministic spatial location.
    for i in range(20):
        x = float(i * 600)

        rows.append(
            {
                "asset_id": f"pipe_{i:02d}",
                "length_m": 50.0,
                "future_break_label": (
                    1 if i in {0, 1, 2, 3, 4} else 0
                ),
                "future_break_events": (
                    2 if i == 0
                    else 1 if i in {1, 2, 3, 4}
                    else 0
                ),
                "geometry": LineString(
                    [
                        (x, 0.0),
                        (x + 40.0, 0.0),
                    ]
                ),
            }
        )

    return pd.DataFrame(
        rows,
        index=[
            100 + i * 3
            for i in range(20)
        ],
    )


def _good_scores(frame):
    values = []

    for i in range(len(frame)):
        values.append(
            1.0 - i / 100.0
        )

    return pd.Series(
        values,
        index=frame.index,
        name="score",
    )


def _bad_scores(frame):
    return pd.Series(
        np.linspace(
            0.0,
            1.0,
            len(frame),
        ),
        index=frame.index,
        name="score",
    )


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.frame = _frame()
        self.good = _good_scores(
            self.frame
        )
        self.bad = _bad_scores(
            self.frame
        )

    def test_synthetic_fixtures_are_flagged(self):
        self.assertTrue(SYNTHETIC)

    def test_spatial_blocks_are_deterministic(self):
        first = spatial_block_ids(
            self.frame
        )
        second = spatial_block_ids(
            self.frame
        )

        pd.testing.assert_series_equal(
            first,
            second,
        )

    def test_assets_in_same_km_cell_share_block(self):
        frame = pd.DataFrame(
            {
                "asset_id": [
                    "a",
                    "b",
                ],
                "length_m": [
                    10.0,
                    10.0,
                ],
                "future_break_label": [
                    0,
                    0,
                ],
                "future_break_events": [
                    0,
                    0,
                ],
                "geometry": [
                    LineString(
                        [
                            (100.0, 100.0),
                            (200.0, 100.0),
                        ]
                    ),
                    LineString(
                        [
                            (700.0, 100.0),
                            (800.0, 100.0),
                        ]
                    ),
                ],
            }
        )

        blocks = spatial_block_ids(
            frame
        )

        self.assertEqual(
            blocks.iloc[0],
            blocks.iloc[1],
        )

    def test_origin_uses_frozen_budget_set(self):
        result = evaluate_policy_origin(
            self.frame,
            self.good,
            cutoff_year=2013,
        )

        self.assertEqual(
            tuple(
                result.budget_results[
                    "budget_share"
                ]
            ),
            DEFAULT_BUDGET_SHARES,
        )

    def test_per_origin_score_is_mean_capture(self):
        result = evaluate_policy_origin(
            self.frame,
            self.good,
            cutoff_year=2013,
        )

        expected = float(
            result.budget_results[
                "breaking_asset_capture"
            ].mean()
        )

        self.assertAlmostEqual(
            result.per_origin_score,
            expected,
        )

    def test_good_ranking_captures_more_than_bad_ranking(self):
        good = evaluate_policy_origin(
            self.frame,
            self.good,
            cutoff_year=2013,
        )
        bad = evaluate_policy_origin(
            self.frame,
            self.bad,
            cutoff_year=2013,
        )

        self.assertGreater(
            good.per_origin_score,
            bad.per_origin_score,
        )

    def test_event_capture_is_reported_separately(self):
        result = evaluate_policy_origin(
            self.frame,
            self.good,
            cutoff_year=2013,
        )

        self.assertIn(
            "breaking_asset_capture",
            result.budget_results.columns,
        )
        self.assertIn(
            "event_capture",
            result.budget_results.columns,
        )

    def test_selection_series_align_to_original_index(self):
        result = evaluate_policy_origin(
            self.frame,
            self.good,
            cutoff_year=2013,
        )

        for selected in result.selections.values():
            self.assertEqual(
                list(selected.index),
                list(self.frame.index),
            )

    def test_origin_rejects_inconsistent_label_and_events(self):
        frame = self.frame.copy()

        idx = frame.index[0]
        frame.loc[
            idx,
            "future_break_label",
        ] = 0

        with self.assertRaises(
            ValueError
        ):
            evaluate_policy_origin(
                frame,
                self.good,
                cutoff_year=2013,
            )

    def test_origin_rejects_no_positive_assets(self):
        frame = self.frame.copy()
        frame[
            "future_break_label"
        ] = 0
        frame[
            "future_break_events"
        ] = 0

        with self.assertRaises(
            ValueError
        ):
            evaluate_policy_origin(
                frame,
                self.good,
                cutoff_year=2013,
            )

    def test_pooled_score_uses_three_frozen_origins(self):
        origins = [
            evaluate_policy_origin(
                self.frame,
                self.good,
                cutoff_year=cutoff,
            )
            for cutoff in VALIDATION_CUTOFFS
        ]

        pooled = pooled_validation_score(
            origins
        )

        expected = np.mean(
            [
                result.per_origin_score
                for result in origins
            ]
        )

        self.assertAlmostEqual(
            pooled,
            expected,
        )

    def test_pooled_score_requires_all_frozen_origins(self):
        origins = [
            evaluate_policy_origin(
                self.frame,
                self.good,
                cutoff_year=2013,
            ),
            evaluate_policy_origin(
                self.frame,
                self.good,
                cutoff_year=2016,
            ),
        ]

        with self.assertRaises(
            ValueError
        ):
            pooled_validation_score(
                origins
            )

    def test_origin_score_table_is_sorted(self):
        origins = [
            evaluate_policy_origin(
                self.frame,
                self.good,
                cutoff_year=2019,
            ),
            evaluate_policy_origin(
                self.frame,
                self.good,
                cutoff_year=2013,
            ),
            evaluate_policy_origin(
                self.frame,
                self.good,
                cutoff_year=2016,
            ),
        ]

        table = origin_score_table(
            origins
        )

        self.assertEqual(
            table["cutoff_year"].to_list(),
            [2013, 2016, 2019],
        )

    def test_bootstrap_identical_policy_has_zero_se_and_improvement(
        self,
    ):
        origins = [
            evaluate_policy_origin(
                self.frame,
                self.good,
                cutoff_year=cutoff,
            )
            for cutoff in VALIDATION_CUTOFFS
        ]

        result = (
            paired_spatial_bootstrap_improvement_se(
                origins,
                origins,
                reps=100,
                seed=7,
            )
        )

        self.assertAlmostEqual(
            result.mean_bootstrap_improvement,
            0.0,
        )
        self.assertAlmostEqual(
            result.standard_error,
            0.0,
        )
        self.assertEqual(
            result.reps_used,
            100,
        )

    def test_bootstrap_is_reproducible(self):
        v1 = [
            evaluate_policy_origin(
                self.frame,
                self.bad,
                cutoff_year=cutoff,
            )
            for cutoff in VALIDATION_CUTOFFS
        ]

        candidate = [
            evaluate_policy_origin(
                self.frame,
                self.good,
                cutoff_year=cutoff,
            )
            for cutoff in VALIDATION_CUTOFFS
        ]

        first = (
            paired_spatial_bootstrap_improvement_se(
                v1,
                candidate,
                reps=100,
                seed=42,
            )
        )

        second = (
            paired_spatial_bootstrap_improvement_se(
                v1,
                candidate,
                reps=100,
                seed=42,
            )
        )

        self.assertAlmostEqual(
            first.standard_error,
            second.standard_error,
        )
        self.assertAlmostEqual(
            first.mean_bootstrap_improvement,
            second.mean_bootstrap_improvement,
        )

    def test_bootstrap_candidate_improvement_is_positive(
        self,
    ):
        v1 = [
            evaluate_policy_origin(
                self.frame,
                self.bad,
                cutoff_year=cutoff,
            )
            for cutoff in VALIDATION_CUTOFFS
        ]

        candidate = [
            evaluate_policy_origin(
                self.frame,
                self.good,
                cutoff_year=cutoff,
            )
            for cutoff in VALIDATION_CUTOFFS
        ]

        result = (
            paired_spatial_bootstrap_improvement_se(
                v1,
                candidate,
                reps=200,
                seed=1,
            )
        )

        self.assertGreater(
            result.mean_bootstrap_improvement,
            0.0,
        )
        self.assertGreaterEqual(
            result.standard_error,
            0.0,
        )


if __name__ == "__main__":
    unittest.main()