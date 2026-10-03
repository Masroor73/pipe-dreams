import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../lib/api';
import { MetaProvider } from '../lib/synthetic';
import type { Escalation, Escalations, Envelope } from '../types/api';
import EscalationPage from './EscalationPage';

const meta = { synthetic: false, config_hash: 'abc' };

function row(asset_id: string, priority_rank: number, owner: string): Escalation {
  return {
    asset_id,
    priority_rank,
    consequence_tier: 'T2',
    evidence_confidence: 'LOW_VERIFY',
    escalation_reason: 'reason',
    owner,
    required_action: 'act',
    response_deadline: '2026-10-24',
    status: 'OPEN',
    last_reviewed: '2026-10-03',
  };
}

const env = (items: Escalation[]): Envelope<Escalations> => ({ meta, data: { items } });

function Loc() {
  const l = useLocation();
  return <div data-testid="loc">{l.search}</div>;
}

function renderPage() {
  return render(
    <MetaProvider>
      <MemoryRouter>
        <EscalationPage />
        <Loc />
      </MemoryRouter>
    </MetaProvider>,
  );
}

const bodyIds = () =>
  screen
    .getAllByRole('row')
    .slice(1)
    .map((r) => within(r).getAllByRole('cell')[1]?.textContent);

afterEach(() => vi.restoreAllMocks());

describe('EscalationPage', () => {
  it('sorts by priority_rank ascending by default, and re-sorts on header click', async () => {
    vi.spyOn(api, 'getEscalations').mockResolvedValue(
      env([row('seg_c', 30, 'Alpha'), row('seg_a', 5, 'Zed'), row('seg_b', 8, 'Mid')]),
    );
    renderPage();
    expect(await screen.findByText('3 assets escalated')).toBeInTheDocument();
    expect(bodyIds()).toEqual(['seg_a', 'seg_b', 'seg_c']);
    const rankHeader = screen.getByRole('columnheader', { name: /priority rank/i });
    expect(rankHeader).toHaveAttribute('aria-sort', 'ascending');

    await userEvent.click(within(rankHeader).getByRole('button'));
    expect(rankHeader).toHaveAttribute('aria-sort', 'descending');
    expect(bodyIds()).toEqual(['seg_c', 'seg_b', 'seg_a']);

    const ownerHeader = screen.getByRole('columnheader', { name: /owner/i });
    await userEvent.click(within(ownerHeader).getByRole('button'));
    expect(ownerHeader).toHaveAttribute('aria-sort', 'ascending');
    expect(rankHeader).toHaveAttribute('aria-sort', 'none');
    expect(bodyIds()).toEqual(['seg_c', 'seg_b', 'seg_a']); // Alpha, Mid, Zed
  });

  it('opens the asset panel via ?asset=', async () => {
    vi.spyOn(api, 'getEscalations').mockResolvedValue(env([row('seg_a', 5, 'Zed')]));
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Open asset seg_a' }));
    expect(screen.getByTestId('loc')).toHaveTextContent('?asset=seg_a');
  });

  it('shows the empty state', async () => {
    vi.spyOn(api, 'getEscalations').mockResolvedValue(env([]));
    renderPage();
    expect(await screen.findByText('No assets are escalated.')).toBeInTheDocument();
  });
});
