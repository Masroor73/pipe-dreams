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

ASSET_COMMUNITY_ASSIGNMENTS_FILE = (
    "asset_community_assignments.csv"
)

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

ASSET_COMMUNITY_ASSIGNMENT_COLUMNS = (
    "asset_id",
    "community_id",
    "overlap_length_m",
    "asset_length_m",
    "overlap_share",
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

    def __init__(
        self,
        cutoff_year: int,
    ) -> None:
        super().__init__(
            str(cutoff_year)
        )
        self.cutoff_year = cutoff_year


class CommunityNotFoundError(Exception):
    """Raised when a requested community id is not available."""

    def __init__(
        self,
        community_id: str,
    ) -> None:
        super().__init__(
            community_id
        )
        self.community_id = community_id


def _clean(
    value: Any,
) -> Any:
    """Convert pandas/numpy values to JSON-safe plain Python values."""

    if value is None:
        return None

    if isinstance(
        value,
        (np.bool_, bool),
    ):
        return bool(value)

    if isinstance(
        value,
        np.integer,
    ):
        return int(value)

    if isinstance(
        value,
        (np.floating, float),
    ):
        number = float(value)
        return (
            None
            if math.isnan(number)
            else number
        )

    if isinstance(
        value,
        str,
    ):
        return value

    try:
        if pd.isna(value):
            return None
    except (
        TypeError,
        ValueError,
    ):
        pass

    return value


def _records(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    return [
        {
            str(key): _clean(value)
            for key, value in row.items()
        }
        for row in df.to_dict(
            orient="records"
        )
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
        isinstance(
            value,
            float,
        )
        and math.isnan(value)
    ):
        return []

    if isinstance(
        value,
        list,
    ):
        return [
            str(item)
            for item in value
        ]

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            "data_quality_flags must be a JSON array"
        )

    parsed = json.loads(
        value
    )

    if not isinstance(
        parsed,
        list,
    ):
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
        self.artifact_dir = Path(
            artifact_dir
        )
        self.loaded = False
        self.errors: list[str] = []
        self.available_cutoffs: tuple[
            int,
            ...,
        ] = ()

        self._communities = (
            pd.DataFrame()
        )
        self._validation = (
            pd.DataFrame()
        )
        self._geojson_by_cutoff: dict[
            int,
            dict[str, Any],
        ] = {}

        self.asset_assignments_loaded = False
        self.asset_assignment_errors: list[str] = []
        self._asset_community_assignments = (
            pd.DataFrame()
        )

        self._load()

    def _load(
        self,
    ) -> None:
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
            communities = (
                pd.read_csv(
                    communities_path
                )
            )
        except Exception as exc:
            self.errors.append(
                f"{COMMUNITIES_FILE}: cannot parse CSV ({exc})"
            )
            return

        try:
            validation = (
                pd.read_csv(
                    validation_path
                )
            )
        except Exception as exc:
            self.errors.append(
                f"{COMMUNITY_VALIDATION_FILE}: cannot parse CSV ({exc})"
            )
            return

        missing = (
            _missing_columns(
                communities,
                COMMUNITY_COLUMNS,
            )
        )

        if missing:
            self.errors.append(
                f"{COMMUNITIES_FILE}: missing required columns {missing}"
            )

        missing_validation = (
            _missing_columns(
                validation,
                COMMUNITY_VALIDATION_COLUMNS,
            )
        )

        if missing_validation:
            self.errors.append(
                f"{COMMUNITY_VALIDATION_FILE}: "
                f"missing required columns {missing_validation}"
            )

        if self.errors:
            return

        cutoff_numeric = (
            pd.to_numeric(
                communities[
                    "cutoff_year"
                ],
                errors="coerce",
            )
        )

        if cutoff_numeric.isna().any():
            self.errors.append(
                f"{COMMUNITIES_FILE}: cutoff_year must be numeric"
            )
            return

        communities = (
            communities.copy()
        )
        communities[
            "cutoff_year"
        ] = cutoff_numeric.astype(
            int
        )

        duplicate_mask = (
            communities.duplicated(
                subset=[
                    "community_id",
                    "cutoff_year",
                ],
                keep=False,
            )
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
                ]
                .dropna()
                .unique()
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
            communities[
                "data_quality_flags"
            ] = (
                communities[
                    "data_quality_flags"
                ].map(
                    _decode_flags
                )
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

            if not isinstance(
                obj,
                dict,
            ):
                self.errors.append(
                    f"{path.name}: "
                    "top-level JSON value must be an object"
                )
                continue

            if (
                obj.get("type")
                != "FeatureCollection"
            ):
                self.errors.append(
                    f"{path.name}: "
                    "type must be FeatureCollection"
                )
                continue

            features = (
                obj.get(
                    "features"
                )
            )

            if not isinstance(
                features,
                list,
            ):
                self.errors.append(
                    f"{path.name}: "
                    "features must be an array"
                )
                continue

            try:
                for feature in features:
                    if not isinstance(
                        feature,
                        dict,
                    ):
                        raise ValueError(
                            "feature must be an object"
                        )

                    properties = (
                        feature.get(
                            "properties"
                        )
                    )

                    if not isinstance(
                        properties,
                        dict,
                    ):
                        raise ValueError(
                            "feature properties must be an object"
                        )

                    properties[
                        "data_quality_flags"
                    ] = _decode_flags(
                        properties.get(
                            "data_quality_flags"
                        )
                    )
            except Exception as exc:
                self.errors.append(
                    f"{path.name}: "
                    f"invalid data_quality_flags ({exc})"
                )
                continue

            geojson_by_cutoff[
                int(
                    cutoff_year
                )
            ] = obj

        if self.errors:
            return

        self._communities = (
            communities
        )
        self._validation = (
            validation
        )
        self._geojson_by_cutoff = (
            geojson_by_cutoff
        )
        self.available_cutoffs = (
            cutoffs
        )
        self.loaded = True

        self._load_asset_community_assignments()

    def _load_asset_community_assignments(
        self,
    ) -> None:
        path = (
            self.artifact_dir
            / ASSET_COMMUNITY_ASSIGNMENTS_FILE
        )

        # The asset-to-community mapping is optional even when the
        # community artifacts themselves are available. A missing or
        # invalid mapping must not disable the existing community API.
        if not path.is_file():
            return

        try:
            assignments = (
                pd.read_csv(
                    path
                )
            )
        except Exception as exc:
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                f"cannot parse CSV ({exc})"
            )
            return

        missing = (
            _missing_columns(
                assignments,
                ASSET_COMMUNITY_ASSIGNMENT_COLUMNS,
            )
        )

        if missing:
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                f"missing required columns {missing}"
            )
            return

        assignments = (
            assignments.loc[
                :,
                list(
                    ASSET_COMMUNITY_ASSIGNMENT_COLUMNS
                ),
            ].copy()
        )

        if assignments.empty:
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                "file contains no assignment rows"
            )
            return

        if assignments[
            "asset_id"
        ].isna().any():
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                "asset_id must not contain nulls"
            )
            return

        if assignments[
            "community_id"
        ].isna().any():
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                "community_id must not contain nulls"
            )
            return

        assignments[
            "asset_id"
        ] = assignments[
            "asset_id"
        ].astype(
            str
        )

        assignments[
            "community_id"
        ] = assignments[
            "community_id"
        ].astype(
            str
        )

        empty_asset_ids = (
            assignments[
                "asset_id"
            ].str.strip()
            == ""
        )

        if empty_asset_ids.any():
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                "asset_id must not contain empty values"
            )
            return

        empty_community_ids = (
            assignments[
                "community_id"
            ].str.strip()
            == ""
        )

        if empty_community_ids.any():
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                "community_id must not contain empty values"
            )
            return

        duplicate_mask = (
            assignments.duplicated(
                subset=[
                    "asset_id",
                    "community_id",
                ],
                keep=False,
            )
        )

        if duplicate_mask.any():
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                "duplicate (asset_id, community_id) rows"
            )
            return

        numeric_columns = (
            "overlap_length_m",
            "asset_length_m",
            "overlap_share",
        )

        for column in numeric_columns:
            numeric = (
                pd.to_numeric(
                    assignments[
                        column
                    ],
                    errors="coerce",
                )
            )

            if numeric.isna().any():
                self.asset_assignment_errors.append(
                    f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                    f"{column} must be numeric"
                )
                return

            values = (
                numeric.to_numpy(
                    dtype=float
                )
            )

            if not np.isfinite(
                values
            ).all():
                self.asset_assignment_errors.append(
                    f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                    f"{column} must contain only finite values"
                )
                return

            assignments[
                column
            ] = numeric

        if (
            assignments[
                "overlap_length_m"
            ]
            < 0
        ).any():
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                "overlap_length_m must be nonnegative"
            )
            return

        if (
            assignments[
                "asset_length_m"
            ]
            <= 0
        ).any():
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                "asset_length_m must be greater than zero"
            )
            return

        if (
            assignments[
                "overlap_length_m"
            ]
            > assignments[
                "asset_length_m"
            ]
        ).any():
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                "overlap_length_m must not exceed "
                "asset_length_m"
            )
            return

        bad_share = (
            (
                assignments[
                    "overlap_share"
                ]
                < 0
            )
            | (
                assignments[
                    "overlap_share"
                ]
                > 1
            )
        )

        if bad_share.any():
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                "overlap_share must be between 0 and 1"
            )
            return

        known_community_ids = set(
            self._communities[
                "community_id"
            ].astype(
                str
            )
        )

        unknown_community_ids = sorted(
            set(
                assignments[
                    "community_id"
                ]
            )
            - known_community_ids
        )

        if unknown_community_ids:
            self.asset_assignment_errors.append(
                f"{ASSET_COMMUNITY_ASSIGNMENTS_FILE}: "
                "contains unknown community_id values "
                f"{unknown_community_ids[:5]}"
            )
            return

        self._asset_community_assignments = (
            assignments
        )
        self.asset_assignments_loaded = True

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
            return (
                self.available_cutoffs[
                    -1
                ]
            )

        if (
            cutoff_year
            not in self.available_cutoffs
        ):
            raise (
                CommunityCutoffNotFoundError(
                    cutoff_year
                )
            )

        return cutoff_year

    def list_communities(
        self,
        cutoff_year: int | None = None,
    ) -> dict[str, Any]:
        cutoff = (
            self._resolve_cutoff(
                cutoff_year
            )
        )

        frame = (
            self._communities.loc[
                self._communities[
                    "cutoff_year"
                ]
                == cutoff
            ].copy()
        )

        frame = (
            frame.sort_values(
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
        )

        item_columns = [
            "community_id",
            "community_name",
            "pipe_length_km",
            "historical_break_count",
            "historical_breaks_per_km",
            "population",
            "equity_index",
            "equity_geography_status",
            "data_quality_flags",
        ]

        return {
            "cutoff_year": cutoff,
            "items": _records(
                frame[
                    item_columns
                ]
            ),
        }

    def geojson(
        self,
        cutoff_year: int | None = None,
    ) -> dict[str, Any]:
        cutoff = (
            self._resolve_cutoff(
                cutoff_year
            )
        )

        geojson = (
            self._geojson_by_cutoff[
                cutoff
            ]
        )

        features = []

        for feature in geojson[
            "features"
        ]:
            properties = dict(
                feature.get(
                    "properties",
                    {}
                )
            )

            properties.pop(
                "cutoff_year",
                None,
            )

            features.append(
                {
                    **feature,
                    "properties": properties,
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    def asset_ids_for_community(
        self,
        community_id: str,
    ) -> set[str]:
        if not self.loaded:
            raise CommunityArtifactsUnavailableError(
                "Community artifacts are missing "
                "or failed validation."
            )

        community_id = str(
            community_id
        )

        known_community_ids = set(
            self._communities[
                "community_id"
            ].astype(
                str
            )
        )

        if (
            community_id
            not in known_community_ids
        ):
            raise CommunityNotFoundError(
                community_id
            )

        if not self.asset_assignments_loaded:
            raise CommunityArtifactsUnavailableError(
                "Asset-community assignments are "
                "missing or failed validation."
            )

        rows = (
            self._asset_community_assignments.loc[
                self._asset_community_assignments[
                    "community_id"
                ]
                == community_id
            ]
        )

        return set(
            rows[
                "asset_id"
            ].astype(
                str
            )
        )

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