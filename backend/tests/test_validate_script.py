"""scripts/validate_artifacts.py and read_and_validate."""

import subprocess
import sys

import pandas as pd
from conftest import ROOT, SYNTHETIC_DIR

from app.services.artifact_validation import read_and_validate

SCRIPT = ROOT / "scripts" / "validate_artifacts.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_synthetic_passes():
    proc = _run(SYNTHETIC_DIR)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS" in proc.stdout


def test_missing_rank_changes(broken_copy):
    (broken_copy / "rank_changes.csv").unlink()
    proc = _run(broken_copy)
    assert proc.returncode == 1
    assert "FAIL" in proc.stdout
    assert "rank_changes.csv" in proc.stdout


def test_duplicate_rank_in_plan_v2(broken_copy):
    path = broken_copy / "plan_v2.parquet"
    df = pd.read_parquet(path)
    df.loc[df.index[1], "rank"] = df.loc[df.index[0], "rank"]
    df.to_parquet(path)
    proc = _run(broken_copy)
    assert proc.returncode == 1
    assert "rank" in proc.stdout


def test_organizer_cell_asset_capture_set(broken_copy):
    path = broken_copy / "validation_results.csv"
    df = pd.read_csv(path)
    mask = df["policy_id"] == "organizer_cell"
    assert mask.any()
    df.loc[mask, "asset_capture"] = 0.5
    df.to_csv(path, index=False)
    proc = _run(broken_copy)
    assert proc.returncode == 1
    assert "organizer_cell" in proc.stdout


def test_show_in_demo_all_false(broken_copy):
    path = broken_copy / "rank_changes.csv"
    df = pd.read_csv(path)
    df["show_in_demo"] = False
    df.to_csv(path, index=False)
    proc = _run(broken_copy)
    assert proc.returncode == 1
    assert "show_in_demo" in proc.stdout


def test_usage_error_exit_2():
    assert _run().returncode == 2


def test_read_and_validate_ok():
    raw, errors = read_and_validate(SYNTHETIC_DIR)
    assert errors == []
    assert raw is not None


def test_read_and_validate_missing_dir(tmp_path):
    raw, errors = read_and_validate(tmp_path / "nope")
    assert raw is None
    assert errors


def test_read_and_validate_missing_file(broken_copy):
    (broken_copy / "escalation.csv").unlink()
    raw, errors = read_and_validate(broken_copy)
    assert raw is None
    assert any("escalation.csv" in e for e in errors)
