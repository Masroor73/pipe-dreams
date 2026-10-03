import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, createApi } from '../lib/api';
import { api } from '../lib/api';
import { MetaProvider } from '../lib/synthetic';
import LimitsPage from './LimitsPage';

const fixtures = createApi({ baseUrl: '', useFixtures: true, fixtureDelayMs: 0 });

function renderPage() {
  return render(
    <MetaProvider>
      <MemoryRouter>
        <LimitsPage />
      </MemoryRouter>
    </MetaProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe('LimitsPage', () => {
  it('renders not-covered items and data quality figures', async () => {
    vi.spyOn(api, 'getNotCovered').mockImplementation(() => fixtures.getNotCovered());
    vi.spyOn(api, 'getDataQuality').mockImplementation(() => fixtures.getDataQuality());
    renderPage();
    expect(await screen.findByText('NC-01')).toBeInTheDocument();
    expect(screen.getByText('service connections')).toBeInTheDocument();
    expect(screen.getByText('Would need: Utility service-line registry')).toBeInTheDocument();
    expect(await screen.findByText('112')).toBeInTheDocument();
    expect(screen.getByText('rows dropped — missing coordinates')).toBeInTheDocument();
    expect(screen.getAllByText('pre_2000').length).toBeGreaterThan(0);
  });

  it('shows an error state with retry', async () => {
    vi.spyOn(api, 'getNotCovered').mockImplementation(() => fixtures.getNotCovered());
    const spy = vi
      .spyOn(api, 'getDataQuality')
      .mockRejectedValueOnce(new ApiError(500, 'boom', 'Quality unavailable'))
      .mockImplementation(() => fixtures.getDataQuality());
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('Quality unavailable');
    await userEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(await screen.findByText('112')).toBeInTheDocument();
    expect(spy).toHaveBeenCalledTimes(2);
  });
});
