import { describe, expect, it } from 'vitest';
import { matchesBye, matchesWake } from './phrases';

describe('phrases', () => {
  it('matches wake phrases', () => {
    for (const t of ['Hello copilot', 'hey, copilot!', 'well hello Pipe Dreams', 'Hello co-pilot']) expect(matchesWake(t)).toBe(true);
  });
  it('rejects non-wake', () => {
    for (const t of ['hello there', 'copilot', 'bye copilot', '']) expect(matchesWake(t)).toBe(false);
  });
  it('matches bye phrases', () => {
    for (const t of ['Bye copilot', 'goodbye copilot.', 'stop copilot', 'ok bye pipe dreams']) expect(matchesBye(t)).toBe(true);
  });
  it('rejects non-bye', () => {
    for (const t of ['hello copilot', 'goodbye', 'stop the pipe']) expect(matchesBye(t)).toBe(false);
  });
});
