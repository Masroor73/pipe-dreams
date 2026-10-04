import { describe, expect, it } from 'vitest';
import type { AssetFeature } from '../../types/api';
import { changedAssetIds } from './changedSegments';

const f = (id: string) => ({ properties: { asset_id: id } }) as unknown as AssetFeature;

describe('changedAssetIds', () => {
  it('returns ids present in shown but not in other', () => {
    expect([...changedAssetIds([f('a'), f('b'), f('c')], [f('b'), f('d')])].sort()).toEqual(['a', 'c']);
  });
  it('returns an empty set when the other plan is not loaded', () => {
    expect(changedAssetIds([f('a')], null).size).toBe(0);
  });
  it('returns an empty set when plans are identical', () => {
    expect(changedAssetIds([f('a')], [f('a')]).size).toBe(0);
  });
});
