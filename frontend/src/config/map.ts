// Frontend-only map display constants. Colours mirror styles/tokens.css
// (MapLibre paint expressions cannot read CSS variables).
import type { EvidenceConfidence } from '../types/api';

export const CONFIDENCE_COLORS: Record<EvidenceConfidence, string> = {
  HIGH: '#0b6e99', // --color-conf-high
  MEDIUM: '#b26a00', // --color-conf-medium
  LOW_VERIFY: '#8a2f86', // --color-conf-low
};

export const CONFIDENCE_LABELS: Record<EvidenceConfidence, string> = {
  HIGH: 'HIGH',
  MEDIUM: 'MEDIUM',
  LOW_VERIFY: 'LOW_VERIFY (verify before acting)',
};

export const CONFIDENCE_ORDER: EvidenceConfidence[] = ['HIGH', 'MEDIUM', 'LOW_VERIFY'];

export const MAP_BACKGROUND = '#f7f9fb'; // --color-bg
export const SELECTED_OUTLINE = '#14202e'; // --color-text

/** Calgary, used before data arrives and when there are no features. */
export const INITIAL_VIEW = { longitude: -114.0719, latitude: 51.0447, zoom: 10 };

export const LINE_WIDTH = { base: 3.5, hover: 6, selected: 6 };
export const FIT_PADDING = 64;
export const FIT_MAX_ZOOM = 14;
