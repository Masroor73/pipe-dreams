import { describe, expect, it } from 'vitest';
import type { AssetListItem } from '../../types/api';
import { assetDots } from './dots';

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

describe('assetDots', () => {
  it('plots each item at [longitude, latitude] unchanged', () => {
    const fc = assetDots([item('a', 51.038, -114.076, true), item('b', 51.04, -114.07, false)]);
    expect(fc.features).toHaveLength(2);
    expect(fc.features[0]!.geometry.coordinates).toEqual([-114.076, 51.038]);
    expect(fc.features[0]!.properties).toMatchObject({ asset_id: 'a', selected: true });
    expect(fc.features[1]!.properties.selected).toBe(false);
  });
});
