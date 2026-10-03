// FLIP list moves with WAAPI. Presentation only: animates DOM nodes from where they
// were to where React just put them. Reads are batched before any write (no layout
// thrash), and only `transform` / `opacity` animate.
import { useLayoutEffect, useRef } from 'react';
import type { RefObject } from 'react';

export interface FlipOptions {
  /** False under reduced motion: positions are tracked but nothing animates. */
  enabled: boolean;
  moveMs: number;
  staggerMs: number;
  enterMs: number;
  easing: string;
}

interface Box {
  x: number;
  y: number;
}

/**
 * Children of `containerRef` marked `data-flip-key` slide from their previous position
 * whenever `signature` changes. New keys fade/scale in. First render never animates.
 */
export function useFlip(containerRef: RefObject<HTMLElement | null>, signature: string, opts: FlipOptions) {
  const prev = useRef<Map<string, Box> | null>(null);
  const running = useRef<Animation[]>([]);

  useLayoutEffect(() => {
    const root = containerRef.current;
    if (!root) return;
    // Settle anything still moving so measurements are layout positions.
    running.current.forEach((a) => a.cancel());
    running.current = [];

    // READ: one batch.
    const rootBox = root.getBoundingClientRect();
    const nodes = Array.from(root.querySelectorAll<HTMLElement>('[data-flip-key]'));
    const next = new Map<string, Box>();
    const measured = nodes.map((el) => {
      const r = el.getBoundingClientRect();
      const box = { x: r.left - rootBox.left, y: r.top - rootBox.top };
      next.set(el.dataset.flipKey!, box);
      return { el, box };
    });

    const before = prev.current;
    prev.current = next;
    if (!before || !opts.enabled || typeof root.animate !== 'function') return;

    // WRITE: start animations.
    let moved = 0;
    for (const { el, box } of measured) {
      const key = el.dataset.flipKey!;
      const from = before.get(key);
      if (!from) {
        running.current.push(
          el.animate([{ opacity: 0, transform: 'scale(0.96)' }, { opacity: 1, transform: 'none' }], {
            duration: opts.enterMs,
            delay: opts.moveMs * 0.5,
            easing: opts.easing,
            fill: 'backwards',
          }),
        );
        continue;
      }
      const dx = from.x - box.x;
      const dy = from.y - box.y;
      if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) continue;
      // Movers ride above the rows that stay put, with a slight lift mid-flight.
      el.style.zIndex = '2';
      const anim = el.animate(
        [
          { transform: `translate(${dx}px, ${dy}px)` },
          { transform: `translate(${dx * 0.5}px, ${dy * 0.5}px) scale(1.025)`, offset: 0.5 },
          { transform: 'none' },
        ],
        {
          duration: opts.moveMs,
          delay: moved * opts.staggerMs,
          easing: opts.easing,
          fill: 'backwards',
        },
      );
      const settle = () => {
        el.style.zIndex = '';
      };
      anim.addEventListener?.('finish', settle);
      anim.addEventListener?.('cancel', settle);
      running.current.push(anim);
      moved += 1;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature]);

  useLayoutEffect(() => () => running.current.forEach((a) => a.cancel()), []);
}
