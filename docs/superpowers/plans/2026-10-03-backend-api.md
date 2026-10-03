# Backend API Build Plan (2026-10-03)

Branch: `feat/backend-api`. Scope: `backend/`, `scripts/`, `artifacts/synthetic/`, `docs/ENGINE_HANDOFF.md`, README backend section.
Out of scope: `frontend/`, `engine/`, `docs/API_CONTRACT.md`, `docs/ARTIFACT_SCHEMAS.md` (read-only; report contract issues instead).

Binding: `AGENTS.md`, `docs/API_CONTRACT.md` (response shapes), `docs/ARTIFACT_SCHEMAS.md` (inputs).
FastAPI is thin: read precomputed artifacts only. No engine imports, no model fitting, no ranking/gate/score computation.
Allowed deps: fastapi, uvicorn[standard], pydantic, pydantic-settings, pandas, pyarrow, shapely; dev: pytest, httpx, ruff.

## Environment

```bash
py -3.11 -m venv backend/.venv            # Windows; elsewhere: python3.11 -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -e "backend[dev]"   # POSIX: backend/.venv/bin/python
```

## Pinned design decisions (all workers follow these)

### Module layout
```
backend/pyproject.toml                 # package "pipe-dreams-backend", packages app*, requires-python >=3.11, ruff + pytest config
backend/app/core/settings.py           # pydantic-settings: artifact_dir, cors_origins
backend/app/core/constants.py          # enums, required columns/keys, physical columns, paging limits, file names
backend/app/schemas/                   # Pydantic response models (common, health, overview, assets, audit, governance)
backend/app/services/artifact_validation.py  # read raw files + validate -> (RawArtifacts, errors). Shared by loader and script.
backend/app/services/artifact_service.py     # load once, cache, wkt->GeoJSON, typed accessors; degraded on failure
backend/app/api/router.py, api/routes/{health,overview,assets,audit,governance}.py
backend/app/main.py                    # create_app(artifact_dir: Path | None = None) -> FastAPI; app = create_app()
scripts/make_synthetic_artifacts.py    # deterministic generator -> artifacts/synthetic/
scripts/validate_artifacts.py <dir>    # imports app.services.artifact_validation; non-zero exit on failure
```

### Settings
- `artifact_dir` default `artifacts/synthetic`, resolved relative to repo root when relative; env override `PIPE_DREAMS_ARTIFACT_DIR`.
- `cors_origins` default `["http://localhost:5173"]`; env `PIPE_DREAMS_CORS_ORIGINS` (JSON list). No wildcard.

### Shapes not fully specified by ARTIFACT_SCHEMAS (chosen here; reported as contract gaps)
- `audit_summary.json` keys: `synthetic` (bool), `config_hash` (str), `git_commit`, `git_tag`, `data_checksums` (obj),
  `selected_policy_id` (PolicyId), `v1_policy_id` (PolicyId), `v2_equals_v1` (bool), `budgets_pct` (list[int]),
  `revision_gate` {`min_origin_wins`, `n_origins`, `min_improvement_in_se`, `bootstrap_block_km`},
  `final_test` {`cutoff_year`, `outcome_years`, `previously_viewed` (bool)}, `data_quality` (obj summary).
  `/api/overview.final_test_previously_viewed` = `final_test.previously_viewed`.
- `agent_log.jsonl` line: `seq` (int), `event_type` (AuditEventType), `timestamp` (str), `summary` (str),
  `candidate` (obj|null; required non-null on TEST_CANDIDATE/ACCEPT/REJECT), `details` (obj).
  candidate keys: `candidate_id, origin_wins, n_origins, pooled_v1_score, pooled_candidate_score, difference, bootstrap_se, required_delta, decision, reason`.
- `source_segment_ids`: parquet `list<string>`.
- Physical (V1/V2-shared) columns: `asset_id, source_segment_ids, length_m, consequence_tier, evidence_confidence, association_quality, rank_stability, evidence_basis, latitude, longitude, geometry_wkt`.
  Plan-specific: `rank, selected, likelihood_score, priority_score, recommended_action, revision_reason`.
- `validation_results.csv.policy_type` in {`policy`,`baseline`}; `policy_id` in PolicyId ∪ BaselineId.

### Validation rules (artifact_validation.py; any error => API degraded, script exit 1)
1. All 10 files exist and parse.
2. Required columns (tables) / keys (JSON) present; `data_quality.json` keys exactly as API_CONTRACT `/api/data-quality`.
3. Enums: Split, PolicyId/BaselineId, policy_type, EvidenceConfidence (plans, escalation), AuditEventType, CandidateDecision, baseline_name in BaselineId.
4. Each plan: ranks unique and exactly 1..N; asset_id unique; V1 and V2 have the same asset_id set and identical physical columns.
5. `rank_changes.csv`: at least 3 rows with `show_in_demo == true`.
6. `organizer_cell` rows in validation_results have null `asset_capture`.
7. Every geometry_wkt parses (shapely) as LineString/MultiLineString.
8. agent_log: `candidate` non-null on TEST_CANDIDATE/ACCEPT/REJECT with all candidate keys; `seq` unique.
9. audit_summary: `synthetic` is bool; `config_hash` non-empty string.
The script additionally prints a WARNING (not failure) when `synthetic` is true or `config_hash == "PLACEHOLDER"`.

### API behaviour
- Envelope `{meta: {synthetic, config_hash}, data}` on all routes except `/api/health`.
- Errors `{error: {code, message}}`: 404 `asset_not_found`, 422 `invalid_query` (custom RequestValidationError handler), 503 `artifacts_unavailable`.
- Load once at app creation; geometry converted to GeoJSON once with shapely `mapping()`; NaN -> null.
- `/api/assets/geojson` registered before `/api/assets/{asset_id}`.
- Paging limits in constants: assets limit 1-500 default 100; rank-changes limit 1-500 default 50.
- Sorting: `rank` asc, `priority_score` desc, `length_m` desc (ties by rank). Filtering/sorting/paging only.

## Tasks

| # | Task | Depends on | Worker |
|---|---|---|---|
| 1 | pyproject, venv, settings, constants, schemas, artifact_validation, synthetic generator (+ generated files), validate_artifacts.py | - | W1 |
| 2 | artifact_service, routes, router, main, error handlers, CORS | 1 | W2 |
| 3 | pytest suite (all routes, envelope, degraded/503, 404, 422, geojson routing, paging/filters, validator pass/fail) | 1 (writes against contract + create_app) | W3, parallel to 2 |
| 4 | docs/ENGINE_HANDOFF.md, README backend run section | 1 | orchestrator |
| 5 | Integration: pytest green, ruff clean, uvicorn smoke + curl each route | 2, 3 | orchestrator |
