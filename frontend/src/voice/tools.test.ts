import { describe, expect, it, vi } from 'vitest';
import type { Api } from '../lib/api';
import { createVoiceTools } from './tools';

const meta = { synthetic: false, config_hash: 'x' };
const env = <T,>(data: T) => ({ meta, data });

function asset(i: number) {
  return {
    asset_id: `PIPE-000${i}`, rank: i, selected: true, length_m: 100.4 + i, priority_score: 1,
    consequence_tier: 'HIGH', evidence_confidence: 'HIGH', recommended_action: 'INSPECT', latitude: 0, longitude: 0,
  };
}

function setup(over: Record<string, unknown> = {}) {
  const api = {
    getAssets: vi.fn(async (q: { limit?: number; plan?: string; community_id?: string }) =>
      env({ plan: q.plan ?? 'v2', total: q.community_id ? 42 : 3, limit: q.limit ?? 100, offset: 0, items: [asset(1), asset(2), asset(3)] }),
    ),
    getAsset: vi.fn(async () =>
      env({
        asset_id: 'PIPE-0001', consequence_tier: 'HIGH', evidence_confidence: 'LOW_VERIFY', evidence_basis: 'basis',
        v1: { rank: 9, selected: false, likelihood_score: 0.1, priority_score: 0.2, recommended_action: 'MONITOR', revision_reason: null },
        v2: { rank: 1, selected: true, likelihood_score: 0.5, priority_score: 0.7, recommended_action: 'VERIFY', revision_reason: 'moved up' },
      }),
    ),
    getOverview: vi.fn(async () =>
      env({
        v1_policy_id: 'V1', selected_policy_id: 'C3', v2_equals_v1: false,
        series: [
          { split: 'final', policy_id: 'C3', budget_pct: 5, asset_capture: 0.29 },
          { split: 'final', policy_id: 'V1', budget_pct: 5, asset_capture: 0.2 },
          { split: 'final', policy_id: 'count_only', budget_pct: 5, asset_capture: 0.22 },
        ],
      }),
    ),
    getAudit: vi.fn(async () =>
      env({
        events: [
          { event_type: 'EVALUATE', candidate: null },
          { event_type: 'REJECT', candidate: { candidate_id: 'C1', origin_wins: 1, n_origins: 3, difference: -0.0023, required_delta: 0.0048, decision: 'REJECT' } },
          { event_type: 'ACCEPT', candidate: { candidate_id: 'C3', origin_wins: 3, n_origins: 3, difference: 0.067, required_delta: 0.0076, decision: 'ACCEPT' } },
        ],
      }),
    ),
    getCommunities: vi.fn(async () =>
      env({
        cutoff_year: 2022,
        items: [
          { community_id: 'AAA', community_name: 'LOW', historical_breaks_per_km: 5.55 },
          { community_id: 'BBB', community_name: 'HIGH', historical_breaks_per_km: 53.61 },
          { community_id: 'CCC', community_name: 'NONE', historical_breaks_per_km: null },
        ],
      }),
    ),
    ...over,
  } as unknown as Api;
  const navigate = vi.fn();
  return { api, navigate, tools: createVoiceTools({ api, navigate }) };
}

describe('voice tools', () => {
  it('get_priority_plan returns compact rows and focuses the map on the top asset', async () => {
    const { api, navigate, tools } = setup();
    const r = (await tools.get_priority_plan({ top_n: 3 })) as { plan: string; items: { asset_id: string }[] };
    expect(api.getAssets).toHaveBeenCalledWith({ plan: 'v2', selected_only: true, sort: 'rank', limit: 3 });
    expect(r.plan).toBe('v2');
    expect(r.items).toHaveLength(3);
    expect(r.items[0]).toMatchObject({ asset_id: 'PIPE-0001', rank: 1, length_m: 101.4, recommended_action: 'INSPECT' });
    expect(navigate).toHaveBeenCalledWith('/map?plan=v2&asset=PIPE-0001');
  });

  it('get_priority_plan caps top_n at 8 and honours v1', async () => {
    const { api, tools } = setup();
    await tools.get_priority_plan({ plan: 'v1', top_n: 50 });
    expect(api.getAssets).toHaveBeenCalledWith({ plan: 'v1', selected_only: true, sort: 'rank', limit: 8 });
  });

  it('explain_asset labels the likelihood score and opens the panel on the current page', async () => {
    const { navigate, tools } = setup();
    const r = (await tools.explain_asset({ asset_id: 'PIPE-0001' })) as Record<string, unknown>;
    expect(r).toMatchObject({ rank_v1: 9, rank_v2: 1, selected_v2: true, evidence_confidence: 'LOW_VERIFY', revision_reason: 'moved up' });
    expect(r.likelihood_score_note).toBe('ranking signal, not failure probability');
    expect(navigate).toHaveBeenCalledWith('?asset=PIPE-0001');
  });

  it('compare_v1_v2 reports decisions as PASSED/FAILED and the final capture', async () => {
    const { navigate, tools } = setup();
    const r = (await tools.compare_v1_v2()) as {
      selected_policy: string;
      candidates: { candidate: string; decision: string; wins: string }[];
      final_test_asset_capture_at_5pct: Record<string, number>;
    };
    expect(r.selected_policy).toBe('C3');
    expect(r.candidates.map((c) => [c.candidate, c.decision])).toEqual([['C1', 'FAILED'], ['C3', 'PASSED']]);
    expect(r.candidates[1]?.wins).toBe('3 of 3 origins');
    expect(r.final_test_asset_capture_at_5pct).toEqual({ v2: 0.29, v1: 0.2, count_only: 0.22 });
    expect(navigate).toHaveBeenCalledWith('/audit');
  });

  it('get_community_priorities sorts by breaks per km and navigates', async () => {
    const { navigate, tools } = setup();
    const r = (await tools.get_community_priorities({ top_n: 2 })) as { items: { name: string; breaks_per_km: number }[] };
    expect(r.items.map((i) => i.name)).toEqual(['HIGH', 'LOW']);
    expect(r.items[0]?.breaks_per_km).toBe(53.6);
    expect(navigate).toHaveBeenCalledWith('/communities');
  });

  it('focus_community navigates and returns pipe counts', async () => {
    const { api, navigate, tools } = setup();
    const r = (await tools.focus_community({ community_id: 'BBB' })) as Record<string, unknown>;
    expect(navigate).toHaveBeenCalledWith('/communities?community=BBB');
    expect(api.getAssets).toHaveBeenCalledWith({ community_id: 'BBB', limit: 1 });
    expect(api.getAssets).toHaveBeenCalledWith({ community_id: 'BBB', selected_only: true, limit: 1 });
    expect(r).toMatchObject({ name: 'HIGH', pipes_total: 42, pipes_selected_for_inspection: 42 });
  });

  it('returns an error object instead of throwing', async () => {
    const { tools } = setup({ getAsset: vi.fn().mockRejectedValue(new Error('No asset')) });
    expect(await tools.explain_asset({ asset_id: 'nope' })).toEqual({ error: 'No asset' });
  });
});
