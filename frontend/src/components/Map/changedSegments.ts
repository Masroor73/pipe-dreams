import { useEffect, useState } from 'react';
import { CHANGED_PULSE } from '../../config/map';
import { prefersReducedMotion } from '../../hooks/motion';
import type { AssetFeature } from '../../types/api';

/**
 * Asset ids selected in `shown` but not in `other`: the segments that changed between plans.
 * Pure set difference for presentation only. The API exposes no explicit "changed" field.
 */
export function changedAssetIds(shown: readonly AssetFeature[], other: readonly AssetFeature[] | null): Set<string> {
  if (!other) return new Set();
  const otherIds = new Set(other.map((f) => f.properties.asset_id));
  return new Set(shown.filter((f) => !otherIds.has(f.properties.asset_id)).map((f) => f.properties.asset_id));
}

/**
 * True briefly (CHANGED_PULSE.holdMs) whenever `key` changes and there are changed
 * segments, so unchanged ones can be dimmed. Never true under reduced motion.
 * Dimming starts in the same render that the key changes (no flash of full opacity).
 */
export function useChangedPulse(key: string, changedCount: number): boolean {
  const active = changedCount > 0 && !prefersReducedMotion();
  const [seenKey, setSeenKey] = useState<string | null>(null);
  const [dimmed, setDimmed] = useState(active);
  if (key !== seenKey) {
    setSeenKey(key);
    setDimmed(active);
  }
  useEffect(() => {
    if (!dimmed) return;
    const t = setTimeout(() => setDimmed(false), CHANGED_PULSE.holdMs);
    return () => clearTimeout(t);
  }, [dimmed, key]);
  return dimmed && active;
}
