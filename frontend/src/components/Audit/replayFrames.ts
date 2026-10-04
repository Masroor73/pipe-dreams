// "Agent run as cinema": pure step sequencing over the audit log.
//
// Presentation only. A frame says *which already-computed API values* are on
// stage at a given step: which candidate decisions have been revealed, whether
// the ranked list shows the V1 or the V2 plan, and which set of assets the map
// highlights. Nothing here scores, ranks, or decides anything; every value shown
// comes from /api/audit, /api/assets, /api/rank-changes or /api/escalations.
//
// Contract gap (docs/API_CONTRACT.md): there are no per-step or per-candidate
// rankings and no per-step "segments touched" field. So the list only changes
// at PLAN_V2 (V1 Top N -> V2 Top N), and DIAGNOSE / TEST_CANDIDATE / ACCEPT /
// REJECT steps highlight no segments. Do not fill the gap client-side.
import type { AuditEvent, CandidateResult } from '../../types/api';

export type CandidateStage = 'pending' | 'testing' | 'resolved';

export interface CandidateFrame {
  id: string;
  stage: CandidateStage;
  /** Gate numbers + decision exactly as in the artifact; null until the candidate is first tested. */
  result: CandidateResult | null;
}

/**
 * Which highlight set the map uses at this step.
 * - plan-v1: every asset in the V1 Top N (the plan appears)
 * - selected-v1: V1 assets inside the frozen capacity (`selected`), i.e. the evaluated plan
 * - changed-v2: assets that entered the V2 Top N or have a rank_changes.csv row
 * - escalated: assets listed in escalation.csv
 * - none: the artifact has no per-segment data for this step
 */
export type Highlight = 'plan-v1' | 'selected-v1' | 'changed-v2' | 'escalated' | 'none';

export interface Frame {
  /** 0-based step index into events sorted by seq. */
  step: number;
  total: number;
  event: AuditEvent;
  plan: 'v1' | 'v2';
  candidates: CandidateFrame[];
  highlight: Highlight;
  /** True once an ESCALATE event has played. */
  escalated: boolean;
}

/** Events in replay order (ascending seq). Never alters event data. */
export function replayOrder(events: AuditEvent[]): AuditEvent[] {
  return [...events].sort((a, b) => a.seq - b.seq);
}

function highlightFor(type: string): Highlight {
  switch (type) {
    case 'PLAN_V1':
      return 'plan-v1';
    case 'EVALUATE':
      return 'selected-v1';
    case 'PLAN_V2':
      return 'changed-v2';
    case 'ESCALATE':
      return 'escalated';
    default:
      return 'none';
  }
}

/**
 * Frame at `step` (clamped). Candidate rules:
 * - not yet tested -> pending;
 * - its TEST_CANDIDATE is the current step and no decision event has played -> testing;
 * - otherwise resolved, using the latest event's candidate payload (the ACCEPT/REJECT
 *   event when present, else the TEST_CANDIDATE payload, which already carries the decision).
 */
export function frameAt(sorted: AuditEvent[], step: number, candidateIds: readonly string[]): Frame | null {
  if (sorted.length === 0) return null;
  const s = Math.min(Math.max(Math.trunc(step), 0), sorted.length - 1);
  const prefix = sorted.slice(0, s + 1);
  const current = sorted[s]!;

  const candidates: CandidateFrame[] = candidateIds.map((id) => {
    const mine = prefix.filter((e) => e.candidate?.candidate_id === id);
    if (mine.length === 0) return { id, stage: 'pending', result: null };
    const last = mine[mine.length - 1]!;
    const decided = mine.some((e) => e.event_type === 'ACCEPT' || e.event_type === 'REJECT');
    const testingNow = !decided && last === current && current.event_type === 'TEST_CANDIDATE';
    return { id, stage: testingNow ? 'testing' : 'resolved', result: last.candidate };
  });

  return {
    step: s,
    total: sorted.length,
    event: current,
    plan: prefix.some((e) => e.event_type === 'PLAN_V2') ? 'v2' : 'v1',
    candidates,
    highlight: highlightFor(current.event_type),
    escalated: prefix.some((e) => e.event_type === 'ESCALATE'),
  };
}

/** Next step for a keyboard / transport command, clamped to the run. */
export function stepCommand(step: number, total: number, cmd: 'prev' | 'next' | 'first' | 'last'): number {
  if (total <= 0) return 0;
  switch (cmd) {
    case 'prev':
      return Math.max(step - 1, 0);
    case 'next':
      return Math.min(step + 1, total - 1);
    case 'first':
      return 0;
    case 'last':
      return total - 1;
  }
}
