"""Optional read-only loader for community intelligence artifacts.

Community artifacts are intentionally separate from the mandatory
pipe-level artifact set. Their absence must not degrade the existing
Pipe Dreams API.

No spatial analysis, scoring, ranking, or model fitting occurs here.
This service validates and serves frozen offline-generated artifacts.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

COMMUNITIES_FILE = "communities.csv"
COMMUNITY_VALIDATION_FILE = "community_validation.csv"
COMMUNITY_GEOJSON_TEMPLATE = "communities_{cutoff_year}.geojson"

COMMUNITY_COLUMNS = (
    "community_id",
    "community_name",
    "cutoff_year",
    "pipe_length_km",
    "historical_break_count",
    "historical_breaks_per_km",
    "population",
    "equity_index",
    "equity_geography_status",
    "data_quality_flags",
)

COMMUNITY_VALIDATION_COLUMNS = (
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
)

ALLOWED_EQUITY_GEOGRAPHY_STATUS = (
    "NOT_ASSESSED",
    "DIRECT",
    "AREA_WEIGHTED",
    "UNAVAILABLE",
)


class CommunityArtifactsUnavailableError(Exception):
    """Raised when optional community artifacts cannot be served."""


class CommunityCutoffNotFoundError(Exception):
    """Raised when a requested community cutoff is not available."""

    def __init__(self, cutoff_year: int) -> None:
        super().__init__(str(cutoff_year))
        self.cutoff_year = cutoff_year


def _clean(value: Any) -> Any:
    """Convert pandas/numpy values to JSON-safe plain Python values."""

    if value is None:
        return None

    if isinstance(value, (np.bool_, bool)):
        return bool(value)

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, (np.floating, float)):
        number = float(value)
        return None if math.isnan(number) else number

    if isinstance(value, str):
        return value

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            str(key): _clean(value)
            for key, value in row.items()
        }
        for row in df.to_dict(orient="records")
    ]


def _missing_columns(
    df: pd.DataFrame,
    required: tuple[str, ...],
) -> list[str]:
    return [
        column
        for column in required
        if column not in df.columns
    ]


def _decode_flags(
    value: Any,
) -> list[str]:
    if value is None or (
        isinstance(value, float)
        and math.isnan(value)
    ):
        return []

    if isinstance(value, list):
        return [str(item) for item in value]

    if not isinstance(value, str):
        raise ValueError(
            "data_quality_flags must be a JSON array"
        )

    parsed = json.loads(value)

    if not isinstance(parsed, list):
        raise ValueError(
            "data_quality_flags must decode to an array"
        )

    return [
        str(item)
        for item in parsed
    ]


class CommunityArtifactService:
    """Load and expose optional frozen community artifacts."""

    def __init__(
        self,
        artifact_dir: Path,
    ) -> None:
        self.artifact_dir = Path(artifact_dir)
        self.loaded = False
        self.errors: list[str] = []
        self.available_cutoffs: tuple[int, ...] = ()

        self._communities = pd.DataFrame()
        self._validation = pd.DataFrame()
        self._geojson_by_cutoff: dict[
            int,
            dict[str, Any],
        ] = {}

        self._load()

    def _load(self) -> None:
        communities_path = (
            self.artifact_dir
            / COMMUNITIES_FILE
        )

        validation_path = (
            self.artifact_dir
            / COMMUNITY_VALIDATION_FILE
        )

        # Community artifacts are optional. If neither root file exists,
        # simply report the capability as unavailable without treating
        # this as a core application failure.
        if (
            not communities_path.is_file()
            and not validation_path.is_file()
        ):
            return

        if not communities_path.is_file():
            self.errors.append(
                f"{COMMUNITIES_FILE}: file is missing"
            )

        if not validation_path.is_file():
            self.errors.append(
                f"{COMMUNITY_VALIDATION_FILE}: file is missing"
            )

        if self.errors:
            return

        try:
            communities = pd.read_csv(
                communities_path
            )
        except Exception as exc:
            self.errors.append(
                f"{COMMUNITIES_FILE}: cannot parse CSV ({exc})"
            )
            return

        try:
            validation = pd.read_csv(
                validation_path
            )
        except Exception as exc:
            self.errors.append(
                f"{COMMUNITY_VALIDATION_FILE}: cannot parse CSV ({exc})"
            )
            return

        missing = _missing_columns(
            communities,
            COMMUNITY_COLUMNS,
        )

        if missing:
            self.errors.append(
                f"{COMMUNITIES_FILE}: missing required columns {missing}"
            )

        missing_validation = _missing_columns(
            validation,
            COMMUNITY_VALIDATION_COLUMNS,
        )

        if missing_validation:
            self.errors.append(
                f"{COMMUNITY_VALIDATION_FILE}: "
                f"missing required columns {missing_validation}"
            )

        if self.errors:
            return

        cutoff_numeric = pd.to_numeric(
            communities["cutoff_year"],
            errors="coerce",
        )

        if cutoff_numeric.isna().any():
            self.errors.append(
                f"{COMMUNITIES_FILE}: cutoff_year must be numeric"
            )
            return

        communities = communities.copy()
        communities["cutoff_year"] = (
            cutoff_numeric.astype(int)
        )

        duplicate_mask = communities.duplicated(
            subset=[
                "community_id",
                "cutoff_year",
            ],
            keep=False,
        )

        if duplicate_mask.any():
            self.errors.append(
                f"{COMMUNITIES_FILE}: duplicate "
                "(community_id, cutoff_year) rows"
            )
            return

        bad_status = sorted(
            {
                str(value)
                for value in communities[
                    "equity_geography_status"
                ].dropna().unique()
                if value
                not in ALLOWED_EQUITY_GEOGRAPHY_STATUS
            }
        )

        if bad_status:
            self.errors.append(
                f"{COMMUNITIES_FILE}: "
                "equity_geography_status contains invalid values "
                f"{bad_status}"
            )
            return

        try:
            communities["data_quality_flags"] = (
                communities[
                    "data_quality_flags"
                ].map(_decode_flags)
            )
        except Exception as exc:
            self.errors.append(
                f"{COMMUNITIES_FILE}: "
                f"invalid data_quality_flags ({exc})"
            )
            return

        cutoffs = tuple(
            sorted(
                communities[
                    "cutoff_year"
                ].unique().tolist()
            )
        )

        geojson_by_cutoff: dict[
            int,
            dict[str, Any],
        ] = {}

        for cutoff_year in cutoffs:
            path = (
                self.artifact_dir
                / COMMUNITY_GEOJSON_TEMPLATE.format(
                    cutoff_year=cutoff_year
                )
            )

            if not path.is_file():
                self.errors.append(
                    f"{path.name}: file is missing"
                )
                continue

            try:
                obj = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            except Exception as exc:
                self.errors.append(
                    f"{path.name}: cannot parse JSON ({exc})"
                )
                continue

            if not isinstance(obj, dict):
                self.errors.append(
                    f"{path.name}: "
                    "top-level JSON value must be an object"
                )
                continue

            if obj.get("type") != "FeatureCollection":
                self.errors.append(
                    f"{path.name}: "
                    "type must be FeatureCollection"
                )
                continue

            features = obj.get("features")

            if not isinstance(features, list):
                self.errors.append(
                    f"{path.name}: "
                    "features must be an array"
                )
                continue

            geojson_by_cutoff[
                int(cutoff_year)
            ] = obj

        if self.errors:
            return

        self._communities = communities
        self._validation = validation
        self._geojson_by_cutoff = (
            geojson_by_cutoff
        )
        self.available_cutoffs = cutoffs
        self.loaded = True

    def _resolve_cutoff(
        self,
        cutoff_year: int | None,
    ) -> int:
        if not self.loaded:
            raise CommunityArtifactsUnavailableError(
                "Community artifacts are missing or failed validation."
            )

        if not self.available_cutoffs:
            raise CommunityArtifactsUnavailableError(
                "No community cutoffs are available."
            )

        if cutoff_year is None:
            return self.available_cutoffs[-1]

        if cutoff_year not in self.available_cutoffs:
            raise CommunityCutoffNotFoundError(
                cutoff_year
            )

        return cutoff_year

    def list_communities(
        self,
        cutoff_year: int | None = None,
    ) -> dict[str, Any]:
        cutoff = self._resolve_cutoff(
            cutoff_year
        )

        frame = self._communities.loc[
            self._communities[
                "cutoff_year"
            ] == cutoff
        ].copy()

        frame = frame.sort_values(
            by=[
                "historical_breaks_per_km",
                "historical_break_count",
                "community_id",
            ],
            ascending=[
                False,
                False,
                True,
            ],
            na_position="last",
        )

        return {
            "cutoff_year": cutoff,
            "items": _records(frame),
        }

    def geojson(
        self,
        cutoff_year: int | None = None,
    ) -> dict[str, Any]:
        cutoff = self._resolve_cutoff(
            cutoff_year
        )

        return self._geojson_by_cutoff[
            cutoff
        ]

    def validation(
        self,
    ) -> list[dict[str, Any]]:
        if not self.loaded:
            raise CommunityArtifactsUnavailableError(
                "Community artifacts are missing or failed validation."
            )

        return _records(
            self._validation
        )