import { render, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import auditFixture from '../../fixtures/audit.json';
import type { AuditEvent } from '../../types/api';
import { AuditTimeline } from './AuditTimeline';

const events = (auditFixture.data as unknown as { events: AuditEvent[] }).events;
const order = events.map((e) => e.seq);

function item(container: HTMLElement, seq: number) {
  return container.querySelector(`li[data-seq="${seq}"]`) as HTMLElement;
}

describe('AuditTimeline replay', () => {
  it('does not reveal decisions the replay has not reached yet', () => {
    // Step 0 = PLAN_V1 only; the first REJECT (seq 5) is still in the future.
    const { container } = render(<MemoryRouter><AuditTimeline events={events} step={0} replayOrder={order} /></MemoryRouter>);
    const future = item(container, 5);
    expect(within(future).getByText('PENDING')).toBeTruthy();
    expect(within(future).queryByText('REJECT')).toBeNull();
    expect(within(future).getByText('Not reached yet in this replay.')).toBeTruthy();
    expect(future.className).not.toMatch(/tone_(accept|reject)/);
  });

  it('shows the decision once the replay reaches it', () => {
    const { container } = render(<MemoryRouter><AuditTimeline events={events} step={4} replayOrder={order} /></MemoryRouter>);
    expect(within(item(container, 5)).getAllByText('REJECT').length).toBeGreaterThan(0);
  });

  it('shows every decision when the replay is idle', () => {
    const { container } = render(<MemoryRouter><AuditTimeline events={events} replayOrder={order} /></MemoryRouter>);
    expect(container.textContent).not.toContain('PENDING');
    expect(within(item(container, 7)).getAllByText('ACCEPT').length).toBeGreaterThan(0);
  });
});
