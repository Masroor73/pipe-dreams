// Shared motion helpers. Presentation only: these never compute data values,
// they only decide *when* and *whether* to reveal values the API provided.
import { useEffect, useRef, useState } from 'react';

const REDUCED_QUERY = '(prefers-reduced-motion: reduce)';

/** True when the user prefers reduced motion (or matchMedia is unavailable, e.g. jsdom). */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return true;
  return window.matchMedia(REDUCED_QUERY).matches;
}

/** Reactive version of prefersReducedMotion(). */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(prefersReducedMotion);
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    const mql = window.matchMedia(REDUCED_QUERY);
    const onChange = () => setReduced(mql.matches);
    mql.addEventListener?.('change', onChange);
    return () => mql.removeEventListener?.('change', onChange);
  }, []);
  return reduced;
}

/**
 * Returns [ref, inView]. inView flips to true once, the first time the element
 * intersects the viewport, and never flips back. Without IntersectionObserver
 * (jsdom, old browsers) it is true immediately so final states always render.
 */
export function useInViewOnce<T extends Element>(
  options: IntersectionObserverInit = { threshold: 0.25 },
): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(
    () => typeof window === 'undefined' || typeof window.IntersectionObserver !== 'function',
  );
  useEffect(() => {
    if (inView) return;
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        setInView(true);
        io.disconnect();
      }
    }, options);
    io.observe(el);
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inView]);
  return [ref, inView];
}
