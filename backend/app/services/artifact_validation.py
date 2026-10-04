"""Read raw artifact files and validate them against docs/ARTIFACT_SCHEMAS.md.

Shared by the API loader and scripts/validate_artifacts.py. Never raises on bad input:
problems are returned as human-readable error strings. No ranking/scoring logic lives here.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from shapely import wkt as shapely_wkt

from app.core import constants as c

MAX_ROW_ERRORS = 5


@dataclass
class RawArtifacts:
    plan_v1: pd.DataFrame
    plan_v2: pd.DataFrame
    baseline: pd.DataFrame
    validation_results: pd.DataFrame
    rank_changes: pd.DataFrame
    escalation: pd.DataFrame
    not_covered: pd.DataFrame
    agent_log: list[dict[str, Any]]
    audit_summary: dict[str, Any]
    data_quality: dict[str, Any]


# --------------------------------------------------------------------------- helpers


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1")
    if value is None or pd.isna(value):
        return False
    return bool(value)


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report any parse problem
        errors.append(f"{path.name}: cannot parse JSON ({exc})")
        return None
    if not isinstance(obj, dict):
        errors.append(f"{path.name}: top-level JSON value must be an object")
        return None
    return obj


def _read_jsonl(path: Path, errors: list[str]) -> list[dict[str, Any]] | None:
    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path.name}: cannot read ({exc})")
        return None
    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path.name}: line {i} is not valid JSON ({exc})")
            return None
        if not isinstance(obj, dict):
            errors.append(f"{path.name}: line {i} must be a JSON object")
            return None
        rows.append(obj)
    return rows


def _read_csv(path: Path, errors: list[str]) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path.name}: cannot parse CSV ({exc})")
        return None


def _read_parquet(path: Path, errors: list[str]) -> pd.DataFrame | None:
    try:
        return pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path.name}: cannot parse parquet ({exc})")
        return None


def _missing_columns(df: pd.DataFrame, required: tuple[str, ...], name: str, errors: list[str]):
    missing = [col for col in required if col not in df.columns]
    if missing:
        errors.append(f"{name}: missing required columns {missing}")
        return False
    return True


def _check_enum(
    df: pd.DataFrame, column: str, allowed: tuple[str, ...], name: str, errors: list[str]
) -> None:
    bad = sorted({str(v) for v in df[column].dropna().unique() if v not in allowed})
    if bad:
        errors.append(f"{name}: column '{column}' has values outside {list(allowed)}: {bad}")
    if df[column].isna().any():
        errors.append(f"{name}: column '{column}' must not contain nulls")


def _check_keys(obj: dict[str, Any], required: tuple[str, ...], name: str, errors: list[str]):
    missing = [k for k in required if k not in obj]
    if missing:
        errors.append(f"{name}: missing required keys {missing}")
        return False
    return True


# --------------------------------------------------------------------------- per-file checks


def _check_plan(df: pd.DataFrame, name: str, errors: list[str]) -> None:
    if not _missing_columns(df, c.PLAN_COLUMNS, name, errors):
        return
    n = len(df)
    if n == 0:
        errors.append(f"{name}: plan has no rows")
        return
    if df["asset_id"].duplicated().any():
        dups = df.loc[df["asset_id"].duplicated(), "asset_id"].head(MAX_ROW_ERRORS).tolist()
        errors.append(f"{name}: duplicate asset_id values, e.g. {dups}")
    ranks = pd.to_numeric(df["rank"], errors="coerce")
    if ranks.isna().any() or sorted(ranks.tolist()) != list(range(1, n + 1)):
        errors.append(f"{name}: ranks must be unique and exactly 1..{n}")
    _check_enum(df, "evidence_confidence", c.EVIDENCE_CONFIDENCE, name, errors)
    bad_geoms = 0
    for asset_id, geom in zip(df["asset_id"], df["geometry_wkt"], strict=True):
        try:
            parsed = shapely_wkt.loads(geom)
            ok = parsed.geom_type in ("LineString", "MultiLineString") and not parsed.is_empty
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            bad_geoms += 1
            if bad_geoms <= MAX_ROW_ERRORS:
                errors.append(
                    f"{name}: asset '{asset_id}' geometry_wkt is not a valid "
                    "LineString/MultiLineString"
                )
    if bad_geoms > MAX_ROW_ERRORS:
        errors.append(f"{name}: {bad_geoms} invalid geometries in total")


def _physical_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.loc[:, list(c.PHYSICAL_COLUMNS)].copy()
    out["source_segment_ids"] = out["source_segment_ids"].map(
        lambda v: tuple(str(x) for x in v) if v is not None else ()
    )
    return out.sort_values("asset_id").reset_index(drop=True)


def _check_plan_pair(v1: pd.DataFrame, v2: pd.DataFrame, errors: list[str]) -> None:
    if not set(c.PLAN_COLUMNS).issubset(v1.columns) or not set(c.PLAN_COLUMNS).issubset(v2.columns):
        return
    if v1["asset_id"].duplicated().any() or v2["asset_id"].duplicated().any():
        return  # already reported
    ids1, ids2 = set(v1["asset_id"]), set(v2["asset_id"])
    if ids1 != ids2:
        only1 = sorted(ids1 - ids2)[:MAX_ROW_ERRORS]
        only2 = sorted(ids2 - ids1)[:MAX_ROW_ERRORS]
        errors.append(
            f"plan_v1/plan_v2: asset_id sets differ (only in v1: {only1}, only in v2: {only2})"
        )
        return
    p1, p2 = _physical_frame(v1), _physical_frame(v2)
    for col in c.PHYSICAL_COLUMNS:
        if not p1[col].equals(p2[col]):
            errors.append(f"plan_v1/plan_v2: physical column '{col}' differs between plans")


def _check_baseline(df: pd.DataFrame, errors: list[str]) -> None:
    name = c.BASELINE_FILE
    if not _missing_columns(df, c.BASELINE_COLUMNS, name, errors):
        return
    _check_enum(df, "baseline_name", c.BASELINE_IDS, name, errors)


def _check_validation_results(df: pd.DataFrame, errors: list[str]) -> None:
    name = c.VALIDATION_RESULTS_FILE
    if not _missing_columns(df, c.VALIDATION_RESULTS_COLUMNS, name, errors):
        return
    _check_enum(df, "split", c.SPLITS, name, errors)
    _check_enum(df, "policy_type", c.POLICY_TYPES, name, errors)
    _check_enum(df, "policy_id", c.POLICY_IDS + c.BASELINE_IDS, name, errors)
    organizer = df[df["policy_id"] == c.ORGANIZER_CELL_ID]
    if organizer["asset_capture"].notna().any():
        errors.append(f"{name}: organizer_cell rows must have null asset_capture")


def _check_rank_changes(df: pd.DataFrame, errors: list[str]) -> None:
    name = c.RANK_CHANGES_FILE
    if not _missing_columns(df, c.RANK_CHANGES_COLUMNS, name, errors):
        return
    demo_rows = int(df["show_in_demo"].map(_truthy).sum())
    if demo_rows < c.MIN_DEMO_RANK_CHANGES:
        errors.append(
            f"{name}: at least {c.MIN_DEMO_RANK_CHANGES} rows need show_in_demo=true "
            f"(found {demo_rows})"
        )


def _check_escalation(df: pd.DataFrame, errors: list[str]) -> None:
    name = c.ESCALATION_FILE
    if _missing_columns(df, c.ESCALATION_COLUMNS, name, errors):
        _check_enum(df, "evidence_confidence", c.EVIDENCE_CONFIDENCE, name, errors)


def _check_agent_log(rows: list[dict[str, Any]], errors: list[str]) -> None:
    name = c.AGENT_LOG_FILE
    seqs: list[Any] = []
    for i, row in enumerate(rows, start=1):
        if not _check_keys(row, c.AGENT_LOG_KEYS, f"{name} line {i}", errors):
            continue
        seqs.append(row["seq"])
        if row["event_type"] not in c.AUDIT_EVENT_TYPES:
            errors.append(f"{name} line {i}: unknown event_type '{row['event_type']}'")
        if row["event_type"] in c.CANDIDATE_EVENT_TYPES:
            cand = row["candidate"]
            if not isinstance(cand, dict):
                errors.append(f"{name} line {i}: {row['event_type']} requires a non-null candidate")
                continue
            if _check_keys(cand, c.CANDIDATE_KEYS, f"{name} line {i} candidate", errors) and (
                cand["decision"] not in c.CANDIDATE_DECISIONS
            ):
                errors.append(f"{name} line {i}: candidate decision '{cand['decision']}' invalid")
    if len(set(map(str, seqs))) != len(seqs):
        errors.append(f"{name}: seq values must be unique")


def _check_audit_summary(obj: dict[str, Any], errors: list[str]) -> None:
    name = c.AUDIT_SUMMARY_FILE
    if not _check_keys(obj, c.AUDIT_SUMMARY_KEYS, name, errors):
        return
    if not isinstance(obj["synthetic"], bool):
        errors.append(f"{name}: 'synthetic' must be a boolean")
    if not isinstance(obj["config_hash"], str) or not obj["config_hash"].strip():
        errors.append(f"{name}: 'config_hash' must be a non-empty string")
    for key in ("selected_policy_id", "v1_policy_id"):
        if obj[key] not in c.POLICY_IDS:
            errors.append(f"{name}: '{key}' must be one of {list(c.POLICY_IDS)}")
    if not isinstance(obj["revision_gate"], dict):
        errors.append(f"{name}: 'revision_gate' must be an object")
    else:
        _check_keys(obj["revision_gate"], c.REVISION_GATE_KEYS, f"{name} revision_gate", errors)
    if not isinstance(obj["final_test"], dict):
        errors.append(f"{name}: 'final_test' must be an object")
    else:
        _check_keys(obj["final_test"], c.FINAL_TEST_KEYS, f"{name} final_test", errors)


def _check_data_quality(obj: dict[str, Any], errors: list[str]) -> None:
    name = c.DATA_QUALITY_FILE
    missing = [k for k in c.DATA_QUALITY_KEYS if k not in obj]
    extra = [k for k in obj if k not in c.DATA_QUALITY_KEYS]
    if missing:
        errors.append(f"{name}: missing required keys {missing}")
    if extra:
        errors.append(f"{name}: unexpected keys {extra}")


# --------------------------------------------------------------------------- public API


def read_and_validate(artifact_dir: Path) -> tuple[RawArtifacts | None, list[str]]:
    """Read all artifact files. Returns (raw or None, errors); raw is None if any error."""
    artifact_dir = Path(artifact_dir)
    errors: list[str] = []

    if not artifact_dir.is_dir():
        return None, [f"artifact directory not found: {artifact_dir}"]

    missing_files = [f for f in c.ARTIFACT_FILES if not (artifact_dir / f).is_file()]
    for f in missing_files:
        errors.append(f"{f}: file is missing")

    def path(name: str) -> Path:
        return artifact_dir / name

    def present(name: str) -> bool:
        return name not in missing_files

    plan_v1 = _read_parquet(path(c.PLAN_V1_FILE), errors) if present(c.PLAN_V1_FILE) else None
    plan_v2 = _read_parquet(path(c.PLAN_V2_FILE), errors) if present(c.PLAN_V2_FILE) else None
    baseline = _read_parquet(path(c.BASELINE_FILE), errors) if present(c.BASELINE_FILE) else None
    validation = (
        _read_csv(path(c.VALIDATION_RESULTS_FILE), errors)
        if present(c.VALIDATION_RESULTS_FILE)
        else None
    )
    rank_changes = (
        _read_csv(path(c.RANK_CHANGES_FILE), errors) if present(c.RANK_CHANGES_FILE) else None
    )
    escalation = _read_csv(path(c.ESCALATION_FILE), errors) if present(c.ESCALATION_FILE) else None
    not_covered = (
        _read_csv(path(c.NOT_COVERED_FILE), errors) if present(c.NOT_COVERED_FILE) else None
    )
    agent_log = _read_jsonl(path(c.AGENT_LOG_FILE), errors) if present(c.AGENT_LOG_FILE) else None
    audit_summary = (
        _read_json(path(c.AUDIT_SUMMARY_FILE), errors) if present(c.AUDIT_SUMMARY_FILE) else None
    )
    data_quality = (
        _read_json(path(c.DATA_QUALITY_FILE), errors) if present(c.DATA_QUALITY_FILE) else None
    )

    if plan_v1 is not None:
        _check_plan(plan_v1, c.PLAN_V1_FILE, errors)
    if plan_v2 is not None:
        _check_plan(plan_v2, c.PLAN_V2_FILE, errors)
    if plan_v1 is not None and plan_v2 is not None:
        _check_plan_pair(plan_v1, plan_v2, errors)
    if baseline is not None:
        _check_baseline(baseline, errors)
    if validation is not None:
        _check_validation_results(validation, errors)
    if rank_changes is not None:
        _check_rank_changes(rank_changes, errors)
    if escalation is not None:
        _check_escalation(escalation, errors)
    if not_covered is not None:
        _missing_columns(not_covered, c.NOT_COVERED_COLUMNS, c.NOT_COVERED_FILE, errors)
    if agent_log is not None:
        _check_agent_log(agent_log, errors)
    if audit_summary is not None:
        _check_audit_summary(audit_summary, errors)
    if data_quality is not None:
        _check_data_quality(data_quality, errors)

    if errors:
        return None, errors

    assert plan_v1 is not None and plan_v2 is not None and baseline is not None
    assert validation is not None and rank_changes is not None and escalation is not None
    assert not_covered is not None and agent_log is not None
    assert audit_summary is not None and data_quality is not None
    raw = RawArtifacts(
        plan_v1=plan_v1,
        plan_v2=plan_v2,
        baseline=baseline,
        validation_results=validation,
        rank_changes=rank_changes,
        escalation=escalation,
        not_covered=not_covered,
        agent_log=agent_log,
        audit_summary=audit_summary,
        data_quality=data_quality,
    )
    return raw, []


def artifact_warnings(raw: RawArtifacts) -> list[str]:
    """Non-fatal warnings (synthetic / placeholder data)."""
    warnings: list[str] = []
    if raw.audit_summary.get("synthetic") is True:
        warnings.append("audit_summary.json: synthetic=true - artifacts are SYNTHETIC DATA")
    if raw.audit_summary.get("config_hash") == c.PLACEHOLDER_CONFIG_HASH:
        warnings.append(
            f"audit_summary.json: config_hash is {c.PLACEHOLDER_CONFIG_HASH} - config not frozen"
        )
    return warnings
