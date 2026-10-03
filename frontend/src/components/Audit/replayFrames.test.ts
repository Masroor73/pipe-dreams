import { describe, expect, it } from 'vitest';
import auditFixture from '../../fixtures/audit.json';
import { CANDIDATE_IDS } from '../../config/display';
import type { AuditEvent } from '../../types/api';
import { frameAt, replayOrder, stepCommand } from './replayFrames';

const events = auditFixture.data.events as unknown as AuditEvent[];
const sorted = replayOrder(events);
const indexOf = (pred: (e: AuditEvent) => boolean) => sorted.findIndex(pred);
const stageOf = (step: number, id: string) => frameAt(sorted, step, CANDIDATE_IDS)!.candidates.find((c) => c.id === id)!;

describe('replayFrames', () => {
  it('orders by seq without mutating the events', () => {
    const shuffled = [...events].reverse();
    const before = JSON.stringify(shuffled);
    expect(replayOrder(shuffled).map((e) => e.seq)).toEqual([...events].map((e) => e.seq).sort((a, b) => a - b));
    expect(JSON.stringify(shuffled)).toBe(before);
  });

  it('opens on PLAN_V1: V1 list, every candidate pending, the V1 Top N highlighted', () => {
    const f = frameAt(sorted, 0, CANDIDATE_IDS)!;
    expect(f.event.event_type).toBe('PLAN_V1');
    expect(f.plan).toBe('v1');
    expect(f.highlight).toBe('plan-v1');
    expect(f.candidates.map((c) => c.stage)).toEqual(['pending', 'pending', 'pending', 'pending']);
    expect(f.escalated).toBe(false);
  });

  it('shows a candidate as testing on its TEST_CANDIDATE step, then resolves it on its decision step', () => {
    const test = indexOf((e) => e.event_type === 'TEST_CANDIDATE');
    const id = sorted[test]!.candidate!.candidate_id;
    expect(stageOf(test, id).stage).toBe('testing');
    expect(frameAt(sorted, test, CANDIDATE_IDS)!.highlight).toBe('none');
    const decision = indexOf((e, ) => (e.event_type === 'ACCEPT' || e.event_type === 'REJECT') && e.candidate?.candidate_id === id);
    const c = stageOf(decision, id);
    expect(c.stage).toBe('resolved');
    // Decision is the artifact's value, unchanged.
    expect(c.result?.decision).toBe(sorted[decision]!.candidate!.decision);
  });

  it('resolves candidates strictly in audit order', () => {
    const resolvedAt = CANDIDATE_IDS.map((id) =>
      sorted.findIndex((_, i) => stageOf(i, id).stage === 'resolved'),
    );
    expect(resolvedAt.every((i) => i >= 0)).toBe(true);
    expect([...resolvedAt].sort((a, b) => a - b)).toEqual(resolvedAt);
  });

  it('switches the list to V2 exactly at PLAN_V2', () => {
    const v2 = indexOf((e) => e.event_type === 'PLAN_V2');
    expect(frameAt(sorted, v2 - 1, CANDIDATE_IDS)!.plan).toBe('v1');
    const f = frameAt(sorted, v2, CANDIDATE_IDS)!;
    expect(f.plan).toBe('v2');
    expect(f.highlight).toBe('changed-v2');
  });

  it('ends with every candidate resolved and escalation shown', () => {
    const f = frameAt(sorted, sorted.length - 1, CANDIDATE_IDS)!;
    expect(f.candidates.every((c) => c.stage === 'resolved')).toBe(true);
    expect(f.escalated).toBe(true);
    expect(f.highlight).toBe('escalated');
  });

  it('a tested candidate with no decision event resolves from its own payload once the run moves on', () => {
    const test = sorted.find((e) => e.event_type === 'TEST_CANDIDATE')!;
    const only = [sorted[0]!, test, { ...sorted[0]!, seq: 99, event_type: 'PLAN_V2' as const }];
    expect(frameAt(only, 1, CANDIDATE_IDS)!.candidates.find((c) => c.id === test.candidate!.candidate_id)!.stage).toBe('testing');
    const after = frameAt(only, 2, CANDIDATE_IDS)!.candidates.find((c) => c.id === test.candidate!.candidate_id)!;
    expect(after.stage).toBe('resolved');
    expect(after.result).toEqual(test.candidate);
  });

  it('clamps steps and returns null for an empty run', () => {
    expect(frameAt(sorted, 999, CANDIDATE_IDS)!.step).toBe(sorted.length - 1);
    expect(frameAt(sorted, -5, CANDIDATE_IDS)!.step).toBe(0);
    expect(frameAt([], 0, CANDIDATE_IDS)).toBeNull();
  });

  it('stepCommand clamps to the run', () => {
    expect(stepCommand(0, 13, 'prev')).toBe(0);
    expect(stepCommand(12, 13, 'next')).toBe(12);
    expect(stepCommand(5, 13, 'first')).toBe(0);
    expect(stepCommand(5, 13, 'last')).toBe(12);
    expect(stepCommand(5, 13, 'next')).toBe(6);
  });
});
