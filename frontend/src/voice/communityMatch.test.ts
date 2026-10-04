import { describe, expect, it, vi } from 'vitest';
import { resolveCommunity } from './communityMatch';
import { createVoiceTools } from './tools';

const items = [
  { community_id: 'FLN', community_name: 'FOREST LAWN' },
  { community_id: 'FLI', community_name: 'FOREST LAWN INDUSTRIAL' },
  { community_id: 'BEL', community_name: 'BELTLINE' },
  { community_id: 'MIS', community_name: 'MISSION' },
  { community_id: 'MAN', community_name: 'MANCHESTER' },
  { community_id: 'MNI', community_name: 'MANCHESTER INDUSTRIAL' },
];

describe('resolveCommunity', () => {
  it('exact, case and filler words ignored', () => {
    expect(resolveCommunity('forest lawn', items)).toEqual({ kind: 'match', item: items[0] });
    expect(resolveCommunity('The Beltline community', items)).toEqual({ kind: 'match', item: items[2] });
  });
  it('prefix and contains', () => {
    expect(resolveCommunity('miss', items)).toEqual({ kind: 'match', item: items[3] });
    expect(resolveCommunity('lawn industrial', items)).toEqual({ kind: 'match', item: items[1] });
  });
  it('fuzzy', () => {
    expect(resolveCommunity('Beltlin', items)).toMatchObject({ kind: 'match' });
    expect(resolveCommunity('Misson', items)).toEqual({ kind: 'match', item: items[3] });
  });
  it('ambiguous returns up to 3 candidates', () => {
    const r = resolveCommunity('manchester', [...items, { community_id: 'MX', community_name: 'MANCHESTER X' }]);
    expect(r.kind).toBe('match'); // exact name wins
    const amb = resolveCommunity('forest', items);
    expect(amb.kind).toBe('ambiguous');
    if (amb.kind === 'ambiguous') expect(amb.candidates.length).toBeLessThanOrEqual(3);
  });
  it('not found', () => {
    expect(resolveCommunity('zzzzzz', items)).toEqual({ kind: 'none' });
  });
});

describe('community tools by name', () => {
  const mk = (n: number) =>
    Array.from({ length: n }, (_, i) => ({ community_id: `C${i}`, community_name: `NAME ${i}`, historical_breaks_per_km: i }));
  const setup = (list: unknown[]) => {
    const api = {
      getCommunities: vi.fn(async () => ({ meta: {}, data: { cutoff_year: 2022, items: list } })),
      getAssets: vi.fn(async () => ({ meta: {}, data: { total: 7, items: [] } })),
    };
    const navigate = vi.fn();
    return { navigate, tools: createVoiceTools({ api: api as never, navigate }) };
  };
  it('focuses by spoken name', async () => {
    const { navigate, tools } = setup(items.map((c) => ({ ...c, historical_breaks_per_km: 1 })));
    const r = await tools.focus_community({ name: 'mission' });
    expect(navigate).toHaveBeenCalledWith('/communities?community=MIS&focus=1');
    expect(r).toMatchObject({ community_id: 'MIS', name: 'MISSION' });
  });
  it('returns candidates when ambiguous and error when unknown', async () => {
    const { navigate, tools } = setup(items.map((c) => ({ ...c, historical_breaks_per_km: 1 })));
    expect(await tools.focus_community({ name: 'forest' })).toMatchObject({ ambiguous: true });
    expect(await tools.focus_community({ name: 'zzzzzz' })).toHaveProperty('error');
    expect(navigate).not.toHaveBeenCalled();
  });
  it('caps top_n at 25', async () => {
    const { tools } = setup(mk(40));
    const r = (await tools.get_community_priorities({ top_n: 99 })) as { items: { rank: number }[] };
    expect(r.items).toHaveLength(25);
    expect(r.items[0]?.rank).toBe(1);
    expect(((await tools.get_community_priorities({})) as { items: unknown[] }).items).toHaveLength(5);
  });
});

describe('replay_agent_run', () => {
  it('opens the audit page with the one-shot replay flag', async () => {
    const navigate = vi.fn();
    const tools = createVoiceTools({ api: {} as never, navigate });
    const r = (await tools.replay_agent_run()) as { started: boolean; note: string };
    expect(navigate).toHaveBeenCalledWith('/audit?replay=1');
    expect(r.started).toBe(true);
    expect(r.note).toMatch(/Nothing is re-computed/);
  });
});
