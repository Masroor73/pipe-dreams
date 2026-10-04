import type { AssetListItem } from '../../types/api';

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
