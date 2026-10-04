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

const PAGE = 500; // API max page size (docs/API_CONTRACT.md)

/** Every page of /api/assets for one query, merged in API order. */
export function useAllAssets(query: AssetListQuery = {}, enabled = true) {
  return useApiResource(async () => {
    if (!enabled) {
      return {
        meta: { synthetic: false, config_hash: '' },
        data: { plan: 'v2' as const, total: 0, limit: PAGE, offset: 0, items: [] },
      };
    }
    const first = await api.getAssets({ ...query, limit: PAGE, offset: 0 });
    const offsets: number[] = [];
    for (let o = PAGE; o < first.data.total; o += PAGE) offsets.push(o);
    const rest = await Promise.all(offsets.map((offset) => api.getAssets({ ...query, limit: PAGE, offset })));
    const items = [...first.data.items, ...rest.flatMap((r) => r.data.items)];
    return { meta: first.meta, data: { ...first.data, limit: PAGE, offset: 0, items } };
  }, [JSON.stringify(query), enabled]);
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

export const useCommunities = () => useApiResource(() => api.getCommunities());
export const useCommunitiesGeoJson = () => useApiResource(() => api.getCommunitiesGeoJson());
