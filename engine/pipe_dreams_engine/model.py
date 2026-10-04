"""Cutoff-safe pipe likelihood models and transparent baselines.

The predictive model is intentionally simple and auditable:

    preprocessing -> regularized logistic regression

Its output is a ranking signal for inspection prioritization. It must not be
presented as a calibrated production failure probability.

This module does not decide inspection capacity, consequence, policy
acceptance, or autonomous revision. Those belong to later engine layers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TARGET_COLUMN = "future_break_label"
EVENT_COLUMN = "future_break_events"

NUMERIC_FEATURES = (
    "age",
    "diameter",
    "length_m",
    "historical_break_weight",
    "nearby_break_weight_200m",
)

CATEGORICAL_FEATURES = (
    "material",
)

MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

FORBIDDEN_FEATURES = {
    TARGET_COLUMN,
    EVENT_COLUMN,
    "outcome_start_year",
    "outcome_end_year",
    "status",
    "pressure_zone",
}


@dataclass(frozen=True)
class FittedPipeModel:
    """A fitted likelihood-ranking model plus auditable metadata."""

    pipeline: Pipeline
    feature_columns: tuple[str, ...]
    n_training_rows: int
    n_positive: int
    positive_rate: float


def _required_columns_missing(
    frame: pd.DataFrame,
    columns,
) -> list[str]:
    return sorted(set(columns) - set(frame.columns))


def _validate_feature_frame(frame: pd.DataFrame) -> None:
    missing = _required_columns_missing(
        frame,
        MODEL_FEATURES,
    )
    if missing:
        raise ValueError(
            f"model frame missing required columns: {missing}"
        )

    accidental = FORBIDDEN_FEATURES.intersection(
        MODEL_FEATURES
    )
    if accidental:
        raise AssertionError(
            "forbidden columns were declared as model features: "
            f"{sorted(accidental)}"
        )


def model_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Return only the declared prediction features.

    Future labels, event counts, current status, pressure zone, geometry,
    asset identifiers, and other metadata cannot enter the model through
    this function.
    """
    _validate_feature_frame(frame)

    X = frame.loc[:, MODEL_FEATURES].copy()

    forbidden_present = (
        set(X.columns) & FORBIDDEN_FEATURES
    )
    if forbidden_present:
        raise AssertionError(
            "future/current-state columns entered model matrix: "
            f"{sorted(forbidden_present)}"
        )

    return X


def _make_pipeline(
    *,
    regularization_c: float = 1.0,
    random_state: int = 0,
) -> Pipeline:
    if regularization_c <= 0:
        raise ValueError(
            "regularization_c must be positive"
        )

    numeric = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    categorical = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="constant",
                    fill_value="UNKNOWN",
                ),
            ),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
            ),
        ]
    )

    preprocess = ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric,
                list(NUMERIC_FEATURES),
            ),
            (
                "categorical",
                categorical,
                list(CATEGORICAL_FEATURES),
            ),
        ],
        remainder="drop",
    )

    classifier = LogisticRegression(
        C=regularization_c,
        max_iter=2000,
        solver="lbfgs",
        random_state=random_state,
    )

    return Pipeline(
        steps=[
            ("preprocess", preprocess),
            ("classifier", classifier),
        ]
    )


def fit_pipe_model(
    training_frame: pd.DataFrame,
    *,
    target_column: str = TARGET_COLUMN,
    regularization_c: float = 1.0,
    random_state: int = 0,
) -> FittedPipeModel:
    """Fit the frozen regularized logistic-regression model.

    ``training_frame`` must already represent a historically valid training
    snapshot with outcomes attached separately by ``attach_future_outcomes``.

    At least one positive and one negative training example are required.
    """
    _validate_feature_frame(training_frame)

    if target_column not in training_frame.columns:
        raise ValueError(
            f"training frame missing target column "
            f"{target_column!r}"
        )

    if len(training_frame) == 0:
        raise ValueError(
            "cannot fit model on an empty training frame"
        )

    target = pd.to_numeric(
        training_frame[target_column],
        errors="coerce",
    )

    if target.isna().any():
        raise ValueError(
            "target contains missing or non-numeric values"
        )

    unique = set(target.astype(int).unique())

    if not unique.issubset({0, 1}):
        raise ValueError(
            "target must contain only binary 0/1 labels"
        )

    if unique != {0, 1}:
        raise ValueError(
            "logistic regression requires both positive "
            "and negative training examples"
        )

    X = model_matrix(training_frame)
    y = target.astype(int).to_numpy()

    pipeline = _make_pipeline(
        regularization_c=regularization_c,
        random_state=random_state,
    )
    pipeline.fit(X, y)

    n_positive = int(y.sum())

    return FittedPipeModel(
        pipeline=pipeline,
        feature_columns=tuple(MODEL_FEATURES),
        n_training_rows=len(training_frame),
        n_positive=n_positive,
        positive_rate=float(
            n_positive / len(training_frame)
        ),
    )


def score_pipe_model(
    fitted: FittedPipeModel,
    scoring_frame: pd.DataFrame,
) -> pd.Series:
    """Return logistic-regression likelihood ranking scores.

    Scores are bounded to [0, 1] because they come from ``predict_proba``,
    but they are used as comparative ranking signals, not asserted to be
    calibrated real-world failure probabilities.
    """
    if not isinstance(fitted, FittedPipeModel):
        raise TypeError(
            "fitted must be a FittedPipeModel"
        )

    X = model_matrix(scoring_frame)

    scores = fitted.pipeline.predict_proba(X)[:, 1]

    if not np.isfinite(scores).all():
        raise AssertionError(
            "model produced non-finite scores"
        )

    if np.any(scores < 0) or np.any(scores > 1):
        raise AssertionError(
            "logistic scores fell outside [0, 1]"
        )

    return pd.Series(
        scores,
        index=scoring_frame.index,
        name="likelihood_score",
        dtype=float,
    )


def count_baseline_scores(
    frame: pd.DataFrame,
    *,
    count_column: str = "historical_break_count",
) -> pd.Series:
    """Transparent count-only comparison baseline.

    This baseline performs no ML and no length normalization. The planner
    may later use these scores to compare capture against the model under
    the same capacity constraint.
    """
    if count_column not in frame.columns:
        raise ValueError(
            f"frame missing count baseline column "
            f"{count_column!r}"
        )

    values = pd.to_numeric(
        frame[count_column],
        errors="coerce",
    )

    if values.isna().any():
        raise ValueError(
            f"{count_column!r} contains missing or "
            "non-numeric values"
        )

    if (values < 0).any():
        raise ValueError(
            f"{count_column!r} cannot contain "
            "negative values"
        )

    return pd.Series(
        values.to_numpy(dtype=float),
        index=frame.index,
        name="count_baseline_score",
    )
    