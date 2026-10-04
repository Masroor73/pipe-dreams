"""Load validated artifacts once and expose read-only accessors.

Pass-through only: reshaping, filtering, sorting and paging. No scoring or ranking.
"""

import logging
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from shapely import wkt
from shapely.geometry import mapping
from shapely.ops import transform as shapely_transform

try:
    from pyproj import Transformer
except ImportError:  # pragma: no cover - optional until installed everywhere
    Transformer = None

from app.core import constants as c
from app.core.settings import REPO_ROOT
from app.services.artifact_validation import (
    RawArtifacts,
    read_and_validate,
)

logger = logging.getLogger(__name__)

BOOL_COLUMNS = (
    "selected",
    "show_in_demo",
    "accepted_vs_v1",
)


class AssetNotFoundError(Exception):
    def __init__(
        self,
        asset_id: str,
        plan: str = "v2",
    ) -> None:
        super().__init__(
            asset_id
        )
        self.asset_id = asset_id
        self.plan = plan


class ArtifactsUnavailableError(Exception):
    pass


def _clean(
    value: Any,
) -> Any:
    """Convert numpy/pandas scalars to plain Python; NaN/NaT/NA -> None."""

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

    if isinstance(
        value,
        pd.Timestamp,
    ):
        return value.isoformat()

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): _clean(item)
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            np.ndarray,
        ),
    ):
        return [
            _clean(item)
            for item in value
        ]

    try:
        if pd.isna(value):
            return None
    except (
        TypeError,
        ValueError,
    ):
        pass

    return value


def _to_bool(
    value: Any,
) -> bool | None:
    value = _clean(
        value
    )

    if (
        value is None
        or isinstance(
            value,
            bool,
        )
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        return (
            value.strip().lower()
            in (
                "true",
                "1",
            )
        )

    return bool(
        value
    )


def _records(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    out: list[
        dict[str, Any]
    ] = []

    for row in df.to_dict(
        orient="records"
    ):
        rec = {
            str(key): _clean(value)
            for key, value
            in row.items()
        }

        for column in BOOL_COLUMNS:
            if column in rec:
                rec[
                    column
                ] = _to_bool(
                    rec[
                        column
                    ]
                )

        out.append(
            rec
        )

    return out


def _tuples_to_lists(
    value: Any,
) -> Any:
    if isinstance(
        value,
        (
            tuple,
            list,
        ),
    ):
        return [
            _tuples_to_lists(item)
            for item in value
        ]

    if isinstance(
        value,
        dict,
    ):
        return {
            key: _tuples_to_lists(
                item
            )
            for key, item
            in value.items()
        }

    return value


_TO_WGS84 = (
    Transformer.from_crs(
        c.ENGINE_PROJECTED_CRS,
        "EPSG:4326",
        always_xy=True,
    )
    if Transformer is not None
    else None
)


def _to_wgs84(geom):
    """Serve WGS84 lon/lat as the contract requires.

    Real artifacts store geometry in the engine's projected CRS (metres).
    Geometry already in lon/lat is returned unchanged.
    """
    min_x, min_y, max_x, max_y = geom.bounds
    if max(abs(min_x), abs(max_x)) <= 180 and max(abs(min_y), abs(max_y)) <= 90:
        return geom
    if _TO_WGS84 is None:
        return geom
    return shapely_transform(_TO_WGS84.transform, geom)


def _geojson(
    geometry_wkt: str,
) -> dict[str, Any]:
    return _tuples_to_lists(
        mapping(
            _to_wgs84(
                wkt.loads(
                    geometry_wkt
                )
            )
        )
    )


def _display_dir(
    path: Path,
) -> str:
    resolved = (
        path.resolve()
    )

    try:
        return (
            resolved
            .relative_to(
                REPO_ROOT
            )
            .as_posix()
        )
    except ValueError:
        return (
            resolved
            .as_posix()
        )


def _num(
    value: Any,
) -> float:
    """Sort helper: null scores sort last when descending."""

    return (
        float("-inf")
        if value is None
        else float(
            value
        )
    )


class ArtifactService:
    def __init__(
        self,
        artifact_dir: Path,
    ) -> None:
        self.artifact_dir = Path(
            artifact_dir
        )
        self.display_dir = (
            _display_dir(
                self.artifact_dir
            )
        )
        self.errors: list[str] = []
        self.loaded = False
        self.meta: (
            dict[str, Any]
            | None
        ) = None

        try:
            raw, errors = (
                read_and_validate(
                    self.artifact_dir
                )
            )

            self.errors = list(
                errors
            )

            if (
                raw is not None
                and not self.errors
            ):
                self._build(
                    raw
                )
                self.loaded = True

        except Exception as exc:
            # Never raise during construction.
            self.errors.append(
                "unexpected error while loading artifacts: "
                f"{exc!r}"
            )
            self.loaded = False

    # ------------------------------------------------------------------ build

    def _build(
        self,
        raw: RawArtifacts,
    ) -> None:
        summary = (
            raw.audit_summary
        )

        self.meta = {
            "synthetic": bool(
                summary[
                    "synthetic"
                ]
            ),
            "config_hash": str(
                summary[
                    "config_hash"
                ]
            ),
        }

        self._summary = (
            _clean(
                summary
            )
        )

        # Geometry is converted once per asset
        # and shared by v1 and v2.
        self._geometry: dict[
            str,
            dict[str, Any],
        ] = {}

        self._plans: dict[
            str,
            list[
                dict[str, Any]
            ],
        ] = {}

        for plan_id, df in (
            (
                "v1",
                raw.plan_v1,
            ),
            (
                "v2",
                raw.plan_v2,
            ),
        ):
            records: list[
                dict[str, Any]
            ] = []

            for row in (
                df.sort_values(
                    "rank"
                )
                .to_dict(
                    orient="records"
                )
            ):
                rec = {
                    key: _clean(
                        value
                    )
                    for key, value
                    in row.items()
                    if key
                    != "geometry_wkt"
                }

                rec[
                    "selected"
                ] = _to_bool(
                    rec[
                        "selected"
                    ]
                )

                ids = row[
                    "source_segment_ids"
                ]

                rec[
                    "source_segment_ids"
                ] = [
                    str(item)
                    for item
                    in (
                        ids
                        if ids is not None
                        else []
                    )
                ]

                if (
                    rec[
                        "asset_id"
                    ]
                    not in self._geometry
                ):
                    self._geometry[
                        rec[
                            "asset_id"
                        ]
                    ] = _geojson(
                        row[
                            "geometry_wkt"
                        ]
                    )

                records.append(
                    rec
                )

            self._plans[
                plan_id
            ] = records

        self._index: dict[
            str,
            dict[
                str,
                dict[str, Any],
            ],
        ] = {
            plan_id: {
                row[
                    "asset_id"
                ]: row
                for row in records
            }
            for plan_id, records
            in self._plans.items()
        }

        self._rank_changes = (
            _records(
                raw.rank_changes
            )
        )

        self._rank_change_by_asset = {
            row[
                "asset_id"
            ]: row
            for row
            in self._rank_changes
        }

        self._series = (
            _records(
                raw.validation_results
            )
        )

        self._events = sorted(
            (
                _clean(event)
                for event
                in raw.agent_log
            ),
            key=lambda event: event[
                "seq"
            ],
        )

        self._escalations = (
            _records(
                raw.escalation
            )
        )

        self._not_covered = (
            _records(
                raw.not_covered
            )
        )

        self._data_quality = (
            _clean(
                raw.data_quality
            )
        )

    # --------------------------------------------------------------- accessors

    def health(
        self,
    ) -> dict[str, Any]:
        return {
            "status": (
                "ok"
                if self.loaded
                else "degraded"
            ),
            "artifacts_loaded": (
                self.loaded
            ),
            "artifact_dir": (
                self.display_dir
            ),
            "synthetic": (
                self.meta[
                    "synthetic"
                ]
                if (
                    self.loaded
                    and self.meta
                )
                else None
            ),
        }

    def overview(
        self,
    ) -> dict[str, Any]:
        summary = (
            self._summary
        )

        return {
            "git_commit": summary[
                "git_commit"
            ],
            "git_tag": summary[
                "git_tag"
            ],
            "v1_policy_id": summary[
                "v1_policy_id"
            ],
            "selected_policy_id": summary[
                "selected_policy_id"
            ],
            "v2_equals_v1": summary[
                "v2_equals_v1"
            ],
            "final_test_previously_viewed": (
                summary[
                    "final_test"
                ][
                    "previously_viewed"
                ]
            ),
            "budgets_pct": summary[
                "budgets_pct"
            ],
            "revision_gate": {
                key: summary[
                    "revision_gate"
                ][
                    key
                ]
                for key
                in c.REVISION_GATE_KEYS
            },
            "series": (
                self._series
            ),
        }

    def list_assets(
        self,
        plan: str,
        selected_only: bool,
        evidence_confidence: str | None,
        consequence_tier: str | None,
        sort: str,
        limit: int,
        offset: int,
        allowed_asset_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        rows = (
            self._plans[
                plan
            ]
        )

        if allowed_asset_ids is not None:
            rows = [
                row
                for row in rows
                if row[
                    "asset_id"
                ]
                in allowed_asset_ids
            ]

        if selected_only:
            rows = [
                row
                for row in rows
                if row[
                    "selected"
                ]
            ]

        if evidence_confidence is not None:
            rows = [
                row
                for row in rows
                if row[
                    "evidence_confidence"
                ]
                == evidence_confidence
            ]

        if consequence_tier is not None:
            rows = [
                row
                for row in rows
                if row[
                    "consequence_tier"
                ]
                == consequence_tier
            ]

        if sort == "priority_score":
            rows = sorted(
                rows,
                key=lambda row: (
                    -_num(
                        row[
                            "priority_score"
                        ]
                    ),
                    row[
                        "rank"
                    ],
                ),
            )

        elif sort == "length_m":
            rows = sorted(
                rows,
                key=lambda row: (
                    -_num(
                        row[
                            "length_m"
                        ]
                    ),
                    row[
                        "rank"
                    ],
                ),
            )

        else:
            rows = sorted(
                rows,
                key=lambda row: row[
                    "rank"
                ],
            )

        fields = (
            "asset_id",
            "rank",
            "selected",
            "length_m",
            "priority_score",
            "consequence_tier",
            "evidence_confidence",
            "recommended_action",
            "latitude",
            "longitude",
        )

        items = [
            {
                key: row[
                    key
                ]
                for key
                in fields
            }
            for row
            in rows[
                offset:
                offset + limit
            ]
        ]

        return {
            "plan": plan,
            "total": len(
                rows
            ),
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    def geojson(
        self,
        plan: str,
        selected_only: bool,
        allowed_asset_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        features = []

        for row in self._plans[
            plan
        ]:
            if (
                allowed_asset_ids is not None
                and row[
                    "asset_id"
                ]
                not in allowed_asset_ids
            ):
                continue

            if (
                selected_only
                and not row[
                    "selected"
                ]
            ):
                continue

            features.append(
                {
                    "type": "Feature",
                    "id": row[
                        "asset_id"
                    ],
                    "geometry": (
                        self._geometry[
                            row[
                                "asset_id"
                            ]
                        ]
                    ),
                    "properties": {
                        "asset_id": row[
                            "asset_id"
                        ],
                        "rank": row[
                            "rank"
                        ],
                        "selected": row[
                            "selected"
                        ],
                        "consequence_tier": row[
                            "consequence_tier"
                        ],
                        "evidence_confidence": row[
                            "evidence_confidence"
                        ],
                        "recommended_action": row[
                            "recommended_action"
                        ],
                    },
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    def asset_detail(
        self,
        asset_id: str,
    ) -> dict[str, Any]:
        v1 = (
            self._index[
                "v1"
            ].get(
                asset_id
            )
        )

        v2 = (
            self._index[
                "v2"
            ].get(
                asset_id
            )
        )

        if (
            v1 is None
            or v2 is None
        ):
            raise AssetNotFoundError(
                asset_id,
                "v2",
            )

        shared = (
            "asset_id",
            "source_segment_ids",
            "length_m",
            "consequence_tier",
            "evidence_confidence",
            "association_quality",
            "rank_stability",
            "evidence_basis",
            "latitude",
            "longitude",
        )

        out: dict[
            str,
            Any,
        ] = {
            key: v2[
                key
            ]
            for key
            in shared
        }

        out[
            "geometry"
        ] = self._geometry[
            asset_id
        ]

        out[
            "v1"
        ] = {
            key: v1[
                key
            ]
            for key
            in c.PLAN_SPECIFIC_COLUMNS
        }

        out[
            "v2"
        ] = {
            key: v2[
                key
            ]
            for key
            in c.PLAN_SPECIFIC_COLUMNS
        }

        rank_change = (
            self._rank_change_by_asset.get(
                asset_id
            )
        )

        out[
            "rank_change"
        ] = (
            None
            if rank_change is None
            else {
                key: rank_change[
                    key
                ]
                for key
                in (
                    "delta_rank",
                    "reason_1",
                    "reason_2",
                    "show_in_demo",
                )
            }
        )

        return out

    def rank_changes(
        self,
        demo_only: bool,
        limit: int,
    ) -> dict[str, Any]:
        rows = (
            self._rank_changes
        )

        if demo_only:
            rows = [
                row
                for row in rows
                if row[
                    "show_in_demo"
                ]
            ]

        return {
            "items": rows[
                :limit
            ]
        }

    def audit(
        self,
    ) -> dict[str, Any]:
        return {
            "events": (
                self._events
            )
        }

    def escalations(
        self,
    ) -> dict[str, Any]:
        return {
            "items": (
                self._escalations
            )
        }

    def not_covered(
        self,
    ) -> dict[str, Any]:
        return {
            "items": (
                self._not_covered
            )
        }

    def data_quality(
        self,
    ) -> dict[str, Any]:
        return (
            self._data_quality
        )