import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AUDIT_REPLAY } from '../../config/display';
import { prefersReducedMotion } from '../../hooks/motion';
import type { AuditEvent } from '../../types/api';

export interface AuditReplay {
  /** Number of events revealed so far in seq order, or null when not replaying (everything visible). */
  revealed: number | null;
  running: boolean;
  /** Polite live-region text; empty until the user starts a replay. */
  announcement: string;
  /** seq values in replay order (ascending API seq). */
  order: number[];
  start: () => void;
  stop: () => void;
}

/** Step interval: the spec's step, shortened so the whole replay fits the cap. */
export function replayStepMs(count: number): number {
  if (count <= 0) return AUDIT_REPLAY.stepMs;
  return Math.min(AUDIT_REPLAY.stepMs, Math.floor(AUDIT_REPLAY.maxTotalMs / count));
}

/**
 * Opt-in replay of the agent run: reveals events one by one in `seq` order.
 * Presentation only; never reorders or alters event data. Under reduced motion,
 * start() leaves every event visible and only announces completion.
 */
export function useAuditReplay(events: AuditEvent[]): AuditReplay {
  const [revealed, setRevealed] = useState<number | null>(null);
  const [announcement, setAnnouncement] = useState('');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sorted = useMemo(() => [...events].sort((a, b) => a.seq - b.seq), [events]);
  const order = useMemo(() => sorted.map((e) => e.seq), [sorted]);
  const total = sorted.length;
  const running = revealed !== null;

  const clear = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  };

  const stop = useCallback(() => {
    clear();
    setRevealed(null);
    setAnnouncement((a) => (a ? 'Replay stopped. All events shown.' : a));
  }, []);

  const start = useCallback(() => {
    clear();
    if (total === 0) return;
    if (prefersReducedMotion()) {
      setRevealed(null);
      setAnnouncement(`Replay complete. All ${total} events shown.`);
      return;
    }
    const interval = replayStepMs(total);
    const step = (n: number) => {
      setRevealed(n);
      const e = sorted[n - 1];
      if (e) setAnnouncement(`Step ${n} of ${total}: ${e.event_type}`);
      timer.current = setTimeout(() => {
        if (n >= total) {
          setRevealed(null);
          setAnnouncement(`Replay complete. All ${total} events shown.`);
          timer.current = null;
        } else {
          step(n + 1);
        }
      }, interval);
    };
    step(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sorted, total]);

  // Esc stops a running replay.
  useEffect(() => {
    if (!running) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') stop();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [running, stop]);

  // Stop timers on unmount or when the event list changes.
  useEffect(() => clear, []);
  useEffect(() => {
    clear();
    setRevealed(null);
  }, [events]);

  return { revealed, running, announcement, order, start, stop };
}
