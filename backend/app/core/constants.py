"""Domain constants: enums, artifact file names, required columns/keys, paging limits."""

# --- Enums (docs/API_CONTRACT.md) ---
POLICY_IDS = ("V1", "C1", "C2", "C3", "C4")
BASELINE_IDS = ("count_only", "organizer_cell")
PLAN_IDS = ("v1", "v2")
SPLITS = ("validation", "final", "confirmation")
EVIDENCE_CONFIDENCE = ("HIGH", "MEDIUM", "LOW_VERIFY")
AUDIT_EVENT_TYPES = (
    "PLAN_V1",
    "EVALUATE",
    "DIAGNOSE",
    "TEST_CANDIDATE",
    "ACCEPT",
    "REJECT",
    "PLAN_V2",
    "ESCALATE",
)
CANDIDATE_DECISIONS = ("ACCEPT", "REJECT")
POLICY_TYPES = ("policy", "baseline")
CANDIDATE_EVENT_TYPES = ("TEST_CANDIDATE", "ACCEPT", "REJECT")

# --- Artifact file names ---
PLAN_V1_FILE = "plan_v1.parquet"
PLAN_V2_FILE = "plan_v2.parquet"
BASELINE_FILE = "baseline.parquet"
VALIDATION_RESULTS_FILE = "validation_results.csv"
AGENT_LOG_FILE = "agent_log.jsonl"
AUDIT_SUMMARY_FILE = "audit_summary.json"
RANK_CHANGES_FILE = "rank_changes.csv"
ESCALATION_FILE = "escalation.csv"
NOT_COVERED_FILE = "not_covered.csv"
DATA_QUALITY_FILE = "data_quality.json"
ARTIFACT_FILES = (
    PLAN_V1_FILE,
    PLAN_V2_FILE,
    BASELINE_FILE,
    VALIDATION_RESULTS_FILE,
    AGENT_LOG_FILE,
    AUDIT_SUMMARY_FILE,
    RANK_CHANGES_FILE,
    ESCALATION_FILE,
    NOT_COVERED_FILE,
    DATA_QUALITY_FILE,
)

# --- Plan columns (docs/ARTIFACT_SCHEMAS.md + plan doc) ---
PHYSICAL_COLUMNS = (
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
    "geometry_wkt",
)
PLAN_SPECIFIC_COLUMNS = (
    "rank",
    "selected",
    "likelihood_score",
    "priority_score",
    "recommended_action",
    "revision_reason",
)
PLAN_COLUMNS = PHYSICAL_COLUMNS + PLAN_SPECIFIC_COLUMNS

# --- Required columns per table ---
BASELINE_COLUMNS = ("asset_id", "baseline_name", "rank", "selected", "score", "length_m")
VALIDATION_RESULTS_COLUMNS = (
    "split",
    "origin_cutoff",
    "policy_id",
    "policy_type",
    "budget_pct",
    "asset_capture",
    "event_capture",
    "lift_vs_count_only",
    "ci_low",
    "ci_high",
    "matched_break_share",
    "pooled_gate_score",
    "accepted_vs_v1",
    "notes",
)
RANK_CHANGES_COLUMNS = (
    "asset_id",
    "rank_v1",
    "rank_v2",
    "delta_rank",
    "action_v1",
    "action_v2",
    "reason_1",
    "reason_2",
    "show_in_demo",
)
ESCALATION_COLUMNS = (
    "asset_id",
    "priority_rank",
    "consequence_tier",
    "evidence_confidence",
    "escalation_reason",
    "owner",
    "required_action",
    "response_deadline",
    "status",
    "last_reviewed",
)
NOT_COVERED_COLUMNS = (
    "coverage_issue_id",
    "scope",
    "description",
    "why_not_covered",
    "required_evidence",
    "ui_severity",
    "source_note",
)

# --- Required keys per JSON ---
AUDIT_SUMMARY_KEYS = (
    "synthetic",
    "config_hash",
    "git_commit",
    "git_tag",
    "data_checksums",
    "selected_policy_id",
    "v1_policy_id",
    "v2_equals_v1",
    "budgets_pct",
    "revision_gate",
    "final_test",
    "data_quality",
)
REVISION_GATE_KEYS = (
    "min_origin_wins",
    "n_origins",
    "min_improvement_in_se",
    "bootstrap_block_km",
)
FINAL_TEST_KEYS = ("cutoff_year", "outcome_years", "previously_viewed")
DATA_QUALITY_KEYS = (
    "rows_dropped_missing_coordinates",
    "match_rate_by_origin",
    "match_rate_by_era",
    "unmatched_share_by_era",
    "unreachable_final_test_share",
    "future_year_pipe_rows_excluded",
    "planned_rows_excluded",
    "inactive_sensitivity",
    "retired_status_strata",
    "notes",
)
AGENT_LOG_KEYS = ("seq", "event_type", "timestamp", "summary", "candidate", "details")
CANDIDATE_KEYS = (
    "candidate_id",
    "origin_wins",
    "n_origins",
    "pooled_v1_score",
    "pooled_candidate_score",
    "difference",
    "bootstrap_se",
    "required_delta",
    "decision",
    "reason",
)

# --- Governance / demo ---
MIN_DEMO_RANK_CHANGES = 3
PLACEHOLDER_CONFIG_HASH = "PLACEHOLDER"
ORGANIZER_CELL_ID = "organizer_cell"

# --- Paging / sorting ---
ASSETS_LIMIT_DEFAULT = 100
ASSETS_LIMIT_MAX = 500
RANK_CHANGES_LIMIT_DEFAULT = 50
RANK_CHANGES_LIMIT_MAX = 500
ASSET_SORT_FIELDS = ("rank", "priority_score", "length_m")

# CRS the engine writes geometry_wkt in (Alberta 3TM, metres); see DECISIONS.md #13.
ENGINE_PROJECTED_CRS = "EPSG:3776"
