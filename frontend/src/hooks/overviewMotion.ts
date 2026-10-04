// Overview motion constants (docs/superpowers/specs/2026-10-03-frontend-motion.md).
// Presentation timing only; nothing here touches data values.

/** Matches --ease-out in tokens.css. */
export const EASE_OUT_CSS = 'cubic-bezier(0.22, 1, 0.36, 1)';
export const EASE_OUT_POINTS: readonly [number, number, number, number] = [0.22, 1, 0.36, 1];

export const MOTION = {
  gate: {
    inViewThreshold: 0.35,
    cardStaggerMs: 400,
    testingEndMs: 470,
    dotsStartMs: 150,
    dotStaggerMs: 40,
    dotDurationMs: 200,
    barStartMs: 150,
    barDurationMs: 320,
    stampStartMs: 470,
    stampDurationMs: 150,
    emphasisStartMs: 1800,
    emphasisDurationMs: 400,
  },
  countUpMs: 600,
  rank: { durationMs: 320, staggerMs: 80, arrowOffsetPx: 8 },
  reveal: { durationMs: 320, offsetPx: 8 },
  chart: { firstDrawMs: 600, switchDrawMs: 400, seriesStaggerMs: 60, whiskerFadeMs: 150 },
} as const;
