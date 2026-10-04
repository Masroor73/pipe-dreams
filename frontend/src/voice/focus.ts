// Focus requests: the voice copilot adds `focus=1` to the URL; the map consumes it once and
// flies to the asset or community. Pure planning logic so it can be tested without a map.
export const FOCUS_PARAM = 'focus';
export const FOCUS_ASSET_ZOOM = 17.5;
export const FOCUS_COMMUNITY_PADDING = 24;
export const FOCUS_COMMUNITY_MAX_ZOOM = 16;
export const FOCUS_DURATION_MS = 1400;

export type LngLatBounds = [[number, number], [number, number]];

export type FocusPlan =
  | { kind: 'asset'; center: [number, number]; zoom: number }
  | { kind: 'community'; bounds: LngLatBounds; padding: number; maxZoom: number };

export interface FocusInput {
  focus: string | null;
  assetId: string | null;
  communityId: string | null;
  /** Bounds of the asset line, if it is loaded on this map. */
  assetBounds: LngLatBounds | null;
  /** Bounds of the community polygon, if loaded. */
  communityBounds: LngLatBounds | null;
}

/** Returns what to do now, or null (nothing requested, or data not loaded yet: keep waiting). */
export function planFocus(i: FocusInput): FocusPlan | null {
  if (i.focus !== '1') return null;
  if (i.assetId) {
    if (!i.assetBounds) return null;
    const [[x0, y0], [x1, y1]] = i.assetBounds;
    return { kind: 'asset', center: [(x0 + x1) / 2, (y0 + y1) / 2], zoom: FOCUS_ASSET_ZOOM };
  }
  if (i.communityId && i.communityBounds) {
    return { kind: 'community', bounds: i.communityBounds, padding: FOCUS_COMMUNITY_PADDING, maxZoom: FOCUS_COMMUNITY_MAX_ZOOM };
  }
  return null;
}
