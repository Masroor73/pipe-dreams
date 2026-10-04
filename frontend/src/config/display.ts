// Frontend-only display constants. No domain thresholds or risk logic here.
import type { BaselineId, PolicyId } from '../types/api';

/** Budget (percent of network length) used for the headline claim. */
export const HEADLINE_BUDGET_PCT = 5;

/** The single supporting line under the headline figures (what they measure). */
export const headlineCaption = (budgetPct: number): string =>
  `Share of future breaking assets caught at a ${budgetPct}% length budget (final test split)`;

/** Asset panel consequence-tier chip. Meaning of individual tiers is not defined in the docs; do not invent bands. */
export const CONSEQUENCE_TIER_LABEL = 'Consequence tier';
export const CONSEQUENCE_TIER_HELP =
  'Consequence tiers are assigned from pipe diameter and asset class and describe the impact of a failure, not its likelihood.';

/** Number of rank-change cards on the Overview page. */
export const DEMO_CARD_COUNT = 3;

/** Escalation / limits teaser sizes. */
export const ESCALATION_TEASER_COUNT = 2;
export const LIMITS_TEASER_COUNT = 3;

/** Candidate revisions in display order, with plain-language descriptions. */
export const CANDIDATE_IDS: PolicyId[] = ['C1', 'C2', 'C3', 'C4'];

export const CANDIDATE_DESCRIPTIONS: Record<string, string> = {
  C1: '2000+ history, no decay, per-asset',
  C2: 'Full history, hl10 recency, per-asset',
  C3: 'Full history, no decay, per-metre',
  C4: '2000+ history + hl10, per-asset',
};

export type ChartSeriesKey = 'v2' | 'v1' | BaselineId;

/** Series colours / dashes for the capture chart. */
export const SERIES_STYLE: Record<ChartSeriesKey, { color: string; dash?: string; width: number }> = {
  v2: { color: '#0b6e99', width: 3.5 },
  v1: { color: '#14202e', width: 2.5 },
  count_only: { color: '#6f7f90', dash: '7 5', width: 2.5 },
  organizer_cell: { color: '#8f9cab', dash: '2 5', width: 2.5 },
};

export const ORGANIZER_LABEL = 'Organizer cell baseline (event capture)';
export const COUNT_ONLY_LABEL = 'Count-only baseline';

export const CHART_HEIGHT = 360;
/** Recharts axis text size in px (project floor is 14px). */
export const CHART_FONT_PX = 15;

/**
 * Audit "agent run as cinema" scrubber. Presentation timing only.
 * Dwell is how long autoplay holds each step, by event type; PLAN_V2 holds longest
 * because the ranked list reorders on it.
 */
export const AUDIT_CINEMA = {
  dwellMs: {
    PLAN_V1: 1300,
    EVALUATE: 1100,
    DIAGNOSE: 1100,
    TEST_CANDIDATE: 900,
    ACCEPT: 1300,
    REJECT: 1100,
    PLAN_V2: 2000,
    ESCALATE: 1500,
  } as Record<string, number>,
  defaultDwellMs: 1100,
  /** Ranked list length; mirrors planning.organizer_top_n in config/policy_config.DRAFT.yaml. */
  topN: 25,
  /** FLIP move for the ranked list (on-screen movement: strong ease-in-out). */
  moveMs: 560,
  /** Keyboard / scrubber stepping: keep it under 300ms so stepping never feels laggy. */
  manualMoveMs: 240,
  moveStaggerMs: 14,
  enterMs: 260,
  /** Reduced motion: changed rows and the step caption cross-fade instead of moving. */
  reducedFadeMs: 120,
  /** Map "touched" ring. */
  pulseMs: 700,
  /** Gate row resolve stamp. */
  stampMs: 180,
} as const;

/** Capture chart: direct line labels, headline-budget marker, and whisker styling (presentation only). */
export const HEADLINE_BUDGET_LABEL = `${HEADLINE_BUDGET_PCT}% budget (headline)`;
export const ORGANIZER_LINE_LABEL = 'Organizer cell (event capture)';
export const COUNT_ONLY_LINE_LABEL = 'Count-only';
/** Text colour for the direct labels (the grey line colours fail 4.5:1 as text). */
export const SERIES_LABEL_COLOR: Record<ChartSeriesKey, string> = {
  v2: '#0b6e99',
  v1: '#14202e',
  count_only: '#4a5b6d',
  organizer_cell: '#4a5b6d',
};
/** Series that also draw confidence whiskers; the others stay as clean lines. */
export const WHISKER_SERIES: ChartSeriesKey[] = ['v2', 'count_only'];
export const CHART_MARGIN_WIDE = { top: 30, right: 232, bottom: 8, left: 8 } as const;
export const CHART_MARGIN_NARROW = { top: 30, right: 124, bottom: 8, left: 0 } as const;
/** Chart widths (px) below which the chart switches to the narrow layout. */
export const CHART_NARROW_PX = 560;
export const CHART_XAXIS_HEIGHT = 48;
export const CHART_LABEL_LINE_PX = 18;
