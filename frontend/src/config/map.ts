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
  base: [[9, 4], [11, 5], [13, 6], [15, 8], [17, 12]],
  hover: [[9, 6], [11, 7], [13, 8.5], [15, 11], [17, 15]],
  selected: [[9, 7], [11, 8], [13, 9.5], [15, 12], [17, 16]],
} as const;
export const CASING_EXTRA = 3; // white casing is this many px wider than the line
export const HALO_EXTRA = 8; // accent halo extra width around the selected line
export const CASING_COLOR = '#ffffff'; // --color-surface
export const HALO_COLOR = '#0b6e99'; // --color-accent
export const SVG_LINE_WIDTH = { base: 5, hover: 7, selected: 9 }; // mirrored in Map.module.css

/** Where MapLibre's worker files are served (see vite.config.ts). */
export const MAPLIBRE_WORKER_PATH = 'maplibre/maplibre-gl-worker.mjs';
export const FIT_PADDING = 64;
export const FIT_PADDING_COMPACT = 32; // used when the map is narrower than FIT_COMPACT_BELOW_PX
export const FIT_COMPACT_BELOW_PX = 640;
export const FIT_MAX_ZOOM = 14;
export const FIT_EASE_MS = 400; // animated refit when the plan changes; 0 under prefers-reduced-motion
/** Mirrors --panel-width in tokens.css: the asset panel covers this much of the map's right side. */
export const FIT_PANEL_WIDTH_PX = 480;
/** If less than this much map would remain beside the panel, ignore the panel (it is full-width on small screens). */
export const FIT_MIN_VISIBLE_PX = 300;

/** Online vector basemap (OpenFreeMap Positron: free, no key). Attribution comes from the style's sources. */
export const BASEMAP_STYLE_URL = 'https://tiles.openfreemap.org/styles/positron';
/** If the basemap style has not loaded within this long, switch to the offline style. */
export const BASEMAP_LOAD_TIMEOUT_MS = 4000;
export const BASEMAP_OFFLINE_NOTE = 'Basemap offline';

/** Changed-segment emphasis (V1/V2 plan difference). Unchanged segments dim, hold, then return to full opacity. */
export const CHANGED_PULSE = {
  dimOpacity: 0.35,
  /** Time unchanged segments stay dimmed before returning. */
  holdMs: 250,
  /** MapLibre paint transition back to full opacity (linear; MapLibre has no easing option). */
  returnMs: 500,
} as const;

/** At or below this width the asset panel is a bottom sheet (mirrors the CSS media query). */
export const SHEET_MAX_WIDTH_PX = 640;
/** Bottom-sheet max height as a fraction of the viewport (mirrors max-height: 60dvh). */
export const SHEET_MAX_HEIGHT_FRAC = 0.6;
/** Ease (ms) when the map moves a selected segment out from under the asset panel; 0 under reduced motion. */
export const REVEAL_EASE_MS = 280;
/** Breathing room (px) kept between a revealed segment and the panel edge. */
export const REVEAL_MARGIN_PX = 48;
/** Outside-click handling: ignore pointer travel beyond this (a map drag), and wait this long for ?asset= to change. */
export const OUTSIDE_CLICK_DRAG_TOLERANCE_PX = 6;
export const OUTSIDE_CLICK_CLOSE_DELAY_MS = 60;

/**
 * Raster street basemap (CARTO's free light_all tiles now return an "API key required" watermark,
 * so this uses OpenStreetMap's standard tiles, desaturated so the pipe layers stand out).
 * The offline style is the fallback when tiles cannot load.
 */
export const STREET_BASEMAP_STYLE = {
  version: 8 as const,
  sources: {
    osm: {
      type: 'raster' as const,
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      maxzoom: 19,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [
    {
      id: 'osm',
      type: 'raster' as const,
      source: 'osm',
      paint: { 'raster-saturation': -0.7, 'raster-brightness-min': 0.25, 'raster-contrast': -0.1 },
    },
  ],
};
