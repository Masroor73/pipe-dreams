import { useCallback, useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { AUDIT_CINEMA } from '../../config/display';
import type { AuditEvent } from '../../types/api';
import { stepCommand } from './replayFrames';

export interface Cinema {
  step: number;
  playing: boolean;
  /** False until the viewer first plays or scrubs; the page opens on the run's end state. */
  engaged: boolean;
  setStep: (step: number) => void;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  command: (cmd: 'prev' | 'next' | 'first' | 'last') => void;
  /** Arrow keys / Home / End step, Space plays or pauses. Attach to the cinema region. */
  onKeyDown: (e: KeyboardEvent<HTMLElement>) => void;
}

export function dwellFor(event: AuditEvent | undefined): number {
  if (!event) return AUDIT_CINEMA.defaultDwellMs;
  return AUDIT_CINEMA.dwellMs[event.event_type] ?? AUDIT_CINEMA.defaultDwellMs;
}

/**
 * Scrubber state for the audit replay. Autoplay advances one step per dwell and stops
 * on the last step. Reduced motion does not change sequencing: each step simply renders
 * its end state with no movement (handled by the views).
 */
export function useCinema(sorted: AuditEvent[]): Cinema {
  const total = sorted.length;
  const [step, setStepState] = useState(Math.max(total - 1, 0));
  const [playing, setPlaying] = useState(false);
  const [engaged, setEngaged] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clear = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  };

  // New data: reset to the end state.
  useEffect(() => {
    clear();
    setPlaying(false);
    setEngaged(false);
    setStepState(Math.max(total - 1, 0));
  }, [sorted, total]);

  // Autoplay: hold the current step for its dwell, then advance; stop on the last step.
  useEffect(() => {
    if (!playing) return;
    if (step >= total - 1) {
      setPlaying(false);
      return;
    }
    timer.current = setTimeout(() => setStepState((s) => Math.min(s + 1, total - 1)), dwellFor(sorted[step]));
    return clear;
  }, [playing, step, total, sorted]);

  useEffect(() => clear, []);

  const setStep = useCallback(
    (s: number) => {
      setEngaged(true);
      setPlaying(false);
      setStepState(Math.min(Math.max(Math.trunc(s), 0), Math.max(total - 1, 0)));
    },
    [total],
  );

  const play = useCallback(() => {
    if (total === 0) return;
    setEngaged(true);
    // From the end (or before the viewer has engaged), play restarts the run.
    setStepState((s) => (!engaged || s >= total - 1 ? 0 : s));
    setPlaying(true);
  }, [total, engaged]);

  const pause = useCallback(() => setPlaying(false), []);
  const toggle = useCallback(() => (playing ? pause() : play()), [playing, pause, play]);

  const command = useCallback(
    (cmd: 'prev' | 'next' | 'first' | 'last') => {
      setEngaged(true);
      setPlaying(false);
      setStepState((s) => stepCommand(engaged ? s : Math.max(total - 1, 0), total, cmd));
    },
    [total, engaged],
  );

  const onKeyDown = useCallback(
    (e: KeyboardEvent<HTMLElement>) => {
      const target = e.target as HTMLElement;
      const isRange = target instanceof HTMLInputElement && target.type === 'range';
      const isButton = target.tagName === 'BUTTON';
      if (e.key === ' ' || e.key === 'Spacebar') {
        if (isButton) return; // native click already toggles / steps
        e.preventDefault();
        toggle();
        return;
      }
      if (isRange) return; // the range input steps natively via onChange
      const map: Record<string, 'prev' | 'next' | 'first' | 'last'> = {
        ArrowLeft: 'prev',
        ArrowUp: 'prev',
        ArrowRight: 'next',
        ArrowDown: 'next',
        Home: 'first',
        End: 'last',
      };
      const cmd = map[e.key];
      if (!cmd) return;
      e.preventDefault();
      command(cmd);
    },
    [toggle, command],
  );

  // Until the viewer engages, always show the run's end state (also on the first render with data).
  const shown = engaged ? step : Math.max(total - 1, 0);
  return { step: shown, playing, engaged, setStep, play, pause, toggle, command, onKeyDown };
}
