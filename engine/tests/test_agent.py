"""Synthetic tests for the autonomous V1-to-V2 revision gate."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd
from shapely.geometry import LineString

from pipe_dreams_engine.agent import (
    CANDIDATE_POLICIES,
    MIN_ORIGIN_WINS,
    POLICY_BY_ID,
    V1_POLICY,
    V1_POLICY_ID,
    build_agent_log,
    evaluate_candidate_gate,
    evaluate_revision_gate,
)
from pipe_dreams_engine.evaluation import (
    VALIDATION_CUTOFFS,
    evaluate_policy_origin,
)

SYNTHETIC = True


def _frame():
    rows = []

    for i in range(40):
        x = float(i * 600)

        rows.append(
            {
                "asset_id": (
                    f"pipe_{i:02d}"
                ),
                "length_m": 25.0,
                "future_break_label": (
                    1
                    if i in {
                        0,
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                    }
                    else 0
                ),
                "future_break_events": (
                    1
                    if i in {
                        0,
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                    }
                    else 0
                ),
                "geometry": LineString(
                    [
                        (x, 0.0),
                        (x + 20.0, 0.0),
                    ]
                ),
            }
        )

    return pd.DataFrame(
        rows,
        index=[
            1000 + i * 7
            for i in range(40)
        ],
    )


def _good_scores(frame):
    # Breaking assets rank first.
    return pd.Series(
        np.linspace(
            1.0,
            0.0,
            len(frame),
        ),
        index=frame.index,
        name="score",
    )


def _bad_scores(frame):
    # Breaking assets rank last.
    return pd.Series(
        np.linspace(
            0.0,
            1.0,
            len(frame),
        ),
        index=frame.index,
        name="score",
    )


def _origins(
    frame,
    scores,
):
    return tuple(
        evaluate_policy_origin(
            frame,
            scores,
            cutoff_year=cutoff,
        )
        for cutoff
        in VALIDATION_CUTOFFS
    )


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.frame = _frame()
        self.good = _origins(
            self.frame,
            _good_scores(
                self.frame
            ),
        )
        self.bad = _origins(
            self.frame,
            _bad_scores(
                self.frame
            ),
        )

    def test_synthetic_fixtures_are_flagged(
        self,
    ):
        self.assertTrue(SYNTHETIC)

    def test_v1_definition_is_frozen(self):
        self.assertEqual(
            V1_POLICY.policy_id,
            "V1",
        )
        self.assertEqual(
            V1_POLICY.history_window,
            "full",
        )
        self.assertEqual(
            V1_POLICY.recency_decay,
            "none",
        )
        self.assertEqual(
            V1_POLICY.ranking_normalization,
            "per_asset",
        )

    def test_four_candidate_ids_match_config(
        self,
    ):
        self.assertEqual(
            [
                policy.policy_id
                for policy
                in CANDIDATE_POLICIES
            ],
            [
                "C1",
                "C2",
                "C3",
                "C4",
            ],
        )

    def test_c3_maps_to_per_metre_planner_mode(
        self,
    ):
        self.assertEqual(
            POLICY_BY_ID[
                "C3"
            ].ranking_mode,
            "per_metre",
        )

    def test_candidate_that_beats_v1_passes_gate(
        self,
    ):
        decision = (
            evaluate_candidate_gate(
                "C1",
                self.bad,
                self.good,
                bootstrap_reps=100,
                bootstrap_seed=7,
            )
        )

        self.assertEqual(
            decision.origin_wins,
            3,
        )
        self.assertGreaterEqual(
            decision.origin_wins,
            MIN_ORIGIN_WINS,
        )
        self.assertGreater(
            decision.difference,
            0.0,
        )
        self.assertEqual(
            decision.decision,
            "ACCEPT",
        )

    def test_identical_candidate_is_rejected(
        self,
    ):
        decision = (
            evaluate_candidate_gate(
                "C1",
                self.bad,
                self.bad,
                bootstrap_reps=100,
                bootstrap_seed=7,
            )
        )

        self.assertEqual(
            decision.origin_wins,
            0,
        )
        self.assertAlmostEqual(
            decision.difference,
            0.0,
        )
        self.assertEqual(
            decision.decision,
            "REJECT",
        )

    def test_unknown_candidate_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            evaluate_candidate_gate(
                "C99",
                self.bad,
                self.good,
                bootstrap_reps=50,
            )

    def test_revision_gate_requires_all_four_candidates(
        self,
    ):
        candidates = {
            "C1": (
                self.good
            ),
        }

        with self.assertRaises(
            ValueError
        ):
            evaluate_revision_gate(
                self.bad,
                candidates,
                bootstrap_reps=50,
            )

    def test_no_passing_candidates_retains_v1(
        self,
    ):
        candidates = {
            policy.policy_id: self.bad
            for policy
            in CANDIDATE_POLICIES
        }

        selection = (
            evaluate_revision_gate(
                self.bad,
                candidates,
                bootstrap_reps=50,
                bootstrap_seed=3,
            )
        )

        self.assertEqual(
            selection.selected_policy_id,
            V1_POLICY_ID,
        )
        self.assertTrue(
            selection.v2_equals_v1
        )
        self.assertTrue(
            all(
                not decision.accepted
                for decision
                in selection.decisions
            )
        )

    def test_passing_candidate_can_become_v2(
        self,
    ):
        candidates = {
            policy.policy_id: (
                self.good
                if policy.policy_id
                == "C1"
                else self.bad
            )
            for policy
            in CANDIDATE_POLICIES
        }

        selection = (
            evaluate_revision_gate(
                self.bad,
                candidates,
                bootstrap_reps=100,
                bootstrap_seed=5,
            )
        )

        self.assertEqual(
            selection.selected_policy_id,
            "C1",
        )
        self.assertFalse(
            selection.v2_equals_v1
        )

    def test_candidate_payload_matches_required_schema(
        self,
    ):
        decision = (
            evaluate_candidate_gate(
                "C1",
                self.bad,
                self.good,
                bootstrap_reps=50,
                bootstrap_seed=9,
            )
        )

        payload = (
            decision.to_candidate_payload()
        )

        self.assertEqual(
            set(payload),
            {
                "candidate_id",
                "origin_wins",
                "n_origins",
                "pooled_v1_score",
                "pooled_candidate_score",
                "difference",
                "bootstrap_se",
                "required_delta",
                "decision",
                "reason",
            },
        )

    def test_agent_log_sequence_is_unique_and_ascending(
        self,
    ):
        candidates = {
            policy.policy_id: self.bad
            for policy
            in CANDIDATE_POLICIES
        }

        selection = (
            evaluate_revision_gate(
                self.bad,
                candidates,
                bootstrap_reps=50,
                bootstrap_seed=1,
            )
        )

        log = build_agent_log(
            selection,
            timestamp=(
                "2026-10-04T00:00:00+00:00"
            ),
        )

        seq = [
            event["seq"]
            for event in log
        ]

        self.assertEqual(
            seq,
            list(
                range(
                    1,
                    len(log) + 1,
                )
            ),
        )

    def test_candidate_is_present_on_test_accept_reject_events(
        self,
    ):
        candidates = {
            policy.policy_id: (
                self.good
                if policy.policy_id
                == "C1"
                else self.bad
            )
            for policy
            in CANDIDATE_POLICIES
        }

        selection = (
            evaluate_revision_gate(
                self.bad,
                candidates,
                bootstrap_reps=50,
                bootstrap_seed=4,
            )
        )

        log = build_agent_log(
            selection,
            timestamp=(
                "2026-10-04T00:00:00+00:00"
            ),
        )

        for event in log:
            if event["event_type"] in {
                "TEST_CANDIDATE",
                "ACCEPT",
                "REJECT",
            }:
                self.assertIsNotNone(
                    event["candidate"]
                )

                self.assertIn(
                    event["candidate"][
                        "decision"
                    ],
                    {
                        "ACCEPT",
                        "REJECT",
                    },
                )

    def test_agent_log_ends_with_plan_v2(
        self,
    ):
        candidates = {
            policy.policy_id: self.bad
            for policy
            in CANDIDATE_POLICIES
        }

        selection = (
            evaluate_revision_gate(
                self.bad,
                candidates,
                bootstrap_reps=50,
            )
        )

        log = build_agent_log(
            selection,
            timestamp=(
                "2026-10-04T00:00:00+00:00"
            ),
        )

        self.assertEqual(
            log[-1]["event_type"],
            "PLAN_V2",
        )

        self.assertEqual(
            log[-1]["details"][
                "selected_policy_id"
            ],
            V1_POLICY_ID,
        )


if __name__ == "__main__":
    unittest.main()