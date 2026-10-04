import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../lib/api';
import { MetaProvider } from '../lib/synthetic';
import type { Escalation, Escalations, Envelope } from '../types/api';
import EscalationPage from './EscalationPage';

const meta = { synthetic: false, config_hash: 'abc' };

function row(asset_id: string, priority_rank: number, owner = 'Zed', reason = 'reason', action = 'act'): Escalation {
  return {
    asset_id,
    priority_rank,
    consequence_tier: 'T2',
    evidence_confidence: 'LOW_VERIFY',
    escalation_reason: reason,
    owner,
    required_action: action,
    response_deadline: '2026-10-24',
    status: 'OPEN',
    last_reviewed: '2026-10-03',
  };
}

const env = (items: Escalation[]): Envelope<Escalations> => ({
  meta,
  data: { items },
});

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
    .filter((r) => within(r).queryAllByRole('cell').length > 0)
    .map((r) => within(r).getAllByRole('cell')[1]?.textContent);

afterEach(() => vi.restoreAllMocks());

describe('EscalationPage', () => {
  it('sorts by priority_rank ascending by default, and re-sorts on header click', async () => {
    vi.spyOn(api, 'getEscalations').mockResolvedValue(
      env([row('seg_c', 30), row('seg_a', 5), row('seg_b', 8)]),
    );
    renderPage();
    expect(await screen.findByText('3 assets escalated')).toBeInTheDocument();
    expect(bodyIds()).toEqual(['seg_a', 'seg_b', 'seg_c']);
    const rankHeader = screen.getByRole('columnheader', {
      name: /priority rank/i,
    });
    expect(rankHeader).toHaveAttribute('aria-sort', 'ascending');

    await userEvent.click(within(rankHeader).getByRole('button'));
    expect(rankHeader).toHaveAttribute('aria-sort', 'descending');
    expect(bodyIds()).toEqual(['seg_c', 'seg_b', 'seg_a']);

    const assetHeader = screen.getByRole('columnheader', { name: /^asset/i });
    await userEvent.click(within(assetHeader).getByRole('button'));
    expect(assetHeader).toHaveAttribute('aria-sort', 'ascending');
    expect(rankHeader).toHaveAttribute('aria-sort', 'none');
    expect(bodyIds()).toEqual(['seg_a', 'seg_b', 'seg_c']);
  });

  it('groups rows by reason, owner and action with a count, ordered by first row rank', async () => {
    vi.spyOn(api, 'getEscalations').mockResolvedValue(
      env([
        row('seg_a', 1, 'Ops', 'R1', 'Inspect'),
        row('seg_b', 2, 'Eng', 'R2', 'Review'),
        row('seg_c', 3, 'Ops', 'R1', 'Inspect'),
        row('seg_d', 4, 'Ops', 'R1', 'Other action'),
      ]),
    );
    renderPage();
    expect(await screen.findByText('4 assets escalated')).toBeInTheDocument();
    const heads = screen.getAllByRole('rowheader');
    expect(heads).toHaveLength(3);
    expect(heads[0]).toHaveTextContent('R1');
    expect(heads[0]).toHaveTextContent('Ops');
    expect(heads[0]).toHaveTextContent('Inspect');
    expect(heads[0]).toHaveTextContent('2 assets');
    expect(heads[1]).toHaveTextContent('1 asset');
    expect(heads[1]).toHaveTextContent('R2');
    expect(heads[2]).toHaveTextContent('Other action');
    const groups = screen.getAllByRole('rowgroup').slice(1);
    expect(within(groups[0]!).getAllByRole('button', { name: /Open asset/ })).toHaveLength(2);
    expect(bodyIds()).toEqual(['seg_a', 'seg_c', 'seg_b', 'seg_d']);
    // sorting happens within groups; group order is fixed
    await userEvent.click(within(screen.getByRole('columnheader', { name: /priority rank/i })).getByRole('button'));
    expect(bodyIds()).toEqual(['seg_c', 'seg_a', 'seg_b', 'seg_d']);
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
