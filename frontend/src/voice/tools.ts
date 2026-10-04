// Client tools for the ElevenLabs voice copilot. Pure functions over the API client
// plus a navigate function. The agent only ever speaks from what these return.
import type { Api } from '../lib/api';
import type { PlanId } from '../types/api';

export type Navigate = (to: string) => void;

export interface VoiceToolDeps {
  api: Api;
  navigate: Navigate;
}

const MAX_ITEMS = 8;
const FINAL_BUDGET_PCT = 5;
const LIKELIHOOD_NOTE = 'ranking signal, not failure probability';

function clampN(n: unknown, fallback: number): number {
  const v = Number(n);
  if (!Number.isFinite(v) || v < 1) return fallback;
  return Math.min(Math.floor(v), MAX_ITEMS);
}

function asPlan(p: unknown): PlanId {
  return p === 'v1' ? 'v1' : 'v2';
}

async function guard<T extends object>(fn: () => Promise<T>): Promise<T | { error: string }> {
  try {
    return await fn();
  } catch (e) {
    return { error: e instanceof Error ? e.message : 'Tool failed.' };
  }
}

export function createVoiceTools({ api, navigate }: VoiceToolDeps) {
  return {
    get_priority_plan: (params: { plan?: string; top_n?: number } = {}) =>
      guard(async () => {
        const plan = asPlan(params.plan);
        const topN = clampN(params.top_n, 5);
        const res = await api.getAssets({ plan, selected_only: true, sort: 'rank', limit: topN });
        const items = res.data.items.slice(0, MAX_ITEMS).map((a) => ({
          asset_id: a.asset_id,
          rank: a.rank,
          length_m: Number(a.length_m.toFixed(1)),
          recommended_action: a.recommended_action,
          evidence_confidence: a.evidence_confidence,
          consequence_tier: a.consequence_tier,
        }));
        const top = items[0];
        navigate(`/map?plan=${plan}${top ? `&asset=${encodeURIComponent(top.asset_id)}` : ''}`);
        return { plan: res.data.plan, selected_total: res.data.total, items };
      }),

    explain_asset: (params: { asset_id: string }) =>
      guard(async () => {
        const res = await api.getAsset(String(params.asset_id));
        const d = res.data;
        navigate(`?asset=${encodeURIComponent(d.asset_id)}`);
        return {
          asset_id: d.asset_id,
          rank_v1: d.v1.rank,
          rank_v2: d.v2.rank,
          selected_v1: d.v1.selected,
          selected_v2: d.v2.selected,
          priority_score: d.v2.priority_score,
          likelihood_score: d.v2.likelihood_score,
          likelihood_score_note: LIKELIHOOD_NOTE,
          consequence_tier: d.consequence_tier,
          evidence_confidence: d.evidence_confidence,
          recommended_action: d.v2.recommended_action,
          revision_reason: d.v2.revision_reason,
          evidence_basis: d.evidence_basis,
        };
      }),

    compare_v1_v2: () =>
      guard(async () => {
        const [ov, audit] = await Promise.all([api.getOverview(), api.getAudit()]);
        const o = ov.data;
        const candidates = audit.data.events
          .filter((e) => e.candidate && (e.event_type === 'ACCEPT' || e.event_type === 'REJECT'))
          .slice(0, MAX_ITEMS)
          .map((e) => {
            const c = e.candidate!;
            return {
              candidate: c.candidate_id,
              decision: c.decision === 'ACCEPT' ? 'PASSED' : 'FAILED',
              wins: `${c.origin_wins} of ${c.n_origins} origins`,
              improvement: Number(c.difference.toFixed(4)),
              pass_bar: Number(c.required_delta.toFixed(4)),
            };
          });
        const capture = (id: string) =>
          o.series.find((r) => r.split === 'final' && r.policy_id === id && r.budget_pct === FINAL_BUDGET_PCT)
            ?.asset_capture ?? null;
        navigate('/audit');
        return {
          v1_policy: o.v1_policy_id,
          selected_policy: o.selected_policy_id,
          v2_equals_v1: o.v2_equals_v1,
          candidates,
          final_test_asset_capture_at_5pct: {
            v2: capture(o.selected_policy_id),
            v1: capture(o.v1_policy_id),
            count_only: capture('count_only'),
          },
        };
      }),

    get_community_priorities: (params: { top_n?: number } = {}) =>
      guard(async () => {
        const topN = clampN(params.top_n, 5);
        const res = await api.getCommunities();
        const items = [...res.data.items]
          .sort((a, b) => (b.historical_breaks_per_km ?? -1) - (a.historical_breaks_per_km ?? -1))
          .slice(0, topN)
          .map((c) => ({
            community_id: c.community_id,
            name: c.community_name,
            breaks_per_km: c.historical_breaks_per_km === null ? null : Number(c.historical_breaks_per_km.toFixed(1)),
          }));
        navigate('/communities');
        return { cutoff_year: res.data.cutoff_year, items };
      }),

    focus_community: (params: { community_id: string }) =>
      guard(async () => {
        const id = String(params.community_id);
        navigate(`/communities?community=${encodeURIComponent(id)}`);
        const [comms, all, selected] = await Promise.all([
          api.getCommunities(),
          api.getAssets({ community_id: id, limit: 1 }),
          api.getAssets({ community_id: id, selected_only: true, limit: 1 }),
        ]);
        const c = comms.data.items.find((x) => x.community_id === id);
        return {
          community_id: id,
          name: c?.community_name ?? null,
          breaks_per_km: c?.historical_breaks_per_km == null ? null : Number(c.historical_breaks_per_km.toFixed(1)),
          pipes_total: all.data.total,
          pipes_selected_for_inspection: selected.data.total,
        };
      }),
  };
}

export type VoiceTools = ReturnType<typeof createVoiceTools>;
