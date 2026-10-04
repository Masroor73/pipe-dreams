"""Synthetic tests for the Pipe Dreams likelihood model."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from pipe_dreams_engine.model import (
    CATEGORICAL_FEATURES,
    FORBIDDEN_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
    count_baseline_scores,
    fit_pipe_model,
    model_matrix,
    score_pipe_model,
)

SYNTHETIC = True


def _training_frame():
    return pd.DataFrame(
        {
            "asset_id": [
                "a",
                "b",
                "c",
                "d",
                "e",
                "f",
            ],
            "age": [
                10,
                70,
                20,
                80,
                15,
                60,
            ],
            "diameter": [
                200,
                300,
                150,
                400,
                np.nan,
                250,
            ],
            "length_m": [
                100.0,
                90.0,
                80.0,
                120.0,
                75.0,
                110.0,
            ],
            "historical_break_count": [
                0,
                4,
                0,
                6,
                1,
                3,
            ],
            "historical_break_weight": [
                0.0,
                4.0,
                0.0,
                6.0,
                1.0,
                3.0,
            ],
            "nearby_break_weight_200m": [
                0.0,
                5.0,
                1.0,
                7.0,
                0.0,
                4.0,
            ],
            "material": [
                "PVC",
                "CI",
                "PVC",
                "CI",
                None,
                "ST",
            ],
            "status": [
                "ACTIVE",
                "ACTIVE",
                "ACTIVE",
                "ACTIVE",
                "ACTIVE",
                "ACTIVE",
            ],
            "pressure_zone": [
                "A",
                "B",
                "A",
                "B",
                "A",
                "C",
            ],
            "future_break_events": [
                0,
                1,
                0,
                2,
                0,
                1,
            ],
            "future_break_label": [
                0,
                1,
                0,
                1,
                0,
                1,
            ],
            "outcome_start_year": [
                2017,
                2017,
                2017,
                2017,
                2017,
                2017,
            ],
            "outcome_end_year": [
                2019,
                2019,
                2019,
                2019,
                2019,
                2019,
            ],
        },
        index=[
            101,
            205,
            309,
            401,
            550,
            777,
        ],
    )


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.frame = _training_frame()

    def test_synthetic_fixtures_are_flagged(self):
        self.assertTrue(SYNTHETIC)

    def test_declared_features_do_not_include_forbidden_fields(
        self,
    ):
        self.assertFalse(
            set(MODEL_FEATURES)
            & FORBIDDEN_FEATURES
        )

    def test_feature_groups_cover_model_features(self):
        self.assertEqual(
            tuple(NUMERIC_FEATURES)
            + tuple(CATEGORICAL_FEATURES),
            tuple(MODEL_FEATURES),
        )

    def test_model_matrix_contains_only_declared_features(
        self,
    ):
        X = model_matrix(self.frame)

        self.assertEqual(
            list(X.columns),
            list(MODEL_FEATURES),
        )

        self.assertNotIn(
            "future_break_label",
            X.columns,
        )
        self.assertNotIn(
            "future_break_events",
            X.columns,
        )
        self.assertNotIn(
            "status",
            X.columns,
        )
        self.assertNotIn(
            "pressure_zone",
            X.columns,
        )

    def test_model_fits_with_missing_numeric_and_material(
        self,
    ):
        fitted = fit_pipe_model(self.frame)

        self.assertEqual(
            fitted.n_training_rows,
            6,
        )
        self.assertEqual(
            fitted.n_positive,
            3,
        )
        self.assertAlmostEqual(
            fitted.positive_rate,
            0.5,
        )

    def test_model_scores_are_finite_and_bounded(self):
        fitted = fit_pipe_model(self.frame)

        scores = score_pipe_model(
            fitted,
            self.frame,
        )

        self.assertEqual(
            list(scores.index),
            list(self.frame.index),
        )
        self.assertTrue(
            np.isfinite(scores).all()
        )
        self.assertTrue(
            ((scores >= 0) & (scores <= 1)).all()
        )

    def test_unseen_material_can_be_scored(self):
        fitted = fit_pipe_model(self.frame)

        scoring = self.frame.iloc[[0]].copy()
        scoring["material"] = "UNSEEN_MATERIAL"

        scores = score_pipe_model(
            fitted,
            scoring,
        )

        self.assertEqual(len(scores), 1)
        self.assertTrue(
            np.isfinite(scores.iloc[0])
        )

    def test_current_status_cannot_change_model_score(self):
        fitted = fit_pipe_model(self.frame)

        first = self.frame.iloc[[0]].copy()
        changed = first.copy()
        changed["status"] = "RETIRED"

        score_a = score_pipe_model(
            fitted,
            first,
        ).iloc[0]
        score_b = score_pipe_model(
            fitted,
            changed,
        ).iloc[0]

        self.assertAlmostEqual(
            score_a,
            score_b,
        )

    def test_pressure_zone_cannot_change_model_score(self):
        fitted = fit_pipe_model(self.frame)

        first = self.frame.iloc[[0]].copy()
        changed = first.copy()
        changed["pressure_zone"] = "OTHER"

        score_a = score_pipe_model(
            fitted,
            first,
        ).iloc[0]
        score_b = score_pipe_model(
            fitted,
            changed,
        ).iloc[0]

        self.assertAlmostEqual(
            score_a,
            score_b,
        )

    def test_future_outcomes_cannot_change_model_score(self):
        fitted = fit_pipe_model(self.frame)

        first = self.frame.iloc[[0]].copy()
        changed = first.copy()

        changed["future_break_label"] = 1
        changed["future_break_events"] = 999
        changed["outcome_start_year"] = 9999
        changed["outcome_end_year"] = 9999

        score_a = score_pipe_model(
            fitted,
            first,
        ).iloc[0]
        score_b = score_pipe_model(
            fitted,
            changed,
        ).iloc[0]

        self.assertAlmostEqual(
            score_a,
            score_b,
        )

    def test_training_requires_target(self):
        frame = self.frame.drop(
            columns=["future_break_label"]
        )

        with self.assertRaises(ValueError):
            fit_pipe_model(frame)

    def test_training_rejects_single_class_target(self):
        frame = self.frame.copy()
        frame["future_break_label"] = 0

        with self.assertRaises(ValueError):
            fit_pipe_model(frame)

    def test_count_baseline_uses_raw_historical_count(self):
        scores = count_baseline_scores(
            self.frame
        )

        np.testing.assert_allclose(
            scores.to_numpy(),
            self.frame[
                "historical_break_count"
            ].to_numpy(dtype=float),
        )

    def test_count_baseline_preserves_index(self):
        scores = count_baseline_scores(
            self.frame
        )

        self.assertEqual(
            list(scores.index),
            list(self.frame.index),
        )

    def test_count_baseline_rejects_negative_counts(self):
        frame = self.frame.copy()
        frame.loc[101, "historical_break_count"] = -1

        with self.assertRaises(ValueError):
            count_baseline_scores(frame)


if __name__ == "__main__":
    unittest.main()