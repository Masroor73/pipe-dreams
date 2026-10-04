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

from app.core import constants as c
from app.core.settings import REPO_ROOT
from app.services.artifact_validation import RawArtifacts, read_and_validate

logger = logging.getLogger(__name__)

BOOL_COLUMNS = ("selected", "show_in_demo", "accepted_vs_v1")


class AssetNotFoundError(Exception):
    def __init__(self, asset_id: str, plan: str = "v2") -> None:
        super().__init__(asset_id)
        self.asset_id = asset_id
        self.plan = plan


class ArtifactsUnavailableError(Exception):
    pass


def _clean(value: Any) -> Any:
    """Convert numpy/pandas scalars to plain Python; NaN/NaT/NA -> None."""
    if value is None:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return None if math.isnan(f) else f
    if isinstance(value, str):
        return value
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_clean(v) for v in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _to_bool(value: Any) -> bool | None:
    value = _clean(value)
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1")
    return bool(value)


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        rec = {str(k): _clean(v) for k, v in row.items()}
        for col in BOOL_COLUMNS:
            if col in rec:
                rec[col] = _to_bool(rec[col])
        out.append(rec)
    return out


def _tuples_to_lists(value: Any) -> Any:
    if isinstance(value, (tuple, list)):
        return [_tuples_to_lists(v) for v in value]
    if isinstance(value, dict):
        return {k: _tuples_to_lists(v) for k, v in value.items()}
    return value


def _geojson(geometry_wkt: str) -> dict[str, Any]:
    return _tuples_to_lists(mapping(wkt.loads(geometry_wkt)))


def _display_dir(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _num(value: Any) -> float:
    """Sort helper: null scores sort last when descending."""
    return float("-inf") if value is None else float(value)


class ArtifactService:
    def __init__(self, artifact_dir: Path) -> None:
        self.artifact_dir = Path(artifact_dir)
        self.display_dir = _display_dir(self.artifact_dir)
        self.errors: list[str] = []
        self.loaded = False
        self.meta: dict[str, Any] | None = None
        try:
            raw, errors = read_and_validate(self.artifact_dir)
            self.errors = list(errors)
            if raw is not None and not self.errors:
                self._build(raw)
                self.loaded = True
        except Exception as exc:  # noqa: BLE001 - never raise at construction
            self.errors.append(f"unexpected error while loading artifacts: {exc!r}")
            self.loaded = False

    # ------------------------------------------------------------------ build
    def _build(self, raw: RawArtifacts) -> None:
        summary = raw.audit_summary
        self.meta = {
            "synthetic": bool(summary["synthetic"]),
            "config_hash": str(summary["config_hash"]),
        }
        self._summary = _clean(summary)

        # Geometry is converted once per asset (shared by v1 and v2).
        self._geometry: dict[str, dict[str, Any]] = {}
        self._plans: dict[str, list[dict[str, Any]]] = {}
        for plan_id, df in (("v1", raw.plan_v1), ("v2", raw.plan_v2)):
            records: list[dict[str, Any]] = []
            for row in df.sort_values("rank").to_dict(orient="records"):
                rec = {k: _clean(v) for k, v in row.items() if k != "geometry_wkt"}
                rec["selected"] = _to_bool(rec["selected"])
                ids = row["source_segment_ids"]
                rec["source_segment_ids"] = [str(x) for x in (ids if ids is not None else [])]
                if rec["asset_id"] not in self._geometry:
                    self._geometry[rec["asset_id"]] = _geojson(row["geometry_wkt"])
                records.append(rec)
            self._plans[plan_id] = records
        self._index: dict[str, dict[str, dict[str, Any]]] = {
            pid: {r["asset_id"]: r for r in recs} for pid, recs in self._plans.items()
        }

        self._rank_changes = _records(raw.rank_changes)
        self._rank_change_by_asset = {r["asset_id"]: r for r in self._rank_changes}
        self._series = _records(raw.validation_results)
        self._events = sorted((_clean(e) for e in raw.agent_log), key=lambda e: e["seq"])
        self._escalations = _records(raw.escalation)
        self._not_covered = _records(raw.not_covered)
        self._data_quality = _clean(raw.data_quality)

    # --------------------------------------------------------------- accessors
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.loaded else "degraded",
            "artifacts_loaded": self.loaded,
            "artifact_dir": self.display_dir,
            "synthetic": self.meta["synthetic"] if self.loaded and self.meta else None,
        }

    def overview(self) -> dict[str, Any]:
        s = self._summary
        return {
            "git_commit": s["git_commit"],
            "git_tag": s["git_tag"],
            "v1_policy_id": s["v1_policy_id"],
            "selected_policy_id": s["selected_policy_id"],
            "v2_equals_v1": s["v2_equals_v1"],
            "final_test_previously_viewed": s["final_test"]["previously_viewed"],
            "budgets_pct": s["budgets_pct"],
            "revision_gate": {k: s["revision_gate"][k] for k in c.REVISION_GATE_KEYS},
            "series": self._series,
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
    ) -> dict[str, Any]:
        rows = self._plans[plan]
        if selected_only:
            rows = [r for r in rows if r["selected"]]
        if evidence_confidence is not None:
            rows = [r for r in rows if r["evidence_confidence"] == evidence_confidence]
        if consequence_tier is not None:
            rows = [r for r in rows if r["consequence_tier"] == consequence_tier]
        if sort == "priority_score":
            rows = sorted(rows, key=lambda r: (-_num(r["priority_score"]), r["rank"]))
        elif sort == "length_m":
            rows = sorted(rows, key=lambda r: (-_num(r["length_m"]), r["rank"]))
        else:
            rows = sorted(rows, key=lambda r: r["rank"])
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
        items = [{k: r[k] for k in fields} for r in rows[offset : offset + limit]]
        return {
            "plan": plan,
            "total": len(rows),
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    def geojson(self, plan: str, selected_only: bool) -> dict[str, Any]:
        features = []
        for r in self._plans[plan]:
            if selected_only and not r["selected"]:
                continue
            features.append(
                {
                    "type": "Feature",
                    "id": r["asset_id"],
                    "geometry": self._geometry[r["asset_id"]],
                    "properties": {
                        "asset_id": r["asset_id"],
                        "rank": r["rank"],
                        "selected": r["selected"],
                        "consequence_tier": r["consequence_tier"],
                        "evidence_confidence": r["evidence_confidence"],
                        "recommended_action": r["recommended_action"],
                    },
                }
            )
        return {"type": "FeatureCollection", "features": features}

    def asset_detail(self, asset_id: str) -> dict[str, Any]:
        v1 = self._index["v1"].get(asset_id)
        v2 = self._index["v2"].get(asset_id)
        if v1 is None or v2 is None:
            raise AssetNotFoundError(asset_id, "v2")
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
        out: dict[str, Any] = {k: v2[k] for k in shared}
        out["geometry"] = self._geometry[asset_id]
        out["v1"] = {k: v1[k] for k in c.PLAN_SPECIFIC_COLUMNS}
        out["v2"] = {k: v2[k] for k in c.PLAN_SPECIFIC_COLUMNS}
        rc = self._rank_change_by_asset.get(asset_id)
        out["rank_change"] = (
            None
            if rc is None
            else {k: rc[k] for k in ("delta_rank", "reason_1", "reason_2", "show_in_demo")}
        )
        return out

    def rank_changes(self, demo_only: bool, limit: int) -> dict[str, Any]:
        rows = self._rank_changes
        if demo_only:
            rows = [r for r in rows if r["show_in_demo"]]
        return {"items": rows[:limit]}

    def audit(self) -> dict[str, Any]:
        return {"events": self._events}

    def escalations(self) -> dict[str, Any]:
        return {"items": self._escalations}

    def not_covered(self) -> dict[str, Any]:
        return {"items": self._not_covered}

    def data_quality(self) -> dict[str, Any]:
        return self._data_quality
