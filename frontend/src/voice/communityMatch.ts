// Resolve a spoken community name against the full community list. Pure.
export interface CommunityLite {
  community_id: string;
  community_name: string;
}

export type CommunityMatch =
  | { kind: 'match'; item: CommunityLite }
  | { kind: 'ambiguous'; candidates: CommunityLite[] }
  | { kind: 'none' };

const STOP = new Set(['the', 'community', 'neighbourhood', 'neighborhood', 'of', 'in']);
export const MAX_FUZZY_DISTANCE = 2;

export function normName(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((w) => w && !STOP.has(w))
    .join(' ');
}

export function levenshtein(a: string, b: string): number {
  const prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let diag = prev[0]!;
    prev[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const tmp = prev[j]!;
      prev[j] = Math.min(prev[j]! + 1, prev[j - 1]! + 1, diag + (a[i - 1] === b[j - 1] ? 0 : 1));
      diag = tmp;
    }
  }
  return prev[b.length]!;
}

function pick(list: CommunityLite[]): CommunityMatch {
  if (list.length === 1) return { kind: 'match', item: list[0]! };
  return { kind: 'ambiguous', candidates: list.slice(0, 3) };
}

export function resolveCommunity(query: string, items: CommunityLite[]): CommunityMatch {
  const q = normName(query);
  if (!q) return { kind: 'none' };
  const named = items.map((c) => ({ c, n: normName(c.community_name) }));
  const exact = named.filter((x) => x.n === q).map((x) => x.c);
  if (exact.length) return pick(exact);
  const starts = named.filter((x) => x.n.startsWith(q)).map((x) => x.c);
  if (starts.length) return pick(starts);
  const contains = named.filter((x) => x.n.includes(q)).map((x) => x.c);
  if (contains.length) return pick(contains);
  const fuzzy = named
    .map((x) => ({ c: x.c, d: levenshtein(q, x.n) }))
    .filter((x) => x.d <= MAX_FUZZY_DISTANCE)
    .sort((a, b) => a.d - b.d);
  if (!fuzzy.length) return { kind: 'none' };
  const best = fuzzy[0]!.d;
  return pick(fuzzy.filter((x) => x.d === best).map((x) => x.c));
}
