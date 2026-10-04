/** Deterministic vertical nudge so direct line labels never overlap (display geometry only). */
export interface LabelSlot {
  key: string;
  /** Pixel y of the line end, measured from the top of the plot area. */
  y: number;
  /** Label height in px (one line or two). */
  height: number;
}

/** Returns the dy (px) to add to each label's natural y. */
export function nudgeLabels(slots: LabelSlot[], plotHeight: number): Record<string, number> {
  const sorted = [...slots].sort((a, b) => a.y - b.y || a.key.localeCompare(b.key));
  const ys = sorted.map((s) => s.y);
  const gap = (i: number) => (sorted[i]!.height + sorted[i + 1]!.height) / 2 + 2;
  for (let i = 1; i < ys.length; i++) ys[i] = Math.max(ys[i]!, ys[i - 1]! + gap(i - 1));
  const last = ys.length - 1;
  if (last >= 0 && ys[last]! > plotHeight) ys[last] = plotHeight;
  for (let i = last - 1; i >= 0; i--) ys[i] = Math.min(ys[i]!, ys[i + 1]! - gap(i));
  const out: Record<string, number> = {};
  sorted.forEach((s, i) => {
    out[s.key] = ys[i]! - s.y;
  });
  return out;
}
