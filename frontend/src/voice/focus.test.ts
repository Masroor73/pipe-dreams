import { describe, expect, it } from 'vitest';
import { FOCUS_ASSET_ZOOM, planFocus } from './focus';

const b: [[number, number], [number, number]] = [[-114.1, 51.0], [-114.0, 51.2]];
const base = { focus: '1', assetId: null, communityId: null, assetBounds: null, communityBounds: null };

describe('planFocus', () => {
  it('does nothing without focus=1', () => {
    expect(planFocus({ ...base, focus: null, assetId: 'A', assetBounds: b })).toBeNull();
  });
  it('centres on the asset at street zoom', () => {
    const p = planFocus({ ...base, assetId: 'A', assetBounds: b });
    expect(p).toEqual({ kind: 'asset', center: [-114.05, 51.1], zoom: FOCUS_ASSET_ZOOM });
    expect(FOCUS_ASSET_ZOOM).toBeGreaterThanOrEqual(17);
  });
  it('waits while the asset is not loaded', () => {
    expect(planFocus({ ...base, assetId: 'A' })).toBeNull();
  });
  it('fits the community tightly', () => {
    const p = planFocus({ ...base, communityId: 'FLN', communityBounds: b });
    expect(p).toMatchObject({ kind: 'community', bounds: b });
    expect(p && p.kind === 'community' && p.padding).toBeLessThanOrEqual(32);
  });
});
