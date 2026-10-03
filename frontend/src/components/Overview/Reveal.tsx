import { useLayoutEffect } from 'react';
import type { ReactNode } from 'react';
import { prefersReducedMotion, useInViewOnce } from '../../hooks/motion';
import { EASE_OUT_CSS, MOTION } from '../../hooks/overviewMotion';

/**
 * Once-only fade/rise (opacity + 8px translateY, 320 ms). `from`-only WAAPI: content
 * is in the DOM at its end state, so failures or reduced motion simply show it.
 */
export function Reveal({ children, className }: { children: ReactNode; className?: string }) {
  const [ref, inView] = useInViewOnce<HTMLDivElement>({ threshold: 0.15 });
  useLayoutEffect(() => {
    const el = ref.current;
    if (!inView || !el || prefersReducedMotion() || typeof el.animate !== 'function') return;
    el.animate(
      [
        { opacity: 0, transform: `translateY(${MOTION.reveal.offsetPx}px)` },
        { opacity: 1, transform: 'none' },
      ],
      { duration: MOTION.reveal.durationMs, easing: EASE_OUT_CSS, fill: 'backwards' },
    );
  }, [inView, ref]);
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
