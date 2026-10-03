import { render, screen, within } from '@testing-library/react';
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
