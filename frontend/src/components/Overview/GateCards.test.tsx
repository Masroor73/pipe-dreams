import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import auditFixture from '../../fixtures/audit.json';
import overviewFixture from '../../fixtures/overview.json';
import type { Resource } from '../../hooks';
import { api } from '../../lib/api';
import { MetaProvider } from '../../lib/synthetic';
import type { Audit, Envelope, Overview } from '../../types/api';
import { GateCards } from './GateCards';

const overview: Resource<Overview> = {
  status: 'success',
  data: overviewFixture.data as unknown as Overview,
  meta: undefined,
  error: undefined,
  reload: () => undefined,
};

function renderCards() {
  return render(
    <MetaProvider>
      <MemoryRouter>
        <GateCards overview={overview} />
      </MemoryRouter>
    </MetaProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe('GateCards', () => {
  it('renders four candidates with decisions read from the audit and marks the selected one', async () => {
    renderCards();
    expect(await screen.findByText('Selected as V2')).toBeInTheDocument();
    const cards = document.querySelectorAll('[data-candidate]');
    expect(cards).toHaveLength(4);
    expect(within(cards[1] as HTMLElement).getByText('PASSED · SELECTED AS V2')).toBeInTheDocument();
    expect(within(cards[0] as HTMLElement).getByText('FAILED')).toBeInTheDocument();
    expect(screen.getByText(/wins ≥2 of 3 validation origins/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /full audit trail/ })).toHaveAttribute('href', '/audit');
  });

  it('shows the recorded decision, never a recomputed one', async () => {
    const modified = structuredClone(auditFixture) as unknown as Envelope<Audit>;
    for (const e of modified.data.events) {
      if (e.candidate?.candidate_id === 'C3') e.candidate.decision = 'ACCEPT';
    }
    vi.spyOn(api, 'getAudit').mockResolvedValue(modified);
    renderCards();
    await screen.findByText('Selected as V2');
    const c3 = document.querySelector('[data-candidate="C3"]') as HTMLElement;
    expect(within(c3).getByText(/^PASSED/)).toBeInTheDocument();
    expect(within(c3).queryByText('FAILED')).not.toBeInTheDocument();
  });
});
