import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from '../../lib/api';
import { MetaProvider } from '../../lib/synthetic';
import { RankChangeCards } from './RankChangeCards';

function Loc() {
  return <output data-testid="loc">{useLocation().search}</output>;
}

function renderCards() {
  return render(
    <MetaProvider>
      <MemoryRouter>
        <RankChangeCards />
        <Loc />
      </MemoryRouter>
    </MetaProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe('RankChangeCards', () => {
  it('renders three cards and opens the asset panel on click', async () => {
    renderCards();
    const cards = await screen.findAllByRole('button');
    expect(cards).toHaveLength(3);
    expect(screen.getByText('#40 → #3')).toBeInTheDocument();
    expect(screen.getByText('37')).toBeInTheDocument();
    expect(screen.getAllByLabelText('Moved up').length).toBeGreaterThan(0);
    expect(screen.queryByText(/↑/)).not.toBeInTheDocument();
    await userEvent.click(cards[0]!);
    expect(screen.getByTestId('loc')).toHaveTextContent('?asset=seg_000013');
  });

  it('shows an error state with retry', async () => {
    vi.spyOn(api, 'getRankChanges').mockRejectedValue(new ApiError(500, 'http_error', 'Boom'));
    renderCards();
    expect(await screen.findByRole('alert')).toHaveTextContent('Boom');
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });
});
