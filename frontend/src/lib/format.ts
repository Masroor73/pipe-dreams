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

/** Rank delta as shown to people: negative = rose in the ranking. */
export function formatDelta(delta: number): string {
  if (delta === 0) return '→ 0';
  const arrow = delta < 0 ? '↑' : '↓';
  return `${arrow} ${Math.abs(delta)}`;
}

/** Signed difference, e.g. +0.015. */
export function formatSigned(value: number, digits = 3): string {
  const s = value.toFixed(digits);
  return value > 0 ? `+${s}` : s;
}
