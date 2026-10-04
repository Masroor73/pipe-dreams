import { useEffect } from 'react';
import { api } from '../lib/api';
import { useReportMeta } from '../lib/synthetic';
import type {
  AssetGeoJsonQuery,
  AssetListQuery,
  Health,
  RankChangesQuery,
} from '../types/api';
import { useApiResource, useRawResource } from './useApiResource';

export { useApiResource, useRawResource } from './useApiResource';
export type { Resource, ResourceStatus } from './useApiResource';

/** Health is not enveloped; its `synthetic` flag also drives the banner. */
export function useHealth() {
  const result = useRawResource<Health>(() => api.getHealth());
  const report = useReportMeta();
  const synthetic = result.data?.synthetic;
  useEffect(() => {
    // null = degraded (unknown); the health gate shows no data, so nothing to report.
    if (synthetic === undefined || synthetic === null) return;
    report('health', { synthetic, config_hash: '' });
    return () => report('health', null);
  }, [synthetic, report]);
  return result;
}

export const useOverview = () => useApiResource(() => api.getOverview());

export function useAssets(query: AssetListQuery = {}) {
  return useApiResource(() => api.getAssets(query), [JSON.stringify(query)]);
}

export function useAssetsGeoJson(query: AssetGeoJsonQuery = {}) {
  return useApiResource(() => api.getAssetsGeoJson(query), [JSON.stringify(query)]);
}

export function useAsset(id: string) {
  return useApiResource(() => api.getAsset(id), [id]);
}

export function useRankChanges(query: RankChangesQuery = {}) {
  return useApiResource(() => api.getRankChanges(query), [JSON.stringify(query)]);
}

export const useAudit = () => useApiResource(() => api.getAudit());
export const useEscalations = () => useApiResource(() => api.getEscalations());
export const useNotCovered = () => useApiResource(() => api.getNotCovered());
export const useDataQuality = () => useApiResource(() => api.getDataQuality());
