// Frontend-only display constants. No domain thresholds or risk logic here.
import type { BaselineId, PolicyId } from '../types/api';

/** Budget (percent of network length) used for the headline claim. */
export const HEADLINE_BUDGET_PCT = 5;

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
