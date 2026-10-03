// Types mirror docs/API_CONTRACT.md exactly (snake_case, nulls never omitted).
// Do not add derived/domain fields here. Contract changes must update the
// backend Pydantic models, API_CONTRACT.md and this file in the same change.

export type PolicyId = 'V1' | 'C1' | 'C2' | 'C3' | 'C4';
export type BaselineId = 'count_only' | 'organizer_cell';
export type PlanId = 'v1' | 'v2';
export type Split = 'validation' | 'final' | 'confirmation';
export type EvidenceConfidence = 'HIGH' | 'MEDIUM' | 'LOW_VERIFY';
export type AuditEventType =
  | 'PLAN_V1'
  | 'EVALUATE'
  | 'DIAGNOSE'
  | 'TEST_CANDIDATE'
  | 'ACCEPT'
  | 'REJECT'
  | 'PLAN_V2'
  | 'ESCALATE';
export type CandidateDecision = 'ACCEPT' | 'REJECT';

/** Values frozen in config/; frontend displays them verbatim. */
export type ConsequenceTier = string;
export type RecommendedAction = string;
export type EscalationStatus = string;
export type UiSeverity = string;

export interface Meta {
  synthetic: boolean;
  config_hash: string;
}

export interface Envelope<T> {
  meta: Meta;
  data: T;
}

export interface ApiErrorBody {
  error: {
    code: 'asset_not_found' | 'invalid_query' | 'artifacts_unavailable' | string;
    message: string;
  };
}

// ---- /api/health (not enveloped) ----
export interface Health {
  status: 'ok' | 'degraded';
  artifacts_loaded: boolean;
  artifact_dir: string;
  /** null when degraded (artifacts not loaded, so synthetic-ness is unknown). */
  synthetic: boolean | null;
}

// ---- /api/overview ----
export interface RevisionGate {
  min_origin_wins: number;
  n_origins: number;
  min_improvement_in_se: number;
  bootstrap_block_km: number;
}

export interface SeriesRow {
  split: Split;
  origin_cutoff: string | null;
  policy_id: PolicyId | BaselineId;
  policy_type: 'policy' | 'baseline';
  budget_pct: number;
  asset_capture: number | null;
  event_capture: number | null;
  lift_vs_count_only: number | null;
  ci_low: number | null;
  ci_high: number | null;
  matched_break_share: number | null;
  pooled_gate_score: number | null;
  accepted_vs_v1: boolean | null;
  notes: string | null;
}

export interface Overview {
  git_commit: string;
  git_tag: string;
  v1_policy_id: PolicyId;
  selected_policy_id: PolicyId;
  v2_equals_v1: boolean;
  final_test_previously_viewed: boolean;
  budgets_pct: number[];
  revision_gate: RevisionGate;
  series: SeriesRow[];
}

// ---- /api/assets ----
export interface AssetListItem {
  asset_id: string;
  rank: number;
  selected: boolean;
  length_m: number;
  priority_score: number;
  consequence_tier: ConsequenceTier;
  evidence_confidence: EvidenceConfidence;
  recommended_action: RecommendedAction;
  latitude: number;
  longitude: number;
}

export interface AssetList {
  plan: PlanId;
  total: number;
  limit: number;
  offset: number;
  items: AssetListItem[];
}

export interface AssetListQuery {
  plan?: PlanId;
  selected_only?: boolean;
  evidence_confidence?: EvidenceConfidence;
  consequence_tier?: string;
  sort?: 'rank' | 'priority_score' | 'length_m';
  limit?: number;
  offset?: number;
}

// ---- /api/assets/geojson ----
export interface LineStringGeometry {
  type: 'LineString';
  coordinates: [number, number][];
}

export interface AssetFeatureProperties {
  asset_id: string;
  rank: number;
  selected: boolean;
  consequence_tier: ConsequenceTier;
  evidence_confidence: EvidenceConfidence;
  recommended_action: RecommendedAction;
}

export interface AssetFeature {
  type: 'Feature';
  id: string;
  geometry: LineStringGeometry;
  properties: AssetFeatureProperties;
}

export interface AssetFeatureCollection {
  type: 'FeatureCollection';
  features: AssetFeature[];
}

export interface AssetGeoJsonQuery {
  plan?: PlanId;
  selected_only?: boolean;
}

// ---- /api/assets/{asset_id} ----
export interface PlanFields {
  rank: number;
  selected: boolean;
  likelihood_score: number;
  priority_score: number;
  recommended_action: RecommendedAction;
  revision_reason: string | null;
}

export interface AssetRankChange {
  delta_rank: number;
  reason_1: string | null;
  reason_2: string | null;
  show_in_demo: boolean;
}

export interface AssetDetail {
  asset_id: string;
  source_segment_ids: string[];
  length_m: number;
  consequence_tier: ConsequenceTier;
  evidence_confidence: EvidenceConfidence;
  association_quality: number;
  rank_stability: number;
  evidence_basis: string;
  latitude: number;
  longitude: number;
  geometry: LineStringGeometry;
  v1: PlanFields;
  v2: PlanFields;
  rank_change: AssetRankChange | null;
}

// ---- /api/rank-changes ----
export interface RankChange {
  asset_id: string;
  rank_v1: number;
  rank_v2: number;
  delta_rank: number;
  action_v1: RecommendedAction;
  action_v2: RecommendedAction;
  reason_1: string | null;
  reason_2: string | null;
  show_in_demo: boolean;
}

export interface RankChanges {
  items: RankChange[];
}

export interface RankChangesQuery {
  demo_only?: boolean;
  limit?: number;
}

// ---- /api/audit ----
export interface CandidateResult {
  candidate_id: PolicyId;
  origin_wins: number;
  n_origins: number;
  pooled_v1_score: number;
  pooled_candidate_score: number;
  difference: number;
  bootstrap_se: number;
  required_delta: number;
  decision: CandidateDecision;
  reason: string;
}

export interface AuditEvent {
  seq: number;
  event_type: AuditEventType;
  timestamp: string;
  summary: string;
  candidate: CandidateResult | null;
  details: Record<string, unknown>;
}

export interface Audit {
  events: AuditEvent[];
}

// ---- /api/escalations ----
export interface Escalation {
  asset_id: string;
  priority_rank: number;
  consequence_tier: ConsequenceTier;
  evidence_confidence: EvidenceConfidence;
  escalation_reason: string;
  owner: string;
  required_action: string;
  response_deadline: string;
  status: EscalationStatus;
  last_reviewed: string;
}

export interface Escalations {
  items: Escalation[];
}

// ---- /api/not-covered ----
export interface NotCoveredItem {
  coverage_issue_id: string;
  scope: string;
  description: string;
  why_not_covered: string;
  required_evidence: string;
  ui_severity: UiSeverity;
  source_note: string;
}

export interface NotCovered {
  items: NotCoveredItem[];
}

// ---- /api/data-quality ----
export interface DataQuality {
  rows_dropped_missing_coordinates: number;
  match_rate_by_origin: Record<string, number>;
  match_rate_by_era: Record<string, number>;
  unmatched_share_by_era: Record<string, number>;
  unreachable_final_test_share: number;
  future_year_pipe_rows_excluded: number;
  planned_rows_excluded: number;
  inactive_sensitivity: {
    included_capture_5pct: number;
    excluded_capture_5pct: number;
  };
  retired_status_strata: Record<string, number>;
  notes: string[];
}
