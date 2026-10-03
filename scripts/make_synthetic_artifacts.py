"""Generate deterministic SYNTHETIC artifacts for the Pipe Dreams backend/frontend.

All values are fabricated placeholders. They exist only so the API and UI can be built
against the artifact contract (docs/ARTIFACT_SCHEMAS.md). Nothing here is a real result.

Usage: python scripts/make_synthetic_artifacts.py [--out DIR]
"""

import argparse
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core import constants as c  # noqa: E402

SEED = 20261003
N_ASSETS = 80
CAPACITY_FRACTION = 0.10  # frozen capacity: 10% of network length
GATE_MIN_WINS = 2
GATE_SE_MULTIPLE = 1.0
ORIGINS = ("2013-12-31", "2016-12-31", "2019-12-31")
VALIDATION_POLICIES = ("V1", "C1", "C2", "C3", "C4")
BUDGETS = (1, 2, 5, 10)

M_PER_DEG_LAT = 111_320.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(51.0))

LOW_BASIS = "sparse break history; association needs field verification"
TIER_WEIGHT ={"T1": 1.0, "T2": 0.7, "T3": 0.45}
BASE_CAPTURE = {1: 0.05, 2: 0.10, 5: 0.21, 10: 0.34}
BUDGET_FACTOR = {1: 0.6, 2: 0.8, 5: 1.0, 10: 1.2}
ORIGIN_SCALE = {"2013-12-31": 0.95, "2016-12-31": 1.0, "2019-12-31": 1.05}
POLICY_DELTA = {"V1": 0.0, "C1": -0.005, "C2": 0.015, "C3": -0.012, "C4": 0.004}
CANDIDATE_SE = {"C1": 0.007, "C2": 0.006, "C3": 0.007, "C4": 0.010}
CANDIDATE_DESC = {
    "C1": "history window 2000+",
    "C2": "recency weighting hl10",
    "C3": "per-meter normalization",
    "C4": "joint 2000+ window and hl10",
}


# --------------------------------------------------------------------------- assets


def build_physical(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i in range(N_ASSETS):
        lat0 = 51.0 + rng.uniform(-0.08, 0.08)
        lon0 = -114.1 + rng.uniform(-0.12, 0.12)
        n_vertices = int(rng.integers(2, 5))
        bearing = rng.uniform(0, 2 * math.pi)
        pts = [(lat0, lon0)]
        for _ in range(n_vertices - 1):
            step = rng.uniform(40, 140)
            bearing += rng.normal(0, 0.5)
            lat = pts[-1][0] + step * math.cos(bearing) / M_PER_DEG_LAT
            lon = pts[-1][1] + step * math.sin(bearing) / M_PER_DEG_LON
            pts.append((lat, lon))
        pts = [(round(la, 6), round(lo, 6)) for la, lo in pts]
        length = 0.0
        for (la1, lo1), (la2, lo2) in zip(pts[:-1], pts[1:], strict=True):
            length += math.hypot((la2 - la1) * M_PER_DEG_LAT, (lo2 - lo1) * M_PER_DEG_LON)
        wkt = "LINESTRING (" + ", ".join(f"{lo:.6f} {la:.6f}" for la, lo in pts) + ")"
        tier = str(rng.choice(["T1", "T2", "T3"], p=[0.25, 0.40, 0.35]))
        conf = str(rng.choice(c.EVIDENCE_CONFIDENCE, p=[0.45, 0.35, 0.20]))
        n_breaks = int(rng.integers(1, 7))
        if conf == "HIGH":
            assoc = rng.uniform(0.85, 0.98)
            basis = f"{n_breaks} matched breaks since 2000; nearest-line distance < 5 m"
        elif conf == "MEDIUM":
            assoc = rng.uniform(0.60, 0.85)
            basis = f"{n_breaks} matched breaks; nearest-line distance < 15 m"
        else:
            assoc = rng.uniform(0.30, 0.60)
            basis = LOW_BASIS
        n_src = int(rng.integers(1, 3))
        src = [str(int(rng.integers(10_000, 99_999))) for _ in range(n_src)]
        rows.append(
            {
                "asset_id": f"seg_{i + 1:06d}",
                "source_segment_ids": src,
                "length_m": round(length, 1),
                "consequence_tier": tier,
                "evidence_confidence": conf,
                "association_quality": round(float(assoc), 3),
                "rank_stability": round(float(rng.uniform(0.4, 0.95)), 3),
                "evidence_basis": basis,
                "latitude": round(sum(p[0] for p in pts) / len(pts), 6),
                "longitude": round(sum(p[1] for p in pts) / len(pts), 6),
                "geometry_wkt": wkt,
            }
        )
    df = pd.DataFrame(rows)
    # Guarantee several T1 + LOW_VERIFY assets so escalation is non-trivial.
    forced = [3, 19, 41, 66, 72]
    is_target = (df["consequence_tier"] == "T1") & (df["evidence_confidence"] == "LOW_VERIFY")
    n_have = int(is_target.sum())
    for idx in forced:
        if n_have >= 4:
            break
        if not is_target.iat[idx]:
            df.at[idx, "consequence_tier"] = "T1"
            df.at[idx, "evidence_confidence"] = "LOW_VERIFY"
            df.at[idx, "association_quality"] = 0.45
            df.at[idx, "evidence_basis"] = LOW_BASIS
            n_have += 1
    return df


def recommended_action(conf: str, selected: bool, tier: str) -> str:
    if conf == "LOW_VERIFY":
        return "VERIFY"
    if selected:
        return "CONDITION_ASSESS" if tier == "T1" else "INSPECT"
    return "MONITOR"


def rank_and_select(phys: pd.DataFrame, likelihood: np.ndarray) -> pd.DataFrame:
    df = phys.copy()
    df["likelihood_score"] = np.round(likelihood, 4)
    weights = df["consequence_tier"].map(TIER_WEIGHT)
    df["priority_score"] = np.round(df["likelihood_score"] * weights, 4)
    df = df.sort_values(["priority_score", "asset_id"], ascending=[False, True]).reset_index(
        drop=True
    )
    df["rank"] = np.arange(1, len(df) + 1)
    capacity = CAPACITY_FRACTION * float(df["length_m"].sum())
    df["selected"] = df["length_m"].cumsum() <= capacity
    df["recommended_action"] = [
        recommended_action(cf, bool(sel), t)
        for cf, sel, t in zip(
            df["evidence_confidence"], df["selected"], df["consequence_tier"], strict=True
        )
    ]
    df["revision_reason"] = None
    return df


def build_plans(
    phys: pd.DataFrame, rng: np.random.Generator
) -> tuple[pd.DataFrame, pd.DataFrame]:
    like_v1 = rng.beta(2, 5, size=len(phys)).clip(0.01, 0.99)
    factor = np.exp(rng.normal(0, 0.3, size=len(phys)))
    like_v2 = (like_v1 * factor).clip(0.01, 0.99)
    v1 = rank_and_select(phys, like_v1)
    v2 = rank_and_select(phys, like_v2)
    rank_v1 = dict(zip(v1["asset_id"], v1["rank"], strict=True))
    reasons = []
    for asset_id, r2 in zip(v2["asset_id"], v2["rank"], strict=True):
        r1 = int(rank_v1[asset_id])
        if abs(int(r2) - r1) >= 8:
            reasons.append(f"recent breaks weighted under hl10 (rank {r1} -> {int(r2)})")
        else:
            reasons.append(None)
    v2["revision_reason"] = reasons
    cols = list(c.PLAN_COLUMNS)
    return v1[cols], v2[cols]


# --------------------------------------------------------------------------- baselines


def build_baseline(v1: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    df = v1[["asset_id", "length_m", "latitude", "longitude"]].copy()
    df["score"] = rng.integers(0, 9, size=len(df)).astype(float)
    df = df.sort_values(["score", "asset_id"], ascending=[False, True]).reset_index(drop=True)
    df["rank"] = np.arange(1, len(df) + 1)
    capacity = CAPACITY_FRACTION * float(df["length_m"].sum())
    df["selected"] = df["length_m"].cumsum() <= capacity
    df["baseline_name"] = "count_only"
    count_rows = df[list(c.BASELINE_COLUMNS)]

    cell = v1[["latitude", "longitude"]].copy()
    cell["cell_id"] = [
        f"cell_{math.floor(la * 25) / 25:.2f}_{math.floor(lo * 25) / 25:.2f}"
        for la, lo in zip(cell["latitude"], cell["longitude"], strict=True)
    ]
    cells = cell.groupby("cell_id").size().rename("score").reset_index()
    cells = cells.sort_values(["score", "cell_id"], ascending=[False, True]).reset_index(drop=True)
    cells["rank"] = np.arange(1, len(cells) + 1)
    cells["selected"] = cells["rank"] <= 3
    cells["asset_id"] = cells["cell_id"]
    cells["baseline_name"] = "organizer_cell"
    cells["length_m"] = np.nan
    cells["score"] = cells["score"].astype(float)
    cell_rows = cells[list(c.BASELINE_COLUMNS)]
    return pd.concat([count_rows, cell_rows], ignore_index=True)


# --------------------------------------------------------------------------- validation


def latent(policy: str, scale: float, delta_scale: float, budget: int) -> tuple[float, float]:
    """Return fabricated (asset_capture, event_capture) before noise."""
    base = BASE_CAPTURE[budget] * scale
    if policy == "count_only":
        asset = base * 0.85
    elif policy == "organizer_cell":
        asset = base * 0.70
    else:
        asset = base + POLICY_DELTA[policy] * delta_scale * BUDGET_FACTOR[budget]
    event = asset + 0.03
    return asset, event


def build_validation(rng: np.random.Generator) -> tuple[pd.DataFrame, dict[str, dict]]:
    rows: list[dict] = []
    val_assets: dict[str, dict[str, list[float]]] = {p: {} for p in VALIDATION_POLICIES}

    def add(split, origin, policy, ptype, budget, scale, delta_scale):
        asset, event = latent(policy, scale, delta_scale, budget)
        asset = float(np.clip(asset + rng.normal(0, 0.0015), 0, 1))
        event = float(np.clip(event + rng.normal(0, 0.0015), 0, 1))
        count_asset, count_event = latent("count_only", scale, delta_scale, budget)
        if policy == "organizer_cell":
            lift = event / count_event
        elif policy == "count_only":
            lift = 1.0
        else:
            lift = asset / count_asset
        primary = event if policy == "organizer_cell" else asset
        rows.append(
            {
                "split": split,
                "origin_cutoff": origin,
                "policy_id": policy,
                "policy_type": ptype,
                "budget_pct": budget,
                "asset_capture": None if policy == "organizer_cell" else round(asset, 4),
                "event_capture": round(event, 4),
                "lift_vs_count_only": round(lift, 3),
                "ci_low": round(primary - 0.03, 4),
                "ci_high": round(primary + 0.03, 4),
                "matched_break_share": round(0.80 + 0.08 * float(rng.random()), 3),
                "pooled_gate_score": None,
                "accepted_vs_v1": None,
                "notes": None,
            }
        )
        return rows[-1]

    # validation split
    for origin in ORIGINS:
        scale = ORIGIN_SCALE[origin]
        for policy in VALIDATION_POLICIES:
            for budget in BUDGETS:
                row = add("validation", origin, policy, "policy", budget, scale, 1.0)
                val_assets[policy].setdefault(origin, []).append(row["asset_capture"])
        for baseline in c.BASELINE_IDS:
            for budget in BUDGETS:
                add("validation", origin, baseline, "baseline", budget, scale, 1.0)

    pooled = {
        p: round(float(np.mean([v for vs in per.values() for v in vs])), 4)
        for p, per in val_assets.items()
    }
    for row in rows:
        if row["split"] == "validation" and row["policy_type"] == "policy":
            row["pooled_gate_score"] = pooled[row["policy_id"]]
            if row["policy_id"] == "C2":
                row["accepted_vs_v1"] = True
            elif row["policy_id"] in ("C1", "C3", "C4"):
                row["accepted_vs_v1"] = False

    # final split (origin_cutoff empty)
    for policy, ptype in (
        ("V1", "policy"),
        ("C2", "policy"),
        ("count_only", "baseline"),
        ("organizer_cell", "baseline"),
    ):
        for budget in BUDGETS:
            row = add("final", None, policy, ptype, budget, 0.95, 0.8)
            row["notes"] = "final test previously viewed; not used for tuning"

    # confirmation split (directional relative lift only)
    for policy, ptype in (("V1", "policy"), ("C2", "policy"), ("count_only", "baseline")):
        row = add("confirmation", None, policy, ptype, 5, 0.90, 0.7)
        row["asset_capture"] = None
        row["notes"] = "directional relative lift only"

    # per-origin wins for the gate log
    origin_means = {
        p: {o: float(np.mean(v)) for o, v in per.items()} for p, per in val_assets.items()
    }
    gate = {}
    for cand in ("C1", "C2", "C3", "C4"):
        wins = sum(
            1 for o in ORIGINS if origin_means[cand][o] > origin_means["V1"][o]
        )
        gate[cand] = {
            "origin_wins": wins,
            "pooled_v1_score": pooled["V1"],
            "pooled_candidate_score": pooled[cand],
        }
    df = pd.DataFrame(rows, columns=list(c.VALIDATION_RESULTS_COLUMNS))
    return df, gate


# --------------------------------------------------------------------------- agent log


def build_agent_log(gate: dict[str, dict], v1: pd.DataFrame, v2: pd.DataFrame, n_escal: int):
    events: list[dict] = []
    base = pd.Timestamp("2026-10-03T21:00:00Z")

    def add(event_type, summary, candidate=None, details=None):
        seq = len(events) + 1
        ts = (base + pd.Timedelta(minutes=seq - 1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        events.append(
            {
                "seq": seq,
                "event_type": event_type,
                "timestamp": ts,
                "summary": summary,
                "candidate": candidate,
                "details": details or {},
            }
        )

    add(
        "PLAN_V1",
        "Built V1 plan from the full-history, per-asset policy",
        details={"n_assets": len(v1), "n_selected": int(v1["selected"].sum())},
    )
    add(
        "EVALUATE",
        "Evaluated V1 on 3 validation origins at 1/2/5/10% budgets",
        details={"origins": list(ORIGINS), "budgets_pct": list(BUDGETS)},
    )
    add(
        "DIAGNOSE",
        "Diagnosed V1 weakness: older breaks dominate recent failure patterns",
        details={"finding": "recent breaks under-weighted"},
    )
    accepted = []
    for cand in ("C1", "C2", "C3", "C4"):
        g = gate[cand]
        required = round(CANDIDATE_SE[cand] * GATE_SE_MULTIPLE, 4)
        diff = round(g["pooled_candidate_score"] - g["pooled_v1_score"], 4)
        ok = g["origin_wins"] >= GATE_MIN_WINS and diff >= required
        if ok:
            accepted.append(cand)
            reason = f"won {g['origin_wins']}/3 origins and pooled gain >= 1 SE"
        elif g["origin_wins"] < GATE_MIN_WINS:
            reason = f"won only {g['origin_wins']}/3 origins"
        else:
            reason = "pooled gain below 1 SE"
        candidate = {
            "candidate_id": cand,
            "origin_wins": g["origin_wins"],
            "n_origins": 3,
            "pooled_v1_score": g["pooled_v1_score"],
            "pooled_candidate_score": g["pooled_candidate_score"],
            "difference": diff,
            "bootstrap_se": CANDIDATE_SE[cand],
            "required_delta": required,
            "decision": "ACCEPT" if ok else "REJECT",
            "reason": reason,
        }
        add(
            "TEST_CANDIDATE",
            f"Testing {cand} ({CANDIDATE_DESC[cand]}) against V1 on 3 validation origins",
            candidate=candidate,
        )
        add(
            candidate["decision"],
            f"{cand} {'accepted' if ok else 'rejected'}: {reason}",
            candidate=candidate,
        )
    assert accepted == ["C2"], f"synthetic gate expected only C2 to pass, got {accepted}"
    add(
        "PLAN_V2",
        "Built V2 plan from accepted candidate C2",
        details={"selected_policy_id": "C2", "n_selected": int(v2["selected"].sum())},
    )
    add(
        "ESCALATE",
        "Escalated high-consequence, low-evidence assets for verification",
        details={"n_escalated": n_escal},
    )
    return events


# --------------------------------------------------------------------------- governance


def build_rank_changes(v1: pd.DataFrame, v2: pd.DataFrame) -> pd.DataFrame:
    m = v1[["asset_id", "rank", "recommended_action"]].merge(
        v2[["asset_id", "rank", "recommended_action"]],
        on="asset_id",
        suffixes=("_v1", "_v2"),
    )
    m["delta_rank"] = m["rank_v2"] - m["rank_v1"]
    m["abs_delta"] = m["delta_rank"].abs()
    m = m.sort_values(["abs_delta", "asset_id"], ascending=[False, True]).head(10)
    m = m.reset_index(drop=True)
    out = []
    for i, r in m.iterrows():
        reason_1 = (
            "recent breaks weighted under hl10"
            if r["delta_rank"] < 0
            else "older breaks decayed under hl10"
        )
        if r["recommended_action_v1"] != r["recommended_action_v2"]:
            a1, a2 = r["recommended_action_v1"], r["recommended_action_v2"]
            reason_2 = f"action changed: {a1} to {a2}"
        elif i % 2 == 0:
            reason_2 = "recency weighting"
        else:
            reason_2 = None
        out.append(
            {
                "asset_id": r["asset_id"],
                "rank_v1": int(r["rank_v1"]),
                "rank_v2": int(r["rank_v2"]),
                "delta_rank": int(r["delta_rank"]),
                "action_v1": r["recommended_action_v1"],
                "action_v2": r["recommended_action_v2"],
                "reason_1": reason_1,
                "reason_2": reason_2,
                "show_in_demo": bool(i < 4),
            }
        )
    return pd.DataFrame(out, columns=list(c.RANK_CHANGES_COLUMNS))


def build_escalation(v2: pd.DataFrame) -> pd.DataFrame:
    sel = v2[(v2["consequence_tier"] == "T1") & (v2["evidence_confidence"] == "LOW_VERIFY")]
    sel = sel.sort_values("rank")
    start = date(2026, 11, 1)
    rows = []
    for i, (_, r) in enumerate(sel.iterrows()):
        rows.append(
            {
                "asset_id": r["asset_id"],
                "priority_rank": int(r["rank"]),
                "consequence_tier": r["consequence_tier"],
                "evidence_confidence": r["evidence_confidence"],
                "escalation_reason": "high consequence, low evidence confidence",
                "owner": "Water Integrity Lead",
                "required_action": "Verify asset record before scheduling",
                "response_deadline": (start + timedelta(days=7 * i)).isoformat(),
                "status": "OPEN" if i % 2 == 0 else "IN_REVIEW",
                "last_reviewed": date(2026, 10, 3).isoformat(),
            }
        )
    return pd.DataFrame(rows, columns=list(c.ESCALATION_COLUMNS))


def build_not_covered() -> pd.DataFrame:
    rows = [
        ("NC-01", "service connections", "Service lines are not in the public pipe layer.",
         "No public geometry or break attribution.", "Utility service-line registry", "HIGH"),
        ("NC-02", "valves and hydrants", "Valves and hydrants are not modelled as assets.",
         "Failures are attributed to mains only.", "Valve and hydrant asset inventory", "MEDIUM"),
        ("NC-03", "private-side infrastructure", "Customer-side plumbing is out of scope.",
         "No data on private-side breaks.", "Private-side incident reports", "LOW"),
        ("NC-04", "pressure transients", "Surge and transient pressure events are not observed.",
         "No pressure telemetry in the open data.", "SCADA pressure time series", "MEDIUM"),
    ]
    note = "SYNTHETIC placeholder (City of Calgary open data pipe layer)"
    return pd.DataFrame(
        [(*r, note) for r in rows], columns=list(c.NOT_COVERED_COLUMNS)
    )


def build_data_quality() -> dict:
    return {
        "rows_dropped_missing_coordinates": 112,
        "match_rate_by_origin": {"2013": 0.81, "2016": 0.84, "2019": 0.86},
        "match_rate_by_era": {"pre_2000": 0.62, "2000_2012": 0.83, "2013_plus": 0.88},
        "unmatched_share_by_era": {"pre_2000": 0.38, "2000_2012": 0.17, "2013_plus": 0.12},
        "unreachable_final_test_share": 0.09,
        "future_year_pipe_rows_excluded": 14,
        "planned_rows_excluded": 230,
        "inactive_sensitivity": {"included_capture_5pct": 0.21, "excluded_capture_5pct": 0.20},
        "retired_status_strata": {"ACTIVE": 0.93, "RETIRED": 0.07},
        "notes": [
            "SYNTHETIC placeholder values.",
            "Present-day network does not reconstruct all historical assets.",
        ],
    }


# --------------------------------------------------------------------------- output


def write_json(path: Path, obj: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")


def write_csv(path: Path, df: pd.DataFrame) -> None:
    df.to_csv(path, index=False, lineterminator="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts" / "synthetic")
    args = parser.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)
    phys = build_physical(rng)
    v1, v2 = build_plans(phys, rng)
    baseline = build_baseline(v1, rng)
    validation, gate = build_validation(rng)
    rank_changes = build_rank_changes(v1, v2)
    escalation = build_escalation(v2)
    not_covered = build_not_covered()
    events = build_agent_log(gate, v1, v2, len(escalation))
    data_quality = build_data_quality()

    audit_summary = {
        "synthetic": True,
        "config_hash": c.PLACEHOLDER_CONFIG_HASH,
        "git_commit": "synthetic",
        "git_tag": "synthetic",
        "data_checksums": {},
        "selected_policy_id": "C2",
        "v1_policy_id": "V1",
        "v2_equals_v1": False,
        "budgets_pct": list(BUDGETS),
        "revision_gate": {
            "min_origin_wins": GATE_MIN_WINS,
            "n_origins": len(ORIGINS),
            "min_improvement_in_se": GATE_SE_MULTIPLE,
            "bootstrap_block_km": 1.0,
        },
        "final_test": {
            "cutoff_year": 2022,
            "outcome_years": [2023, 2024, 2025],
            "previously_viewed": True,
        },
        "data_quality": {
            "summary": "SYNTHETIC placeholder data quality summary",
            "overall_match_rate": 0.84,
        },
    }

    v1.to_parquet(out / c.PLAN_V1_FILE, index=False)
    v2.to_parquet(out / c.PLAN_V2_FILE, index=False)
    baseline.to_parquet(out / c.BASELINE_FILE, index=False)
    write_csv(out / c.VALIDATION_RESULTS_FILE, validation)
    write_csv(out / c.RANK_CHANGES_FILE, rank_changes)
    write_csv(out / c.ESCALATION_FILE, escalation)
    write_csv(out / c.NOT_COVERED_FILE, not_covered)
    with open(out / c.AGENT_LOG_FILE, "w", encoding="utf-8", newline="\n") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")
    write_json(out / c.AUDIT_SUMMARY_FILE, audit_summary)
    write_json(out / c.DATA_QUALITY_FILE, data_quality)
    print(f"Wrote {len(c.ARTIFACT_FILES)} synthetic artifacts to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
