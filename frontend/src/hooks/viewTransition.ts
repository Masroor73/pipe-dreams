import { flushSync } from 'react-dom';
import { prefersReducedMotion } from './motion';

type StartViewTransition = (update: () => void) => unknown;

/** True when the View Transitions API exists and the user has not asked for reduced motion. */
export function canViewTransition(): boolean {
  return (
    typeof document !== 'undefined' &&
    typeof (document as unknown as { startViewTransition?: unknown }).startViewTransition === 'function' &&
    !prefersReducedMotion()
  );
}

/**
 * Runs a synchronous DOM-updating navigation inside a cross-fade view transition.
 * Where unsupported (or reduced motion) it just runs `update()` (an instant swap).
 */
export function withViewTransition(update: () => void): void {
  if (!canViewTransition()) {
    update();
    return;
  }
  (document as unknown as { startViewTransition: StartViewTransition }).startViewTransition(() => {
    flushSync(update);
  });
}
