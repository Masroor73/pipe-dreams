"""Derive Pipe Dreams evidence-confidence thresholds before final testing.

Safety rules:
- break records are truncated to <= 2022 before association;
- confidence thresholds use validation snapshots 2013/2016/2019 only;
- fitted models use training cutoffs 2010/2013/2016 only;
- no 2023-2025 outcome is accessed.

Rank stability:
    Apply the three historical V1 models to the same snapshot.
    Convert each score vector to within-snapshot percentile ranks.
    stability = 1 - (max_percentile - min_percentile)

Thus stability lies in [0, 1], where 1 means the asset's relative
ranking is unchanged across historical model fits.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipe_dreams_engine.agent import V1_POLICY
from pipe_dreams_engine.evidence import (
    attach_future_outcomes,
    build_evidence_snapshot,
)
from pipe_dreams_engine.governance import (
    association_quality,
    derive_confidence_thresholds,
    evidence_quality_score,
)
from pipe_dreams_engine.matching import associate_breaks
from pipe_dreams_engine.model import (
    fit_pipe_model,
    score_pipe_model,
)
from pipe_dreams_engine.real_data import load_real_inputs


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BREAKS = (
    ROOT / "data" / "audit_working" / "data" / "breaks_raw.json"
)
DEFAULT_PIPES = (
    ROOT / "data" / "audit_working" / "data" / "pipes_raw.json"
)
DEFAULT_COMMUNITIES = (
    ROOT / "data" / "external" / "community_boundaries.csv"
)
DEFAULT_OUT = (
    ROOT
    / "data"
    / "audit_working"
    / "evidence_confidence_preview.json"
)

MAX_BREAK_YEAR = 2022
HORIZON_YEARS = 3

TRAINING_CUTOFFS = (2010, 2013, 2016)
VALIDATION_CUTOFFS = (2013, 2016, 2019)


def percentile_rank(scores: pd.Series) -> pd.Series:
    """Return deterministic within-snapshot percentile rank in [0, 1]."""
    numeric = pd.to_numeric(scores, errors="coerce")

    if numeric.isna().any():
        raise ValueError("model scores contain missing values")

    if len(numeric) == 0:
        raise ValueError("cannot rank empty score vector")

    # rank(pct=True) is deterministic for ties with method='average'.
    return numeric.rank(
        method="average",
        pct=True,
    ).astype(float)


def rank_stability_for_snapshot(
    frame: pd.DataFrame,
    fitted_models: list,
) -> pd.Series:
    """Measure relative-rank stability across frozen historical V1 fits."""
    rank_columns = []

    for fitted in fitted_models:
        scores = score_pipe_model(
            fitted,
            frame,
        )

        rank_columns.append(
            percentile_rank(scores)
        )

    ranks = pd.concat(
        rank_columns,
        axis=1,
    )

    rank_range = (
        ranks.max(axis=1)
        - ranks.min(axis=1)
    )

    stability = (
        1.0 - rank_range
    ).clip(
        lower=0.0,
        upper=1.0,
    )

    stability.name = "rank_stability"

    if not np.isfinite(
        stability.to_numpy(dtype=float)
    ).all():
        raise AssertionError(
            "rank stability contains non-finite values"
        )

    return stability


def summary(values: pd.Series) -> dict[str, float]:
    x = pd.to_numeric(
        values,
        errors="coerce",
    ).dropna()

    return {
        "min": float(x.min()),
        "p10": float(x.quantile(0.10)),
        "p25": float(x.quantile(0.25)),
        "median": float(x.quantile(0.50)),
        "p75": float(x.quantile(0.75)),
        "p90": float(x.quantile(0.90)),
        "max": float(x.max()),
        "mean": float(x.mean()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "--breaks",
        type=Path,
        default=DEFAULT_BREAKS,
    )
    parser.add_argument(
        "--pipes",
        type=Path,
        default=DEFAULT_PIPES,
    )
    parser.add_argument(
        "--communities",
        type=Path,
        default=DEFAULT_COMMUNITIES,
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
    )

    args = parser.parse_args()

    print("PIPE DREAMS EVIDENCE-CONFIDENCE DERIVATION")
    print("Safety boundary: break_year <= 2022")
    print()

    (
        communities,
        pipes,
        all_breaks,
        diagnostics,
    ) = load_real_inputs(
        breaks_path=args.breaks,
        pipes_path=args.pipes,
        communities_path=args.communities,
    )

    pipes = (
        pipes.copy()
        .reset_index(drop=True)
    )

    breaks = (
        all_breaks.loc[
            pd.to_numeric(
                all_breaks["break_year"],
                errors="coerce",
            )
            <= MAX_BREAK_YEAR
        ]
        .copy()
        .reset_index(drop=True)
    )

    if (
        pd.to_numeric(
            breaks["break_year"],
            errors="coerce",
        ).max()
        > MAX_BREAK_YEAR
    ):
        raise RuntimeError(
            "break safety boundary failed"
        )

    print(f"eligible pipes: {len(pipes):,}")
    print(f"safe breaks: {len(breaks):,}")
    print(f"communities: {len(communities):,}")
    print()

    print("Associating validation-safe breaks...")
    associations = associate_breaks(
        breaks,
        pipes,
    )

    print(
        "associated:",
        f"{int(associations['associated'].sum()):,}",
    )
    print()

    snapshot_cache: dict[int, pd.DataFrame] = {}

    def v1_snapshot(
        cutoff: int,
    ) -> pd.DataFrame:
        if cutoff not in snapshot_cache:
            snapshot_cache[cutoff] = (
                build_evidence_snapshot(
                    pipes,
                    breaks,
                    associations,
                    cutoff_year=cutoff,
                    history_start_year=None,
                    recency="none",
                )
            )

        return snapshot_cache[cutoff]

    print("Fitting frozen historical V1 models...")

    fitted_models = []

    for training_cutoff in TRAINING_CUTOFFS:
        if (
            training_cutoff
            + HORIZON_YEARS
            > MAX_BREAK_YEAR
        ):
            raise RuntimeError(
                "training outcome crosses safety boundary"
            )

        training = attach_future_outcomes(
            v1_snapshot(training_cutoff),
            pipes,
            breaks,
            associations,
            cutoff_year=training_cutoff,
            horizon_years=HORIZON_YEARS,
        )

        fitted = fit_pipe_model(
            training
        )

        fitted_models.append(
            fitted
        )

        print(
            f"{training_cutoff}: "
            f"{fitted.n_training_rows:,} rows, "
            f"{fitted.n_positive:,} positives"
        )

    print()
    print(
        "Deriving evidence quality from validation snapshots..."
    )

    pooled_validation_quality = []
    validation_summaries = {}

    for cutoff in VALIDATION_CUTOFFS:
        frame = v1_snapshot(
            cutoff
        )

        stability = (
            rank_stability_for_snapshot(
                frame,
                fitted_models,
            )
        )

        assoc_quality = (
            association_quality(
                frame
            )
        )

        quality = (
            evidence_quality_score(
                assoc_quality,
                stability,
            )
        )

        pooled_validation_quality.append(
            pd.Series(
                quality,
                index=frame.index,
                dtype=float,
            )
        )

        validation_summaries[
            str(cutoff)
        ] = {
            "assets": int(
                len(frame)
            ),
            "association_quality": summary(
                pd.Series(
                    assoc_quality,
                    index=frame.index,
                )
            ),
            "rank_stability": summary(
                stability
            ),
            "evidence_quality": summary(
                pd.Series(
                    quality,
                    index=frame.index,
                )
            ),
        }

        print(
            f"{cutoff}: "
            f"{len(frame):,} assets"
        )

    pooled_quality = pd.concat(
        pooled_validation_quality,
        ignore_index=True,
    )

    # The exact 0.5 evidence-quality value is the frozen
    # limited-direct-evidence sentinel produced for assets with
    # no historically attributed breaks. Do not let that point mass
    # collapse validation terciles.
    #
    # Thresholds are therefore learned only from validation assets
    # with evidence quality strictly greater than the neutral sentinel.
    # Assets at or below 0.5 remain LOW_VERIFY under the resulting
    # thresholds.
    informative_validation_quality = (
        pooled_quality.loc[
            pooled_quality > 0.5
        ]
    )

    if len(informative_validation_quality) == 0:
        raise RuntimeError(
            "validation contains no informative evidence-quality "
            "scores above the neutral 0.5 sentinel"
        )

    thresholds = (
        derive_confidence_thresholds(
            informative_validation_quality
        )
    )

    if thresholds.low_to_medium <= 0.5:
        raise AssertionError(
            "LOW->MEDIUM threshold must remain above "
            "the neutral 0.5 evidence sentinel"
        )

    if (
        thresholds.medium_to_high
        <= thresholds.low_to_medium
    ):
        raise AssertionError(
            "confidence thresholds did not separate"
        )

    print()
    print("FROZEN VALIDATION-ONLY THRESHOLDS")
    print(
        "LOW -> MEDIUM:",
        f"{thresholds.low_to_medium:.12f}",
    )
    print(
        "MEDIUM -> HIGH:",
        f"{thresholds.medium_to_high:.12f}",
    )
    print(
        "source:",
        thresholds.source,
    )

    # Calculate current planning-time stability, but do not derive
    # thresholds from it.
    current_frame = v1_snapshot(
        2022
    )

    current_stability = (
        rank_stability_for_snapshot(
            current_frame,
            fitted_models,
        )
    )

    current_assoc_quality = (
        association_quality(
            current_frame
        )
    )

    current_quality = (
        evidence_quality_score(
            current_assoc_quality,
            current_stability,
        )
    )

    payload = {
        "validation_only": True,
        "final_test_executed": False,
        "max_break_year_used": MAX_BREAK_YEAR,
        "policy_basis": V1_POLICY.policy_id,
        "training_cutoffs": list(
            TRAINING_CUTOFFS
        ),
        "validation_cutoffs": list(
            VALIDATION_CUTOFFS
        ),
        "rank_stability_definition": (
            "1 - range of within-snapshot percentile ranks "
            "across frozen V1 models trained at 2010, 2013, 2016"
        ),
        "threshold_derivation": (
            "governance terciles over pooled 2013/2016/2019 "
            "validation evidence-quality scores strictly above "
            "the neutral 0.5 limited-direct-evidence sentinel"
        ),
        "neutral_evidence_sentinel": 0.5,
        "informative_validation_assets": int(
            len(informative_validation_quality)
        ),
        "pooled_validation_assets": int(
            len(pooled_quality)
        ),
        "thresholds": {
            "low_to_medium": float(
                thresholds.low_to_medium
            ),
            "medium_to_high": float(
                thresholds.medium_to_high
            ),
            "source": thresholds.source,
        },
        "validation_summary": (
            validation_summaries
        ),
        "current_2022_summary": {
            "assets": int(
                len(current_frame)
            ),
            "association_quality": summary(
                pd.Series(
                    current_assoc_quality,
                    index=current_frame.index,
                )
            ),
            "rank_stability": summary(
                current_stability
            ),
            "evidence_quality": summary(
                pd.Series(
                    current_quality,
                    index=current_frame.index,
                )
            ),
        },
        "data_diagnostics": diagnostics,
    }

    args.out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.out.write_text(
        json.dumps(
            payload,
            indent=2,
        )
        + "\n"
    )

    print()
    print("Preview written to:")
    print(args.out)
    print()
    print("FINAL TEST WAS NOT EXECUTED.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
