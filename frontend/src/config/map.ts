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

/** Line widths in px as [zoom, width] stops, interpolated linearly by MapLibre. >= 3px at the fitted view (~z14). */
export const LINE_WIDTH_STOPS = {
  base: [[11, 2], [13, 3.5], [15, 6], [17, 10]],
  hover: [[11, 4], [13, 6], [15, 9], [17, 14]],
  selected: [[11, 4], [13, 6.5], [15, 10], [17, 15]],
} as const;
export const CASING_EXTRA = 2; // white casing is this many px wider than the line
export const HALO_EXTRA = 8; // accent halo extra width around the selected line
export const CASING_COLOR = '#ffffff'; // --color-surface
export const HALO_COLOR = '#0b6e99'; // --color-accent
export const SVG_LINE_WIDTH = { base: 3.5, hover: 6, selected: 7 };

/** Where MapLibre's worker files are served (see vite.config.ts). */
export const MAPLIBRE_WORKER_PATH = 'maplibre/maplibre-gl-worker.mjs';
export const FIT_PADDING = 64;
export const FIT_MAX_ZOOM = 14;
