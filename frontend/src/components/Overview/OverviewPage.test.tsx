import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from '../../lib/api';
import { MetaProvider } from '../../lib/synthetic';
import OverviewPage from '../../pages/OverviewPage';

beforeAll(() => {
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
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
  it('renders every block from fixtures', async () => {
    renderPage();
    expect(await screen.findByText(/Share of future breaking assets caught/)).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: /Capture by length budget/ })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: /full audit trail/i })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: /escalation list/i })).toBeInTheDocument();
    expect(await screen.findByText(/Disclosure:/)).toBeInTheDocument();
  });

  it('shows retry on the overview-backed sections when the request fails', async () => {
    vi.spyOn(api, 'getOverview').mockRejectedValue(new ApiError(500, 'http_error', 'Overview failed'));
    renderPage();
    const retries = await screen.findAllByRole('button', { name: /retry/i });
    expect(retries.length).toBeGreaterThanOrEqual(1);
  });
});
