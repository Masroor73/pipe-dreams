import { describe, expect, it } from 'vitest';
import { formatRankMove, rankDirection, rankShiftMagnitude } from './format';

describe('rank movement (lower rank number is better)', () => {
  it('shows an improvement from 7736 to 49 as up 7687', () => {
    expect(rankDirection(7736, 49)).toBe('up');
    expect(rankShiftMagnitude(7736, 49)).toBe(7687);
    expect(formatRankMove(7736, 49)).toBe('↑ 7687');
  });
  it('shows a drop as down', () => {
    expect(formatRankMove(5, 31)).toBe('↓ 26');
    expect(rankDirection(5, 31)).toBe('down');
  });
  it('shows no change', () => {
    expect(formatRankMove(10, 10)).toBe('→ 0');
    expect(rankDirection(10, 10)).toBe('same');
  });
});
