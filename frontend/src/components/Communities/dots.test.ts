import { describe, expect, it } from 'vitest';
import type { AssetFeature, AssetListItem } from '../../types/api';
import { assetDots, featurePoints, isProjected } from './dots';

const item = (id: string, lat: number, lon: number, selected: boolean): AssetListItem => ({
  asset_id: id,
  rank: 1,
  selected,
  length_m: 0.7,
  priority_score: 1,
  consequence_tier: 'T3',
  evidence_confidence: 'HIGH',
  recommended_action: 'INSPECT',
  latitude: lat,
  longitude: lon,
});

const feat = (id: string, coords: unknown): AssetFeature =>
  ({
    type: 'Feature',
    id,
    geometry: { type: 'MultiLineString', coordinates: coords },
    properties: {
      asset_id: id,
      rank: 1,
      selected: true,
      consequence_tier: 'T3',
      evidence_confidence: 'HIGH',
      recommended_action: 'INSPECT',
    },
  }) as unknown as AssetFeature;

describe('assetDots', () => {
  it('plots each item at [longitude, latitude] unchanged', () => {
    const fc = assetDots([item('a', 51.038, -114.076, true), item('b', 51.04, -114.07, false)]);
    expect(fc.features).toHaveLength(2);
    expect(fc.features[0]!.geometry.coordinates).toEqual([-114.076, 51.038]);
    expect(fc.features[0]!.properties).toMatchObject({ asset_id: 'a', selected: true });
    expect(fc.features[1]!.properties.selected).toBe(false);
  });
});

describe('geometry helpers', () => {
  it('picks the first vertex of line and multi-line coordinates', () => {
    const fc = featurePoints([
      feat('a', [[[-114.07, 51.03], [-114.06, 51.04]]]),
      feat('b', [[-114.1, 51.0], [-114.0, 51.1]]),
    ]);
    expect(fc.features.map((f) => f.geometry.coordinates)).toEqual([
      [-114.07, 51.03],
      [-114.1, 51.0],
    ]);
  });

  it('detects projected coordinates', () => {
    expect(isProjected([feat('a', [[[-5303.4, 5655734.3]]])])).toBe(true);
    expect(isProjected([feat('a', [[[-114.07, 51.03]]])])).toBe(false);
  });
});
