import { useCallback, useEffect, useRef, useState } from 'react';
import { BASEMAP_LOAD_TIMEOUT_MS } from '../../config/map';

export type BasemapMode = 'online' | 'offline';

/** A style-level failure has no tile/source attached; tile 404s after the style loaded must not count. */
export function isStyleLevelError(e: { sourceId?: string; tile?: unknown } | undefined | null): boolean {
  return !e?.sourceId && !e?.tile;
}

/**
 * Decides whether the online basemap is usable. Goes offline (once, permanently) if the
 * style errors or has not loaded before the timeout. Later errors after the style loaded are ignored.
 */
export function useBasemap(timeoutMs: number = BASEMAP_LOAD_TIMEOUT_MS) {
  const [mode, setMode] = useState<BasemapMode>('online');
  const styleLoaded = useRef(false);

  useEffect(() => {
    if (mode !== 'online') return;
    const t = setTimeout(() => {
      if (!styleLoaded.current) setMode('offline');
    }, timeoutMs);
    return () => clearTimeout(t);
  }, [mode, timeoutMs]);

  const onStyleLoaded = useCallback(() => {
    styleLoaded.current = true;
  }, []);

  const onMapError = useCallback((e: { sourceId?: string; tile?: unknown } | undefined) => {
    if (!styleLoaded.current && isStyleLevelError(e)) setMode('offline');
  }, []);

  return { mode, onStyleLoaded, onMapError };
}
