import type {
  AssetDetail,
  AssetFeatureCollection,
  AssetGeoJsonQuery,
  AssetList,
  AssetListItem,
  AssetListQuery,
  Audit,
  DataQuality,
  Envelope,
  Escalations,
  Health,
  NotCovered,
  Overview,
  RankChanges,
  RankChangesQuery,
} from '../types/api';

import healthFixture from '../fixtures/health.json';
import overviewFixture from '../fixtures/overview.json';
import assetsFixture from '../fixtures/assets.json';
import geojsonV1Fixture from '../fixtures/assets_geojson_v1.json';
import geojsonV2Fixture from '../fixtures/assets_geojson_v2.json';
import assetDetailsFixture from '../fixtures/asset_details.json';
import rankChangesFixture from '../fixtures/rank_changes.json';
import auditFixture from '../fixtures/audit.json';
import escalationsFixture from '../fixtures/escalations.json';
import notCoveredFixture from '../fixtures/not_covered.json';
import dataQualityFixture from '../fixtures/data_quality.json';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

export interface ApiOptions {
  baseUrl: string;
  useFixtures: boolean;
  fetchImpl?: typeof fetch;
  /** Artificial latency for fixture mode, in ms. */
  fixtureDelayMs?: number;
}

export interface Api {
  getHealth(): Promise<Health>;
  getOverview(): Promise<Envelope<Overview>>;
  getAssets(query?: AssetListQuery): Promise<Envelope<AssetList>>;
  getAssetsGeoJson(query?: AssetGeoJsonQuery): Promise<Envelope<AssetFeatureCollection>>;
  getAsset(id: string): Promise<Envelope<AssetDetail>>;
  getRankChanges(query?: RankChangesQuery): Promise<Envelope<RankChanges>>;
  getAudit(): Promise<Envelope<Audit>>;
  getEscalations(): Promise<Envelope<Escalations>>;
  getNotCovered(): Promise<Envelope<NotCovered>>;
  getDataQuality(): Promise<Envelope<DataQuality>>;
}

type QueryValue = string | number | boolean | undefined;

export function buildQueryString(query: object | undefined): string {
  if (!query) return '';
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query as Record<string, QueryValue>)) {
    if (value === undefined) continue;
    params.set(key, typeof value === 'boolean' ? (value ? 'true' : 'false') : String(value));
  }
  const s = params.toString();
  return s ? `?${s}` : '';
}

async function parseError(res: Response): Promise<ApiError> {
  let code = 'http_error';
  let message = `Request failed with status ${res.status}.`;
  try {
    const body: unknown = await res.json();
    const err = (body as { error?: { code?: unknown; message?: unknown } } | null)?.error;
    if (err && typeof err.code === 'string') code = err.code;
    if (err && typeof err.message === 'string') message = err.message;
  } catch {
    // Body was not JSON: keep the fallback code and message.
  }
  return new ApiError(res.status, code, message);
}

// ---- fixture-mode helpers (mock of the backend's paging/filtering only) ----

const FIXTURE_META = (assetsFixture as { meta: Envelope<unknown>['meta'] }).meta;
const details = assetDetailsFixture as unknown as Record<string, AssetDetail>;

function pageItems(items: AssetListItem[], q: AssetListQuery): AssetList {
  let rows = items;
  if (q.selected_only) rows = rows.filter((r) => r.selected);
  if (q.evidence_confidence) rows = rows.filter((r) => r.evidence_confidence === q.evidence_confidence);
  if (q.consequence_tier) rows = rows.filter((r) => r.consequence_tier === q.consequence_tier);
  const sort = q.sort ?? 'rank';
  rows = [...rows].sort((a, b) =>
    sort === 'priority_score' ? b.priority_score - a.priority_score : sort === 'length_m' ? b.length_m - a.length_m : a.rank - b.rank,
  );
  const limit = q.limit ?? 100;
  const offset = q.offset ?? 0;
  return { plan: q.plan ?? 'v2', total: rows.length, limit, offset, items: rows.slice(offset, offset + limit) };
}

function fixtureAssetList(q: AssetListQuery): AssetList {
  const plan = q.plan ?? 'v2';
  const base: AssetListItem[] =
    plan === 'v2'
      ? (assetsFixture.data.items as AssetListItem[])
      : Object.values(details).map((d) => ({
          asset_id: d.asset_id,
          rank: d.v1.rank,
          selected: d.v1.selected,
          length_m: d.length_m,
          priority_score: d.v1.priority_score,
          consequence_tier: d.consequence_tier,
          evidence_confidence: d.evidence_confidence,
          recommended_action: d.v1.recommended_action,
          latitude: d.latitude,
          longitude: d.longitude,
        }));
  return { ...pageItems(base, q), plan };
}

export function createApi(options: ApiOptions): Api {
  const { baseUrl, useFixtures } = options;
  const fetchImpl = options.fetchImpl ?? ((...args: Parameters<typeof fetch>) => fetch(...args));
  const delayMs = options.fixtureDelayMs ?? 150;

  async function fixture<T>(value: T): Promise<T> {
    if (delayMs > 0) await new Promise((r) => setTimeout(r, delayMs));
    return structuredClone(value);
  }

  async function real<T>(path: string, query?: object): Promise<T> {
    const url = `${baseUrl}/api${path}${buildQueryString(query)}`;
    let res: Response;
    try {
      res = await fetchImpl(url);
    } catch (e) {
      throw new ApiError(0, 'network_error', e instanceof Error ? e.message : 'Network request failed.');
    }
    if (!res.ok) throw await parseError(res);
    try {
      return (await res.json()) as T;
    } catch {
      throw new ApiError(res.status, 'invalid_response', 'The server returned a response that is not valid JSON.');
    }
  }

  return {
    getHealth: () => (useFixtures ? fixture(healthFixture as Health) : real<Health>('/health')),

    getOverview: () =>
      useFixtures ? fixture(overviewFixture as unknown as Envelope<Overview>) : real('/overview'),

    getAssets: (query = {}) =>
      useFixtures
        ? fixture({ meta: FIXTURE_META, data: fixtureAssetList(query) })
        : real('/assets', query),

    getAssetsGeoJson: (query = {}) => {
      if (!useFixtures) return real('/assets/geojson', query);
      const src = (query.plan ?? 'v2') === 'v1' ? geojsonV1Fixture : geojsonV2Fixture;
      const env = structuredClone(src) as unknown as Envelope<AssetFeatureCollection>;
      if (query.selected_only ?? true) {
        env.data.features = env.data.features.filter((f) => f.properties.selected);
      }
      return fixture(env);
    },

    getAsset: async (id) => {
      if (!useFixtures) return real(`/assets/${encodeURIComponent(id)}`);
      const d = details[id];
      if (!d) {
        if (delayMs > 0) await new Promise((r) => setTimeout(r, delayMs));
        throw new ApiError(404, 'asset_not_found', `No asset with id '${id}' in plan v2.`);
      }
      return fixture({ meta: FIXTURE_META, data: d });
    },

    getRankChanges: (query = {}) => {
      if (!useFixtures) return real('/rank-changes', query);
      const env = structuredClone(rankChangesFixture) as unknown as Envelope<RankChanges>;
      let items = env.data.items;
      if (query.demo_only ?? true) items = items.filter((i) => i.show_in_demo);
      env.data.items = items.slice(0, query.limit ?? 50);
      return fixture(env);
    },

    getAudit: () => (useFixtures ? fixture(auditFixture as unknown as Envelope<Audit>) : real('/audit')),
    getEscalations: () =>
      useFixtures ? fixture(escalationsFixture as unknown as Envelope<Escalations>) : real('/escalations'),
    getNotCovered: () =>
      useFixtures ? fixture(notCoveredFixture as unknown as Envelope<NotCovered>) : real('/not-covered'),
    getDataQuality: () =>
      useFixtures ? fixture(dataQualityFixture as unknown as Envelope<DataQuality>) : real('/data-quality'),
  };
}

const isTest = import.meta.env.MODE === 'test';

export const api: Api = createApi({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  useFixtures: import.meta.env.VITE_USE_FIXTURES === 'true',
  fixtureDelayMs: isTest ? 0 : 150,
});

export const { getHealth, getOverview, getAssets, getAssetsGeoJson, getAsset, getRankChanges, getAudit, getEscalations, getNotCovered, getDataQuality } = api;
