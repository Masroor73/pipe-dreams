import { describe, expect, it, vi } from 'vitest';
import { ApiError, buildQueryString, createApi } from './api';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

const ENV = { meta: { synthetic: true, config_hash: 'PLACEHOLDER' }, data: { items: [] } };

describe('buildQueryString', () => {
  it('serialises booleans as "true"/"false", skips undefined', () => {
    expect(buildQueryString({ plan: 'v1', selected_only: false, limit: 5, offset: undefined })).toBe(
      '?plan=v1&selected_only=false&limit=5',
    );
    expect(buildQueryString({})).toBe('');
    expect(buildQueryString(undefined)).toBe('');
  });
});

describe('real mode', () => {
  it('builds URL with query params and passes the envelope through', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(ENV));
    const api = createApi({ baseUrl: 'http://x:8000', useFixtures: false, fetchImpl });
    const res = await api.getAssets({ plan: 'v2', selected_only: true, sort: 'priority_score', limit: 10 });
    expect(fetchImpl).toHaveBeenCalledWith('http://x:8000/api/assets?plan=v2&selected_only=true&sort=priority_score&limit=10');
    expect(res).toEqual(ENV);
  });

  it('calls the right path for each endpoint', async () => {
    const fetchImpl = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse(ENV)));
    const api = createApi({ baseUrl: 'http://x', useFixtures: false, fetchImpl });
    await api.getHealth();
    await api.getOverview();
    await api.getAssetsGeoJson({ plan: 'v1' });
    await api.getAsset('seg_000001');
    await api.getRankChanges({ demo_only: false });
    await api.getAudit();
    await api.getEscalations();
    await api.getNotCovered();
    await api.getDataQuality();
    expect(fetchImpl.mock.calls.map((c) => c[0])).toEqual([
      'http://x/api/health',
      'http://x/api/overview',
      'http://x/api/assets/geojson?plan=v1',
      'http://x/api/assets/seg_000001',
      'http://x/api/rank-changes?demo_only=false',
      'http://x/api/audit',
      'http://x/api/escalations',
      'http://x/api/not-covered',
      'http://x/api/data-quality',
    ]);
  });

  it('throws ApiError parsed from the contract error body', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(jsonResponse({ error: { code: 'asset_not_found', message: "No asset with id 'abc'." } }, 404));
    const api = createApi({ baseUrl: 'http://x', useFixtures: false, fetchImpl });
    const err = await api.getAsset('abc').catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 404, code: 'asset_not_found', message: "No asset with id 'abc'." });
  });

  it('falls back to a generic code when the error body is not JSON', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response('<html>bad gateway</html>', { status: 502 }));
    const api = createApi({ baseUrl: 'http://x', useFixtures: false, fetchImpl });
    const err = await api.getOverview().catch((e: unknown) => e);
    expect(err).toMatchObject({ status: 502, code: 'http_error' });
  });

  it('wraps network failures', async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));
    const api = createApi({ baseUrl: 'http://x', useFixtures: false, fetchImpl });
    const err = await api.getAudit().catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 0, code: 'network_error', message: 'Failed to fetch' });
  });
});

describe('fixture mode', () => {
  const api = createApi({ baseUrl: 'http://unused', useFixtures: true, fixtureDelayMs: 0 });

  it('never calls fetch and returns contract-shaped, synthetic envelopes', async () => {
    const fetchImpl = vi.fn();
    const a = createApi({ baseUrl: 'http://unused', useFixtures: true, fixtureDelayMs: 0, fetchImpl });
    const overview = await a.getOverview();
    expect(overview.meta).toEqual({ synthetic: true, config_hash: 'PLACEHOLDER' });
    expect(overview.data.series.length).toBeGreaterThan(0);
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('returns health unwrapped', async () => {
    const h = await api.getHealth();
    expect(h).toMatchObject({ status: 'ok', artifacts_loaded: true, synthetic: true });
  });

  it('returns details for a known asset and 404s on an unknown one', async () => {
    const ok = await api.getAsset('seg_000001');
    expect(ok.data.asset_id).toBe('seg_000001');
    const err = await api.getAsset('nope').catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 404, code: 'asset_not_found' });
  });

  it('picks the v1 or v2 geojson by plan', async () => {
    const v1 = await api.getAssetsGeoJson({ plan: 'v1', selected_only: false });
    const v2 = await api.getAssetsGeoJson({ plan: 'v2', selected_only: false });
    expect(v1.data.features).toHaveLength(60);
    expect(v2.data.features).toHaveLength(60);
    const r1 = Object.fromEntries(v1.data.features.map((f) => [f.id, f.properties.rank]));
    const r2 = Object.fromEntries(v2.data.features.map((f) => [f.id, f.properties.rank]));
    expect(r1).not.toEqual(r2);
  });

  it('defaults geojson to selected_only=true', async () => {
    const sel = await api.getAssetsGeoJson();
    expect(sel.data.features.length).toBeGreaterThan(0);
    expect(sel.data.features.length).toBeLessThan(60);
    expect(sel.data.features.every((f) => f.properties.selected)).toBe(true);
  });

  it('defaults rank changes to demo_only=true', async () => {
    const demo = await api.getRankChanges();
    const all = await api.getRankChanges({ demo_only: false });
    expect(demo.data.items.every((i) => i.show_in_demo)).toBe(true);
    expect(demo.data.items.length).toBeGreaterThanOrEqual(3);
    expect(all.data.items.length).toBeGreaterThan(demo.data.items.length);
  });

  it('applies paging and filtering to the asset list', async () => {
    const page = await api.getAssets({ limit: 5, offset: 2 });
    expect(page.data.total).toBe(60);
    expect(page.data.items).toHaveLength(5);
    const v1 = await api.getAssets({ plan: 'v1', limit: 1 });
    expect(v1.data.plan).toBe('v1');
    expect(v1.data.items[0]?.rank).toBe(1);
  });
});
