# Pipe Dreams — Artifact Schemas

These artifacts are the contract between the Python engine and FastAPI.

## `plan_v1.parquet` / `plan_v2.parquet`

Required columns:
- `asset_id`
- `source_segment_ids`
- `rank`
- `selected`
- `length_m`
- `likelihood_score`
- `priority_score`
- `consequence_tier`
- `evidence_confidence`
- `association_quality`
- `rank_stability`
- `evidence_basis`
- `recommended_action`
- `revision_reason`
- `latitude`
- `longitude`
- `geometry_wkt`

Types:
- `source_segment_ids` is a parquet `list<string>`;
- `latitude` / `longitude` / `geometry_wkt` are WGS84 (EPSG:4326).

Physical columns (must be identical for the same `asset_id` in V1 and V2):
`asset_id`, `source_segment_ids`, `length_m`, `consequence_tier`, `evidence_confidence`, `association_quality`, `rank_stability`, `evidence_basis`, `latitude`, `longitude`, `geometry_wkt`.

Integrity:
- unique ranks 1..N;
- selected state derives from frozen capacity;
- same physical asset attributes must not randomly differ between V1 and V2;
- V2 changes must be policy/action changes, not regenerated asset metadata.

## `baseline.parquet`

Required:
- `asset_id`
- `baseline_name`
- `rank`
- `selected`
- `score`
- `length_m`

## `validation_results.csv`

Required:
- `split` = validation | final | confirmation
- `origin_cutoff`
- `policy_id`
- `policy_type`
- `budget_pct`
- `asset_capture`
- `event_capture`
- `lift_vs_count_only`
- `ci_low`
- `ci_high`
- `matched_break_share`
- `pooled_gate_score`
- `accepted_vs_v1`
- `notes`

Rules:
- organizer cell baseline has null `asset_capture`;
- final split contains V1, selected V2, and baselines only;
- confirmation may omit absolute capture.

## `agent_log.jsonl`

Events may include:
- `PLAN_V1`
- `EVALUATE`
- `DIAGNOSE`
- `TEST_CANDIDATE`
- `ACCEPT`
- `REJECT`
- `PLAN_V2`
- `ESCALATE`

Every line is one JSON object with:
- `seq` (int, unique, ascending order of events);
- `event_type` (one of the events above);
- `timestamp` (ISO 8601 string);
- `summary` (short human-readable string);
- `candidate` (object, or `null`);
- `details` (object; free-form extras, may be `{}`).

`candidate` is required (non-null) on `TEST_CANDIDATE`, `ACCEPT` and `REJECT` events and must contain:
- `candidate_id`;
- `origin_wins`;
- `n_origins`;
- `pooled_v1_score`;
- `pooled_candidate_score`;
- `difference`;
- `bootstrap_se`;
- `required_delta`;
- `decision` (`ACCEPT` | `REJECT`);
- `reason`.

## `audit_summary.json`

Required:
- `synthetic`
- `config_hash`
- `git_commit`
- `git_tag`
- `data_checksums`
- `selected_policy_id`
- `v1_policy_id`
- `v2_equals_v1` (bool)
- `budgets_pct` (list of int, e.g. `[1, 2, 5, 10]`)
- `revision_gate` — object with `min_origin_wins`, `n_origins`, `min_improvement_in_se`, `bootstrap_block_km`
- `final_test` — object with `cutoff_year`, `outcome_years`, `previously_viewed` (bool)
- `data_quality`

## `rank_changes.csv`

Required:
- `asset_id`
- `rank_v1`
- `rank_v2`
- `delta_rank`
- `action_v1`
- `action_v2`
- `reason_1`
- `reason_2`
- `show_in_demo`

At least three real rows must have `show_in_demo=true`.

## `escalation.csv`

Required:
- `asset_id`
- `priority_rank`
- `consequence_tier`
- `evidence_confidence`
- `escalation_reason`
- `owner`
- `required_action`
- `response_deadline`
- `status`
- `last_reviewed`

Escalation must be derived from the actual plan/governance rules, not hardcoded unrelated values.

## `not_covered.csv`

Required:
- `coverage_issue_id`
- `scope`
- `description`
- `why_not_covered`
- `required_evidence`
- `ui_severity`
- `source_note`

## `data_quality.json`

Keys must be spelled exactly as in `API_CONTRACT.md` under `GET /api/data-quality`.

Required:
- rows dropped for missing coordinates;
- match rate by origin;
- match rate by era;
- unmatched share by era;
- unreachable final-test share;
- future-year pipe rows excluded;
- planned rows excluded;
- inactive sensitivity;
- retired-status reporting strata;
- notes.

---

## Validation

Run `scripts/validate_artifacts.py artifacts/<run>` before pointing the API at a new run. It uses the same checks as the API loader; see `docs/ENGINE_HANDOFF.md`.

---

## Community Intelligence Artifacts

Community analysis is separate from the pipe-level V1/V2
experiment. All community artifacts are generated offline.

### `communities.csv`

One row per community per supported historical cutoff.

Required columns:
- `community_id`
- `community_name`
- `cutoff_year`
- `pipe_length_km`
- `historical_break_count`
- `historical_breaks_per_km`
- `population`
- `equity_index`
- `equity_geography_status`
- `data_quality_flags`

Rules:
- `community_id` and `cutoff_year` jointly identify each row.
- Historical break counts include events through the cutoff only.
- Historical pipe length excludes assets installed after the cutoff.
- Pipe length is calculated from line geometry clipped to
  community boundaries.
- `historical_breaks_per_km` is null when pipe length is zero
  or unavailable.
- Population and equity fields remain null until their sources
  and geographic alignment are verified.
- Current population/equity context must not enter historical
  predictive evaluation.
- `data_quality_flags` is a JSON-encoded array of strings
  when stored in CSV.

### `communities.geojson`

A GeoJSON FeatureCollection containing community boundaries
and their frozen indicators.

Required:
- WGS84 (EPSG:4326) geometry;
- `community_id` as each feature's ID;
- properties matching the corresponding `communities.csv` row.

A separate GeoJSON artifact is produced for each supported
cutoff year, named:

`communities_{cutoff_year}.geojson`

The API selects the appropriate frozen file using the
`cutoff_year` query parameter.

### `community_validation.csv`

One row per historical validation origin per requested network-length
budget.

Required columns:
- `origin_cutoff`
- `outcome_start_year`
- `outcome_end_year`
- `budget_pct`
- `communities_evaluated`
- `selected_community_count`
- `selected_pipe_length_km`
- `eligible_pipe_length_km`
- `actual_network_share`
- `future_break_events`
- `future_break_events_assigned`
- `future_break_events_unassigned`
- `future_break_events_ambiguous`
- `future_break_events_in_eligible_network`
- `future_break_events_outside_eligible_network`
- `selected_future_break_events`
- `event_capture`
- `lift_vs_network_share`
- `notes`

Rules:
- Rank communities using only historical information available at the
  origin cutoff.
- Historical ranking uses `historical_breaks_per_km`, with deterministic
  tie-breaking by historical break count and community ID.
- Evaluate the fixed network-length budgets defined in the experiment
  protocol: 5%, 10%, and 20%.
- Select whole communities in rank order until the requested share of
  eligible pipe-network length is reached.
- Because communities are atomic decision units, the realized network
  share may exceed the requested budget. `actual_network_share` records
  the realized fraction.
- Future break events are evaluated only in the declared future outcome
  period.
- `event_capture` uses uniquely assigned future events occurring in
  communities that had eligible pipe network at the historical cutoff
  as its denominator.
- Future events outside the eligible historical network are reported
  separately and are not silently discarded.
- Geographic assignment coverage, including unassigned and ambiguous
  events, must be reported separately.
- `lift_vs_network_share` equals `event_capture` divided by
  `actual_network_share`.
- This artifact does not participate in the pipe-level V1/V2 acceptance
  gate.

### Community Data Integrity

- Community IDs must be stable across all artifacts.
- Boundary versions and data-source versions must be recorded.
- Community polygons must not silently duplicate break events
  along shared boundaries.
- Breaks outside the covered geography must be reported.
- Small pipe-length denominators must be flagged.
- Present-day geometry and historical boundary limitations
  must be disclosed.
- All numerical results must come from actual processing;
  synthetic examples must remain explicitly labeled.
