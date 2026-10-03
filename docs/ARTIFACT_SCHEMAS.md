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

Every candidate decision must include:
- candidate ID;
- origin wins;
- pooled V1 score;
- pooled candidate score;
- difference;
- bootstrap SE;
- required delta;
- decision;
- reason.

## `audit_summary.json`

Required:
- `synthetic`
- `config_hash`
- `git_commit`
- `git_tag`
- `data_checksums`
- `selected_policy_id`
- `v1_policy_id`
- `revision_gate`
- `final_test`
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
