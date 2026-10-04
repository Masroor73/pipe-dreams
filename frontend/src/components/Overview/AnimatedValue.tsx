import { useCountUp } from '../../hooks/countUp';
import { useInViewOnce } from '../../hooks/motion';
import { MOTION } from '../../hooks/overviewMotion';

export interface AnimatedValueProps {
  /** API value; the animation ends exactly here. */
  value: number;
  /** Starting value of the count (0 for headline, V1 rank for rank cards). */
  from?: number;
  /** Same formatter used for the static value. */
  format: (n: number) => string;
  durationMs?: number;
  delayMs?: number;
  integer?: boolean;
  className?: string;
}

/**
 * Counts from `from` to `value` once, on first view. The accessible text is always
 * the final formatted value; the ticking text is aria-hidden while it runs.
 * Reduced motion / no IntersectionObserver: renders only the final text.
 */
export function AnimatedValue({
  value,
  from = 0,
  format,
  durationMs = MOTION.countUpMs,
  delayMs,
  integer,
  className,
}: AnimatedValueProps) {
  const [ref, inView] = useInViewOnce<HTMLSpanElement>({ threshold: 0.5 });
  const { value: current, animating } = useCountUp(value, { from, durationMs, delayMs, integer, play: inView });
  const final = format(value);
  if (!animating) {
    return (
      <span ref={ref} className={className}>
        {final}
      </span>
    );
  }
  return (
    <span ref={ref} className={className}>
      <span aria-hidden="true">{format(current)}</span>
      <span style={SR_ONLY}>{final}</span>
    </span>
  );
}

const SR_ONLY: React.CSSProperties = {
  position: 'absolute',
  width: 1,
  height: 1,
  overflow: 'hidden',
  clip: 'rect(0 0 0 0)',
  whiteSpace: 'nowrap',
};
