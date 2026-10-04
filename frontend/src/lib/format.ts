// Display-only formatting. No domain logic.

export function formatPct(fraction: number | null | undefined, digits = 1): string {
  if (fraction === null || fraction === undefined || Number.isNaN(fraction)) return '—';
  return `${(fraction * 100).toFixed(digits)}%`;
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toLocaleString('en-CA', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** ISO date or timestamp -> "3 Oct 2026". Timestamps also get " 14:05 UTC" when withTime. */
export function formatDate(iso: string | null | undefined, withTime = false): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const date = d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  if (!withTime) return date;
  const time = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' });
  return `${date}, ${time} UTC`;
}

export type RankDirection = 'up' | 'down' | 'same';

/** Lower rank number = higher priority. Direction comes from the two ranks, never from delta_rank's sign. */
export function rankDirection(rankV1: number, rankV2: number): RankDirection {
  if (rankV2 < rankV1) return 'up';
  if (rankV2 > rankV1) return 'down';
  return 'same';
}

/** Places moved, always non-negative. */
export function rankShiftMagnitude(rankV1: number, rankV2: number): number {
  return Math.abs(rankV1 - rankV2);
}

/** As shown to people: "↑ 7687" when rank went from 7736 to 49. */
export function formatRankMove(rankV1: number, rankV2: number): string {
  const dir = rankDirection(rankV1, rankV2);
  if (dir === 'same') return '→ 0';
  return `${dir === 'up' ? '↑' : '↓'} ${rankShiftMagnitude(rankV1, rankV2)}`;
}

/** Signed difference, e.g. +0.015. */
export function formatSigned(value: number, digits = 3): string {
  const s = value.toFixed(digits);
  return value > 0 ? `+${s}` : s;
}
