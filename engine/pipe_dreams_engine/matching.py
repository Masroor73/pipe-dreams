"""Spatial matching and temporal eligibility for break-to-pipe attribution.

Geometries must already be in a metre CRS. Recovered matching used EPSG:3776;
this module does not reproject.

Distance and ambiguity thresholds are the recovered audit defaults. They are
not read from config yet and must not be retuned from final-window results.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from shapely import STRtree

# Recovered defaults from data/audit_handoff/audit_backtest.py.
CRS_M = "EPSG:3776"
ASSOC_M = 30.0
AMBIG_M = 5.0


def _as_bool_or_array(mask):
    if mask.shape == ():
        return bool(mask)
    return mask



def _safe_year(value):
    """Convert years to numeric values; invalid or missing years become NaN."""
    return np.asarray(pd.to_numeric(value, errors="coerce"), dtype=float)


def historically_attributable(install_year, break_year):
    """A pipe must have been installed strictly before the historical break."""
    installed = _safe_year(install_year)
    broken = _safe_year(break_year)
    valid = np.isfinite(installed) & np.isfinite(broken)
    return _as_bool_or_array(valid & (installed < broken))


def eligible_at_cutoff(install_year, cutoff_year):
    """A pipe must exist by the planning cutoff year."""
    installed = _safe_year(install_year)
    cutoff = _safe_year(cutoff_year)
    valid = np.isfinite(installed) & np.isfinite(cutoff)
    return _as_bool_or_array(valid & (installed <= cutoff))


def _spatial_pairs(break_geoms, pipe_geoms, assoc_m: float) -> pd.DataFrame:
    """All (break, pipe) pairs within assoc_m using true point-to-line distance."""
    n_breaks = len(break_geoms)
    n_pipes = len(pipe_geoms)
    if n_breaks == 0 or n_pipes == 0:
        return pd.DataFrame(columns=["b", "p", "dist"])

    tree = STRtree(pipe_geoms)
    rows = []
    for b_idx, geom in enumerate(break_geoms):
        if geom is None or getattr(geom, "is_empty", False):
            continue
        hits = tree.query(geom, predicate="dwithin", distance=assoc_m)
        for p_idx in np.atleast_1d(hits):
            p_idx = int(p_idx)
            pipe_geom = pipe_geoms[p_idx]
            dist = float(geom.distance(pipe_geom))
            if dist <= assoc_m + 1e-6:
                rows.append((b_idx, p_idx, dist))

    if not rows:
        return pd.DataFrame(columns=["b", "p", "dist"])
    return pd.DataFrame(rows, columns=["b", "p", "dist"])


def associate_breaks(
    breaks: pd.DataFrame,
    pipes: pd.DataFrame,
    *,
    assoc_m: float = ASSOC_M,
    ambig_m: float = AMBIG_M,
    break_year_col: str = "break_year",
    install_year_col: str = "install_year",
    pipe_id_col: str = "asset_id",
) -> pd.DataFrame:
    """Associate each break with the nearest historically attributable pipe.

    Spatial filter: point-to-line distance <= assoc_m (recovered default 30 m).
    Temporal filter for attribution: install_year < break_year.

    Candidate-pipe eligibility at a planning cutoff (install_year <= cutoff)
    is not applied here; use eligible_at_cutoff.
    """
    break_geoms = list(breaks["geometry"])
    pipe_geoms = list(pipes["geometry"])
    pairs = _spatial_pairs(break_geoms, pipe_geoms, assoc_m)

    out = pd.DataFrame(index=breaks.index)
    out["candidate_count_within_threshold"] = 0
    out["nearest_segment_idx"] = -1
    out["nearest_distance_m"] = np.nan
    out["second_nearest_distance_m"] = np.nan
    out["nearest_segment_id"] = None
    out["associated"] = False
    out["ambiguous"] = False

    if pairs.empty:
        return out

    spatial_counts = pairs.groupby("b").size()
    out.loc[out.index[spatial_counts.index], "candidate_count_within_threshold"] = (
        spatial_counts.to_numpy()
    )

    install = pipes[install_year_col].to_numpy()
    break_year = breaks[break_year_col].to_numpy()
    pairs = pairs.copy()
    pairs["eligible"] = historically_attributable(
        install[pairs["p"].to_numpy()],
        break_year[pairs["b"].to_numpy()],
    )

    el = pairs.loc[pairs["eligible"]].sort_values(["b", "dist", "p"], kind="mergesort")
    if el.empty:
        return out

    el = el.copy()
    el["rank"] = el.groupby("b").cumcount()
    first = el.loc[el["rank"] == 0].set_index("b")
    second = el.loc[el["rank"] == 1].set_index("b")

    first_pos = first.index.to_numpy()
    out.iloc[first_pos, out.columns.get_loc("nearest_segment_idx")] = first["p"].to_numpy()
    out.iloc[first_pos, out.columns.get_loc("nearest_distance_m")] = first["dist"].to_numpy()
    if pipe_id_col in pipes.columns:
        ids = pipes[pipe_id_col].to_numpy()
        out.iloc[first_pos, out.columns.get_loc("nearest_segment_id")] = ids[first["p"].to_numpy()]
    out.iloc[first_pos, out.columns.get_loc("associated")] = True

    if not second.empty:
        second_pos = second.index.to_numpy()
        out.iloc[second_pos, out.columns.get_loc("second_nearest_distance_m")] = (
            second["dist"].to_numpy()
        )

    associated = out["associated"].to_numpy()
    gap = out["second_nearest_distance_m"].to_numpy() - out["nearest_distance_m"].to_numpy()
    out["ambiguous"] = associated & (gap <= ambig_m)

    matched = out["associated"].to_numpy()
    if matched.any():
        nearest_idx = out.loc[matched, "nearest_segment_idx"].to_numpy()
        dists = out.loc[matched, "nearest_distance_m"].to_numpy()
        if np.any(dists > assoc_m + 1e-6):
            raise AssertionError("associated distance exceeds association threshold")
        if not np.all(
            historically_attributable(
                pipes[install_year_col].to_numpy()[nearest_idx],
                breaks.loc[matched, break_year_col].to_numpy(),
            )
        ):
            raise AssertionError("associated pipe install_year is not < break_year")

    return out
