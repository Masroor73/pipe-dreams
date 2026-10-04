"""Synthetic tests for Pipe Dreams governance rules."""

from __future__ import annotations

import unittest
from datetime import date

import numpy as np
import pandas as pd

from pipe_dreams_engine.governance import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW_VERIFY,
    CONFIDENCE_MEDIUM,
    CONSEQUENCE_T1,
    CONSEQUENCE_T2,
    CONSEQUENCE_T3,
    ACTION_CONDITION_ASSESS,
    ACTION_INSPECT,
    ACTION_MONITOR,
    ACTION_VERIFY,
    apply_governance,
    assign_evidence_confidence,
    association_quality,
    build_escalation_rows,
    build_not_covered_records,
    consequence_tier,
    derive_confidence_thresholds,
    evidence_quality_score,
    recommended_action,
)

SYNTHETIC = True


def _frame():
    return pd.DataFrame(
        {
            "asset_id": [
                "a",
                "b",
                "c",
                "d",
            ],
            "rank": [
                1,
                2,
                3,
                4,
            ],
            "selected": [
                True,
                True,
                False,
                True,
            ],
            "diameter": [
                900.0,
                400.0,
                200.0,
                0.0,
            ],
            "historical_break_count": [
                4,
                2,
                0,
                1,
            ],
            "historical_ambiguous_break_count": [
                0,
                1,
                0,
                1,
            ],
            "historical_mean_match_distance_m": [
                3.0,
                15.0,
                np.nan,
                25.0,
            ],
        },
        index=[
            101,
            205,
            309,
            401,
        ],
    )


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.frame = _frame()

    def test_synthetic_fixtures_are_flagged(self):
        self.assertTrue(SYNTHETIC)

    def test_consequence_tiers_follow_frozen_diameter_rule(
        self,
    ):
        tiers = consequence_tier(
            pd.Series(
                [
                    600,
                    599,
                    300,
                    299,
                    1,
                ]
            )
        )

        self.assertEqual(
            tiers.to_list(),
            [
                CONSEQUENCE_T1,
                CONSEQUENCE_T2,
                CONSEQUENCE_T2,
                CONSEQUENCE_T3,
                CONSEQUENCE_T3,
            ],
        )

    def test_invalid_diameter_is_not_silently_t3(
        self,
    ):
        tiers = consequence_tier(
            pd.Series(
                [
                    0,
                    -1,
                    np.nan,
                ]
            )
        )

        self.assertTrue(
            tiers.isna().all()
        )

    def test_no_history_gets_neutral_association_quality(
        self,
    ):
        quality = association_quality(
            self.frame
        )

        self.assertAlmostEqual(
            quality.loc[309],
            0.5,
        )

    def test_clear_close_matches_score_better_than_ambiguous_far_matches(
        self,
    ):
        quality = association_quality(
            self.frame
        )

        self.assertGreater(
            quality.loc[101],
            quality.loc[205],
        )
        self.assertGreater(
            quality.loc[205],
            quality.loc[401],
        )

    def test_evidence_quality_uses_weaker_component(
        self,
    ):
        assoc = pd.Series(
            [0.9, 0.4],
            index=[
                1,
                2,
            ],
        )

        stability = pd.Series(
            [0.5, 0.8],
            index=[
                1,
                2,
            ],
        )

        result = evidence_quality_score(
            assoc,
            stability,
        )

        np.testing.assert_allclose(
            result.to_numpy(),
            [
                0.5,
                0.4,
            ],
        )

    def test_confidence_thresholds_are_validation_terciles(
        self,
    ):
        values = pd.Series(
            np.linspace(
                0.0,
                1.0,
                101,
            )
        )

        thresholds = (
            derive_confidence_thresholds(
                values
            )
        )

        self.assertAlmostEqual(
            thresholds.low_to_medium,
            1.0 / 3.0,
            places=2,
        )
        self.assertAlmostEqual(
            thresholds.medium_to_high,
            2.0 / 3.0,
            places=2,
        )

    def test_confidence_assignment_uses_frozen_thresholds(
        self,
    ):
        thresholds = (
            derive_confidence_thresholds(
                pd.Series(
                    [
                        0.0,
                        0.3,
                        0.6,
                        0.9,
                    ]
                )
            )
        )

        scores = pd.Series(
            [
                0.1,
                0.5,
                0.95,
            ],
            index=[
                1,
                2,
                3,
            ],
        )

        result = assign_evidence_confidence(
            scores,
            thresholds,
        )

        self.assertEqual(
            result.to_list(),
            [
                CONFIDENCE_LOW_VERIFY,
                CONFIDENCE_MEDIUM,
                CONFIDENCE_HIGH,
            ],
        )

    def test_low_verify_always_routes_to_verify(
        self,
    ):
        self.assertEqual(
            recommended_action(
                CONFIDENCE_LOW_VERIFY,
                True,
                CONSEQUENCE_T1,
            ),
            ACTION_VERIFY,
        )

    def test_selected_t1_routes_to_condition_assess(
        self,
    ):
        self.assertEqual(
            recommended_action(
                CONFIDENCE_HIGH,
                True,
                CONSEQUENCE_T1,
            ),
            ACTION_CONDITION_ASSESS,
        )

    def test_selected_non_t1_routes_to_inspect(
        self,
    ):
        self.assertEqual(
            recommended_action(
                CONFIDENCE_HIGH,
                True,
                CONSEQUENCE_T2,
            ),
            ACTION_INSPECT,
        )

    def test_unselected_routes_to_monitor(
        self,
    ):
        self.assertEqual(
            recommended_action(
                CONFIDENCE_HIGH,
                False,
                CONSEQUENCE_T1,
            ),
            ACTION_MONITOR,
        )

    def test_apply_governance_invalid_diameter_becomes_low_verify(
        self,
    ):
        validation_scores = pd.Series(
            np.linspace(
                0.0,
                1.0,
                30,
            )
        )

        thresholds = (
            derive_confidence_thresholds(
                validation_scores
            )
        )

        stability = pd.Series(
            [
                0.95,
                0.80,
                0.60,
                0.90,
            ],
            index=self.frame.index,
        )

        result = apply_governance(
            self.frame,
            rank_stability=stability,
            thresholds=thresholds,
        )

        self.assertEqual(
            result.loc[
                401,
                "evidence_confidence",
            ],
            CONFIDENCE_LOW_VERIFY,
        )

        self.assertEqual(
            result.loc[
                401,
                "recommended_action",
            ],
            ACTION_VERIFY,
        )

    def test_escalation_rule_is_t1_plus_low_verify(
        self,
    ):
        frame = pd.DataFrame(
            {
                "asset_id": [
                    "a",
                    "b",
                    "c",
                ],
                "rank": [
                    1,
                    2,
                    3,
                ],
                "consequence_tier": [
                    CONSEQUENCE_T1,
                    CONSEQUENCE_T1,
                    CONSEQUENCE_T2,
                ],
                "evidence_confidence": [
                    CONFIDENCE_LOW_VERIFY,
                    CONFIDENCE_HIGH,
                    CONFIDENCE_LOW_VERIFY,
                ],
            }
        )

        rows = build_escalation_rows(
            frame,
            start_date=date(
                2026,
                10,
                4,
            ),
            last_reviewed=date(
                2026,
                10,
                4,
            ),
        )

        self.assertEqual(
            rows["asset_id"].to_list(),
            ["a"],
        )

        self.assertEqual(
            rows.iloc[0][
                "required_action"
            ],
            "Verify asset record before scheduling",
        )

    def test_not_covered_records_are_explicit(
        self,
    ):
        rows = build_not_covered_records()

        self.assertGreaterEqual(
            len(rows),
            4,
        )

        required = {
            "coverage_issue_id",
            "scope",
            "description",
            "why_not_covered",
            "required_evidence",
            "ui_severity",
            "source_note",
        }

        self.assertEqual(
            set(rows.columns),
            required,
        )

        self.assertTrue(
            rows[
                "coverage_issue_id"
            ].is_unique
        )


if __name__ == "__main__":
    unittest.main()