import {
  FIT_COMPACT_BELOW_PX,
  FIT_MIN_VISIBLE_PX,
  FIT_PADDING,
  FIT_PADDING_COMPACT,
  FIT_PANEL_WIDTH_PX,
} from '../../config/map';
import type { AssetFeature } from '../../types/api';

export type Bounds = [[number, number], [number, number]];

/** Bounding box of all vertices, for camera framing only. */
export function featureBounds(features: AssetFeature[]): Bounds | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const f of features) {
    for (const [x, y] of f.geometry.coordinates) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
  }
  if (!Number.isFinite(minX)) return null;
  return [
    [minX, minY],
    [maxX, maxY],
  ];
}

export interface FitPadding {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

/** Camera padding for fitting the lines: compact on narrow maps, and keeps lines clear of the asset panel when it sits beside the map. */
export function fitPadding(mapWidth: number, panelOpen: boolean): FitPadding {
  const base = mapWidth > 0 && mapWidth < FIT_COMPACT_BELOW_PX ? FIT_PADDING_COMPACT : FIT_PADDING;
  const panelBesideMap = panelOpen && mapWidth - FIT_PANEL_WIDTH_PX >= FIT_MIN_VISIBLE_PX;
  return { top: base, bottom: base, left: base, right: base + (panelBesideMap ? FIT_PANEL_WIDTH_PX : 0) };
}

export function hasWebGL(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2') ?? canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

export interface SvgLine {
  asset_id: string;
  d: string;
}

export const SVG_VIEW = { width: 1000, height: 640, pad: 40 };

/** Equirectangular projection (longitude scaled by cos(mid-latitude)) into the SVG viewBox. */
export function projectFeatures(features: AssetFeature[]): SvgLine[] {
  const b = featureBounds(features);
  if (!b) return [];
  const [[minLon, minLat], [maxLon, maxLat]] = b;
  const k = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
  const w = Math.max((maxLon - minLon) * k, 1e-9);
  const h = Math.max(maxLat - minLat, 1e-9);
  const { width, height, pad } = SVG_VIEW;
  const scale = Math.min((width - 2 * pad) / w, (height - 2 * pad) / h);
  const offX = (width - w * scale) / 2;
  const offY = (height - h * scale) / 2;
  return features.map((f) => ({
    asset_id: f.properties.asset_id,
    d: f.geometry.coordinates
      .map(([lon, lat], i) => {
        const x = offX + (lon - minLon) * k * scale;
        const y = offY + (maxLat - lat) * scale;
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(' '),
  }));
}
