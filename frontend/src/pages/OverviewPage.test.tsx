import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from '../lib/api';
import { MetaProvider } from '../lib/synthetic';
import OverviewPage from './OverviewPage';

beforeAll(() => {
  class RO {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  vi.stubGlobal('ResizeObserver', RO);
});

afterEach(() => vi.restoreAllMocks());

function renderPage() {
  return render(
    <MetaProvider>
      <MemoryRouter>
        <OverviewPage />
      </MemoryRouter>
    </MetaProvider>,
  );
}

describe('OverviewPage', () => {
  it('renders all blocks from fixtures', async () => {
    renderPage();
    expect(await screen.findByText(/V2 catches/)).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Final test (2023–2025)' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Validation · origin 2013' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirmation' })).toBeInTheDocument();
    expect(screen.getByText('Organizer cell baseline (event capture)')).toBeInTheDocument();
    expect(await screen.findByText(/Disclosure: the 2023–2025 final test window/)).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: /Open escalation list/ })).toHaveAttribute('href', '/escalation');
  });

  it('switches split on click', async () => {
    renderPage();
    const btn = await screen.findByRole('button', { name: 'Confirmation' });
    await userEvent.click(btn);
    expect(btn).toHaveAttribute('aria-pressed', 'true');
  });

  it('shows retry when overview fails', async () => {
    vi.spyOn(api, 'getOverview').mockRejectedValue(new ApiError(500, 'http_error', 'Overview down'));
    renderPage();
    const alerts = await screen.findAllByRole('alert');
    expect(alerts.length).toBeGreaterThan(0);
    expect((await screen.findAllByRole('button', { name: /retry/i })).length).toBeGreaterThan(0);
  });
});
