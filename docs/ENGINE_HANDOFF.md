# Pipe Dreams — Engine → API Artifact Handoff

The engine and the API share files, not code. The engine writes artifacts. The API reads them once at startup and never recomputes anything.

## Steps

1. **Write a run directory.** The engine writes all ten files listed in [`ARTIFACT_SCHEMAS.md`](./ARTIFACT_SCHEMAS.md) to `artifacts/<run>/` (for example `artifacts/final-freeze-v1/`):
   `plan_v1.parquet`, `plan_v2.parquet`, `baseline.parquet`, `validation_results.csv`, `agent_log.jsonl`, `audit_summary.json`, `rank_changes.csv`, `escalation.csv`, `not_covered.csv`, `data_quality.json`.
   `artifacts/*` is git-ignored except `artifacts/synthetic/`.

2. **Validate.** From the repo root:

   ```bash
   backend/.venv/Scripts/python scripts/validate_artifacts.py artifacts/<run>   # POSIX: backend/.venv/bin/python
   ```

   This runs the same checks the API loader runs (`backend/app/services/artifact_validation.py`). It exits non-zero on any error. Fix the engine output, not the validator.

3. **Point the API at it and restart.**

   ```bash
   # PowerShell
   $env:PIPE_DREAMS_ARTIFACT_DIR = "artifacts/<run>"
   # bash
   export PIPE_DREAMS_ARTIFACT_DIR=artifacts/<run>
   cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000
   ```

   Relative paths resolve against the repo root. Artifacts are loaded once, so restart the API after every new run. Check `GET /api/health`: `status` must be `"ok"`. If it reports `"degraded"`, the startup log lists each validation error, and every other route returns `503 artifacts_unavailable`.

## Shapes the API relies on beyond ARTIFACT_SCHEMAS.md

- `audit_summary.json` must also carry `v2_equals_v1` (bool) and `budgets_pct` (list of ints). `revision_gate` holds `min_origin_wins`, `n_origins`, `min_improvement_in_se`, `bootstrap_block_km`. `final_test` holds `cutoff_year`, `outcome_years`, `previously_viewed`.
- Each `agent_log.jsonl` line holds `seq`, `event_type`, `timestamp`, `summary`, `candidate` (object or null) and `details` (object). `candidate` is required on `TEST_CANDIDATE`, `ACCEPT` and `REJECT` events, with `candidate_id, origin_wins, n_origins, pooled_v1_score, pooled_candidate_score, difference, bootstrap_se, required_delta, decision, reason`.
- `data_quality.json` uses exactly the keys in `API_CONTRACT.md` under `/api/data-quality`.
- `source_segment_ids` is a parquet list of strings.
- V1 and V2 must contain the same assets with identical physical columns (`asset_id, source_segment_ids, length_m, consequence_tier, evidence_confidence, association_quality, rank_stability, evidence_basis, latitude, longitude, geometry_wkt`).

`scripts/make_synthetic_artifacts.py` is a working reference for every shape.

## Screenshot rule

Before any screenshot, recording or submission material, `audit_summary.json` must have `synthetic: false` and a real `config_hash` (not `"PLACEHOLDER"`). The validator prints a warning while either is true, and the frontend shows the SYNTHETIC / PLACEHOLDER DATA banner.
