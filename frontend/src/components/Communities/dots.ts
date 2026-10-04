import type { AssetFeature, AssetListItem } from '../../types/api';

export interface DotProps {
  asset_id: string;
  rank: number;
  selected: boolean;
  evidence_confidence: string;
}

export interface DotCollection {
  type: 'FeatureCollection';
  features: { type: 'Feature'; geometry: { type: 'Point'; coordinates: [number, number] }; properties: DotProps }[];
}

/** One point per asset at the API-provided WGS84 latitude/longitude. No reprojection or maths. */
export function assetDots(items: AssetListItem[]): DotCollection {
  return {
    type: 'FeatureCollection',
    features: items.map((a) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [a.longitude, a.latitude] },
      properties: {
        asset_id: a.asset_id,
        rank: a.rank,
        selected: a.selected,
        evidence_confidence: a.evidence_confidence,
      },
    })),
  };
}

/** First vertex of a LineString / MultiLineString coordinate tree. No maths, just picking a vertex. */
export function firstVertex(coords: unknown): [number, number] | null {
  let c: unknown = coords;
  while (Array.isArray(c) && Array.isArray(c[0])) c = c[0];
  if (Array.isArray(c) && typeof c[0] === 'number' && typeof c[1] === 'number') return [c[0], c[1]];
  return null;
}

/** True when any feature's coordinates are not lon/lat degrees (e.g. a projected CRS in metres). */
export function isProjected(features: AssetFeature[]): boolean {
  return features.some((f) => {
    const v = firstVertex(f.geometry.coordinates);
    return !v || Math.abs(v[0]) > 180 || Math.abs(v[1]) > 90;
  });
}

/** One point per line feature at its first vertex, for the small circle layer. */
export function featurePoints(features: AssetFeature[]): DotCollection {
  const out: DotCollection['features'] = [];
  for (const f of features) {
    const v = firstVertex(f.geometry.coordinates);
    if (!v) continue;
    out.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: v },
      properties: {
        asset_id: f.properties.asset_id,
        rank: f.properties.rank,
        selected: f.properties.selected,
        evidence_confidence: f.properties.evidence_confidence,
      },
    });
  }
  return { type: 'FeatureCollection', features: out };
}
