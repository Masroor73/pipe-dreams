// Count-up helpers. Presentation only: the last frame always reports the exact target.
import { useEffect, useState } from 'react';
import { EASE_OUT_POINTS } from './overviewMotion';
import { prefersReducedMotion } from './motion';

/** Solve a CSS cubic-bezier(x1,y1,x2,y2) easing: progress t in [0,1] -> eased value. */
export function cubicBezier(x1: number, y1: number, x2: number, y2: number): (t: number) => number {
  const cx = 3 * x1;
  const bx = 3 * (x2 - x1) - cx;
  const ax = 1 - cx - bx;
  const cy = 3 * y1;
  const by = 3 * (y2 - y1) - cy;
  const ay = 1 - cy - by;
  const sampleX = (s: number) => ((ax * s + bx) * s + cx) * s;
  const sampleY = (s: number) => ((ay * s + by) * s + cy) * s;
  const slopeX = (s: number) => (3 * ax * s + 2 * bx) * s + cx;
  return (t) => {
    if (t <= 0) return 0;
    if (t >= 1) return 1;
    let s = t;
    for (let i = 0; i < 8; i++) {
      const err = sampleX(s) - t;
      if (Math.abs(err) < 1e-5) return sampleY(s);
      const d = slopeX(s);
      if (Math.abs(d) < 1e-6) break;
      s -= err / d;
    }
    let lo = 0;
    let hi = 1;
    s = t;
    for (let i = 0; i < 24; i++) {
      const x = sampleX(s);
      if (Math.abs(x - t) < 1e-5) break;
      if (x < t) lo = s;
      else hi = s;
      s = (lo + hi) / 2;
    }
    return sampleY(s);
  };
}

export const easeOut = cubicBezier(...EASE_OUT_POINTS);

export interface CountUpOptions {
  from: number;
  to: number;
  durationMs: number;
  delayMs?: number;
  /** Round intermediate values to integers (rank ticks). */
  integer?: boolean;
  onFrame: (value: number) => void;
}

/** rAF-driven count-up. The last frame is exactly `to`. Returns a cancel function. */
export function runCountUp({ from, to, durationMs, delayMs = 0, integer = false, onFrame }: CountUpOptions): () => void {
  let raf = 0;
  let start: number | null = null;
  let cancelled = false;
  const step = (now: number) => {
    if (cancelled) return;
    if (start === null) start = now + delayMs;
    const t = (now - start) / durationMs;
    if (t < 0) {
      raf = requestAnimationFrame(step);
      return;
    }
    if (t >= 1) {
      onFrame(to);
      return;
    }
    const v = from + (to - from) * easeOut(t);
    onFrame(integer ? Math.round(v) : v);
    raf = requestAnimationFrame(step);
  };
  raf = requestAnimationFrame(step);
  return () => {
    cancelled = true;
    cancelAnimationFrame(raf);
  };
}

/**
 * Current display value for a count-up that starts when `play` flips true.
 * Reduced motion (or no rAF): the target is returned immediately.
 */
export function useCountUp(
  to: number,
  opts: { from?: number; durationMs: number; delayMs?: number; integer?: boolean; play: boolean },
): { value: number; animating: boolean } {
  const { from = 0, durationMs, delayMs, integer, play } = opts;
  const skip = prefersReducedMotion() || typeof requestAnimationFrame !== 'function';
  const [value, setValue] = useState(skip ? to : from);
  const [done, setDone] = useState(skip);
  useEffect(() => {
    if (skip) {
      setValue(to);
      setDone(true);
      return;
    }
    if (!play) return;
    const cancel = runCountUp({
      from,
      to,
      durationMs,
      delayMs,
      integer,
      onFrame: (v) => {
        setValue(v);
        if (v === to) setDone(true);
      },
    });
    return cancel;
  }, [to, from, durationMs, delayMs, integer, play, skip]);
  return { value: skip ? to : value, animating: !skip && !done };
}
