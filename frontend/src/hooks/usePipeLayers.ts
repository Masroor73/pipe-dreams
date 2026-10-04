import { useMemo } from 'react';
import { assetDots, featurePoints, isProjected } from '../components/Communities/dots';
import type { DotCollection } from '../components/Communities/dots';
import type { AssetFeatureCollection, AssetGeoJsonQuery, AssetListQuery } from '../types/api';
import { useAllAssets, useAssetsGeoJson } from './index';
import type { ResourceStatus } from './index';

const NO_POINTS: DotCollection = { type: 'FeatureCollection', features: [] };

export interface PipeLayers {
  status: ResourceStatus;
  errorMessage?: string;
  reload: () => void;
  /** Lines to draw; null when the API geometry is not lon/lat degrees. */
  lines: AssetFeatureCollection | null;
  /** Small circles: first vertices of the lines, or latitude/longitude from /api/assets as a fallback. */
  points: DotCollection;
}

/**
 * One /api/assets/geojson request. If its coordinates are still projected (not degrees),
 * falls back to plotting the WGS84 latitude/longitude of /api/assets items as dots.
 */
export function usePipeLayers(geoQuery: AssetGeoJsonQuery, listQuery: AssetListQuery, enabled = true): PipeLayers {
  const geo = useAssetsGeoJson(geoQuery, enabled);
  const projected = geo.status === 'success' && !!geo.data && isProjected(geo.data.features);
  const list = useAllAssets(listQuery, projected);

  return useMemo<PipeLayers>(() => {
    if (geo.status !== 'success' || !geo.data) {
      return { status: geo.status, errorMessage: geo.error?.message, reload: geo.reload, lines: null, points: NO_POINTS };
    }
    if (!projected) {
      return { status: 'success', reload: geo.reload, lines: geo.data, points: featurePoints(geo.data.features) };
    }
    return {
      status: list.status,
      errorMessage: list.error?.message,
      reload: list.reload,
      lines: null,
      points: list.data ? assetDots(list.data.items) : NO_POINTS,
    };
  }, [geo.status, geo.data, geo.error, geo.reload, projected, list.status, list.data, list.error, list.reload]);
}
