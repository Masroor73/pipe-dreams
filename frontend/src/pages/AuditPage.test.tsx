import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from '../lib/api';
import { MetaProvider } from '../lib/synthetic';
import type { Audit, Envelope } from '../types/api';
import AuditPage from './AuditPage';

const meta = { synthetic: false, config_hash: 'abc' };

function renderPage() {
  return render(
    <MetaProvider>
      <MemoryRouter>
        <AuditPage />
      </MemoryRouter>
    </MetaProvider>,
  );
}

const audit: Envelope<Audit> = {
  meta,
  data: {
    events: [
      { seq: 1, event_type: 'PLAN_V1', timestamp: '2026-10-03T14:04:56Z', summary: 'first thing', candidate: null, details: { policy_id: 'V1' } },
      {
        seq: 2,
        event_type: 'TEST_CANDIDATE',
        timestamp: '2026-10-03T14:10:00Z',
        summary: 'second thing',
        candidate: {
          candidate_id: 'C2',
          origin_wins: 3,
          n_origins: 3,
          pooled_v1_score: 0.19,
          pooled_candidate_score: 0.205,
          difference: 0.015,
          bootstrap_se: 0.004,
          required_delta: 0.004,
          decision: 'ACCEPT',
          reason: 'won all origins',
        },
        details: {},
      },
      { seq: 3, event_type: 'ESCALATE', timestamp: '2026-10-03T14:20:00Z', summary: 'third thing', candidate: null, details: {} },
    ],
  },
};

afterEach(() => vi.restoreAllMocks());

describe('AuditPage', () => {
  it('renders all events in the order given with candidate decision from data', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    expect(await screen.findByText('first thing')).toBeInTheDocument();
    const items = screen.getAllByRole('listitem').filter((li) => li.hasAttribute('data-event-type'));
    expect(items.map((li) => li.getAttribute('data-event-type'))).toEqual(['PLAN_V1', 'TEST_CANDIDATE', 'ESCALATE']);
    const table = screen.getByRole('table', { name: /revision gate result for C2/i });
    expect(within(table).getByText('ACCEPT')).toBeInTheDocument();
    expect(within(table).getByText('0.205')).toBeInTheDocument();
    expect(screen.getByText('won all origins')).toBeInTheDocument();
  });

  it('shows the gate table once per candidate when a test is followed by its decision', async () => {
    const test = audit.data.events[1]!;
    const grouped: Envelope<Audit> = {
      meta,
      data: {
        events: [
          test,
          { ...test, seq: 3, event_type: 'ACCEPT', summary: 'accepted C2' },
        ],
      },
    };
    vi.spyOn(api, 'getAudit').mockResolvedValue(grouped);
    renderPage();
    expect(await screen.findByText('accepted C2')).toBeInTheDocument();
    expect(screen.getAllByRole('table')).toHaveLength(1);
    expect(screen.getByText('second thing')).toBeInTheDocument();
  });

  it('has no event-type filter or redundant step text', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    await screen.findByText('first thing');
    expect(screen.queryByRole('group', { name: /filter by event type/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/^Step \d/)).not.toBeInTheDocument();
  });

  it('shows details as key/value pairs', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    expect(await screen.findByText('policy_id')).toBeInTheDocument();
  });

  it('shows the empty state', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue({ meta, data: { events: [] } });
    renderPage();
    expect(await screen.findByText('No audit events recorded.')).toBeInTheDocument();
  });

  it('shows the error state', async () => {
    vi.spyOn(api, 'getAudit').mockRejectedValue(new ApiError(500, 'boom', 'Audit exploded'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('Audit exploded');
  });
});

describe('AuditPage replay', () => {
  const hiddenSeqs = () =>
    screen
      .getAllByRole('listitem')
      .filter((li) => li.hasAttribute('data-event-type') && /hidden/.test(li.className))
      .map((li) => li.getAttribute('data-seq'));

  const motionAllowed = () =>
    vi.stubGlobal('matchMedia', (q: string) => ({
      matches: false,
      media: q,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    }));

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('shows the replay button and all events before any replay', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    await screen.findByText('first thing');
    expect(screen.getByRole('button', { name: 'Replay agent run' })).toBeInTheDocument();
    expect(hiddenSeqs()).toEqual([]);
  });

  it('steps events in seq order, then Stop shows everything', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    await screen.findByText('first thing');
    motionAllowed();
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole('button', { name: 'Replay agent run' }));
    expect(screen.getByRole('button', { name: 'Stop replay' })).toBeInTheDocument();
    expect(hiddenSeqs()).toEqual(['2', '3']);
    expect(screen.getByText('Step 1 of 3: PLAN_V1')).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(350));
    expect(hiddenSeqs()).toEqual(['3']);
    fireEvent.click(screen.getByRole('button', { name: 'Stop replay' }));
    expect(hiddenSeqs()).toEqual([]);
    expect(screen.getByRole('button', { name: 'Replay agent run' })).toBeInTheDocument();
  });

  it('ends with everything shown after the last step', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    await screen.findByText('first thing');
    motionAllowed();
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole('button', { name: 'Replay agent run' }));
    act(() => void vi.advanceTimersByTime(350 * 3 + 10));
    expect(hiddenSeqs()).toEqual([]);
    expect(screen.getByRole('button', { name: 'Replay agent run' })).toBeInTheDocument();
  });

  it('shows everything immediately under reduced motion (default in jsdom)', async () => {
    vi.spyOn(api, 'getAudit').mockResolvedValue(audit);
    renderPage();
    await screen.findByText('first thing');
    fireEvent.click(screen.getByRole('button', { name: 'Replay agent run' }));
    expect(hiddenSeqs()).toEqual([]);
    expect(screen.getByRole('button', { name: 'Replay agent run' })).toBeInTheDocument();
  });
});
