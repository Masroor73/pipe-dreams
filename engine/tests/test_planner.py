"""Synthetic tests for capacity-constrained pipe planning."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from pipe_dreams_engine.planner import (
    DEFAULT_BUDGET_SHARES,
    RANK_PER_ASSET,
    RANK_PER_METRE,
    build_capacity_plan,
    build_multi_budget_plans,
    rank_assets,
    ranking_key,
)

SYNTHETIC = True


def _frame():
    return pd.DataFrame(
        {
            "asset_id": [
                "pipe_a",
                "pipe_b",
                "pipe_c",
                "pipe_d",
            ],
            "length_m": [
                100.0,
                10.0,
                50.0,
                40.0,
            ],
        },
        index=[
            101,
            205,
            309,
            401,
        ],
    )


def _scores(frame):
    return pd.Series(
        [
            0.90,
            0.80,
            0.70,
            0.60,
        ],
        index=frame.index,
        name="likelihood_score",
    )


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.frame = _frame()
        self.scores = _scores(
            self.frame
        )

    def test_synthetic_fixtures_are_flagged(self):
        self.assertTrue(SYNTHETIC)

    def test_per_asset_key_is_raw_score(self):
        key = ranking_key(
            self.frame,
            self.scores,
            ranking_mode=RANK_PER_ASSET,
        )

        np.testing.assert_allclose(
            key.to_numpy(),
            self.scores.to_numpy(),
        )

    def test_per_metre_key_divides_by_length(self):
        key = ranking_key(
            self.frame,
            self.scores,
            ranking_mode=RANK_PER_METRE,
        )

        expected = (
            self.scores.to_numpy()
            / self.frame[
                "length_m"
            ].to_numpy()
        )

        np.testing.assert_allclose(
            key.to_numpy(),
            expected,
        )

    def test_per_asset_and_per_metre_can_rank_differently(
        self,
    ):
        per_asset = rank_assets(
            self.frame,
            self.scores,
            ranking_mode=RANK_PER_ASSET,
        )
        per_metre = rank_assets(
            self.frame,
            self.scores,
            ranking_mode=RANK_PER_METRE,
        )

        self.assertEqual(
            per_asset.iloc[0]["asset_id"],
            "pipe_a",
        )
        self.assertEqual(
            per_metre.iloc[0]["asset_id"],
            "pipe_b",
        )

    def test_ranking_preserves_original_indexes(self):
        ranked = rank_assets(
            self.frame,
            self.scores,
        )

        self.assertEqual(
            set(ranked.index),
            set(self.frame.index),
        )

    def test_ties_are_resolved_by_asset_id(
        self,
    ):
        frame = pd.DataFrame(
            {
                "asset_id": [
                    "z_pipe",
                    "a_pipe",
                ],
                "length_m": [
                    50.0,
                    50.0,
                ],
            },
            index=[
                11,
                22,
            ],
        )

        scores = pd.Series(
            [0.5, 0.5],
            index=frame.index,
        )

        ranked = rank_assets(
            frame,
            scores,
        )

        self.assertEqual(
            list(ranked["asset_id"]),
            [
                "a_pipe",
                "z_pipe",
            ],
        )

    def test_capacity_plan_never_exceeds_budget(
        self,
    ):
        plan, summary = build_capacity_plan(
            self.frame,
            self.scores,
            budget_share=0.50,
        )

        self.assertLessEqual(
            summary.selected_network_m,
            summary.budget_m + 1e-9,
        )

        selected_length = plan.loc[
            plan["selected"],
            "length_m",
        ].sum()

        self.assertAlmostEqual(
            selected_length,
            summary.selected_network_m,
        )

    def test_selection_is_ranked_prefix(self):
        plan, _ = build_capacity_plan(
            self.frame,
            self.scores,
            budget_share=0.80,
        )

        flags = plan[
            "selected"
        ].to_list()

        seen_false = False
        for flag in flags:
            if not flag:
                seen_false = True
            elif seen_false:
                self.fail(
                    "selected assets must form "
                    "a ranked prefix"
                )

    def test_planner_does_not_skip_long_pipe_to_pack_shorter_pipe(
        self,
    ):
        # Eligible network = 200 m.
        # 50% budget = 100 m.
        #
        # pipe_a is first and exactly fills the budget.
        plan, summary = build_capacity_plan(
            self.frame,
            self.scores,
            budget_share=0.50,
            ranking_mode=RANK_PER_ASSET,
        )

        selected = plan.loc[
            plan["selected"],
            "asset_id",
        ].to_list()

        self.assertEqual(
            selected,
            ["pipe_a"],
        )
        self.assertAlmostEqual(
            summary.selected_network_m,
            100.0,
        )

    def test_prefix_stops_when_next_asset_crosses_budget(
        self,
    ):
        frame = pd.DataFrame(
            {
                "asset_id": [
                    "a",
                    "b",
                    "c",
                ],
                "length_m": [
                    60.0,
                    60.0,
                    10.0,
                ],
            },
            index=[
                1,
                2,
                3,
            ],
        )

        scores = pd.Series(
            [0.9, 0.8, 0.7],
            index=frame.index,
        )

        # Total = 130 m; budget = 78 m.
        # a fits (60), b crosses (120), and c must not be packed afterward.
        plan, _ = build_capacity_plan(
            frame,
            scores,
            budget_share=0.60,
        )

        self.assertEqual(
            plan.loc[
                plan["selected"],
                "asset_id",
            ].to_list(),
            ["a"],
        )

    def test_multi_budget_uses_frozen_capacity_set(
        self,
    ):
        plans = build_multi_budget_plans(
            self.frame,
            self.scores,
        )

        self.assertEqual(
            tuple(plans.keys()),
            DEFAULT_BUDGET_SHARES,
        )

    def test_larger_budget_cannot_select_fewer_assets_for_same_ranking(
        self,
    ):
        plans = build_multi_budget_plans(
            self.frame,
            self.scores,
        )

        counts = [
            plans[share][1]
            .selected_asset_count
            for share
            in DEFAULT_BUDGET_SHARES
        ]

        self.assertEqual(
            counts,
            sorted(counts),
        )

    def test_scores_must_match_frame_index_exactly(
        self,
    ):
        scores = self.scores.copy()
        scores.index = [
            205,
            101,
            309,
            401,
        ]

        with self.assertRaises(
            ValueError
        ):
            rank_assets(
                self.frame,
                scores,
            )

    def test_zero_length_is_rejected(self):
        frame = self.frame.copy()
        frame.loc[
            101,
            "length_m",
        ] = 0.0

        with self.assertRaises(
            ValueError
        ):
            rank_assets(
                frame,
                self.scores,
            )

    def test_negative_length_is_rejected(self):
        frame = self.frame.copy()
        frame.loc[
            101,
            "length_m",
        ] = -1.0

        with self.assertRaises(
            ValueError
        ):
            rank_assets(
                frame,
                self.scores,
            )

    def test_invalid_budget_share_is_rejected(
        self,
    ):
        for bad in [
            0.0,
            -0.01,
            1.01,
            np.nan,
        ]:
            with self.subTest(
                budget_share=bad
            ):
                with self.assertRaises(
                    ValueError
                ):
                    build_capacity_plan(
                        self.frame,
                        self.scores,
                        budget_share=bad,
                    )


if __name__ == "__main__":
    unittest.main()