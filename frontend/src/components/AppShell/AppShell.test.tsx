import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../lib/api';
import { MetaProvider } from '../../lib/synthetic';
import { ApiError } from '../../lib/api';
import { AppShell } from './AppShell';

function renderShell(path = '/') {
  return render(
    <MetaProvider>
      <MemoryRouter initialEntries={[path]}>
        <AppShell />
      </MemoryRouter>
    </MetaProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe('AppShell', () => {
  it('renders the banner, nav and the routed page when healthy', async () => {
    renderShell('/audit');
    expect(await screen.findByRole('heading', { name: 'Agent audit' })).toBeInTheDocument();
    expect(await screen.findByText(/SYNTHETIC \/ PLACEHOLDER DATA/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Overview' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Limits' })).toBeInTheDocument();
  });

  it('shows the banner on deep links to any route', async () => {
    renderShell('/escalation');
    expect(await screen.findByText(/SYNTHETIC \/ PLACEHOLDER DATA/)).toBeInTheDocument();
  });

  it('shows "Artifacts unavailable" instead of routes when health is degraded', async () => {
    vi.spyOn(api, 'getHealth').mockResolvedValue({
      status: 'degraded',
      artifacts_loaded: false,
      artifact_dir: 'artifacts/missing',
      synthetic: false,
    });
    renderShell('/');
    expect(await screen.findByRole('heading', { name: 'Artifacts unavailable' })).toBeInTheDocument();
    expect(screen.getByText('artifacts/missing')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Overview' })).not.toBeInTheDocument();
  });

  it('shows "Artifacts unavailable" when health is unreachable', async () => {
    vi.spyOn(api, 'getHealth').mockRejectedValue(new ApiError(0, 'network_error', 'Failed to fetch'));
    renderShell('/');
    expect(await screen.findByRole('heading', { name: 'Artifacts unavailable' })).toBeInTheDocument();
    expect(screen.getByText(/Failed to fetch/)).toBeInTheDocument();
  });

  it('opens the asset panel from ?asset= and closes it', async () => {
    renderShell('/?asset=seg_000007');
    expect(await screen.findByRole('complementary', { name: 'Asset detail' })).toHaveTextContent('seg_000007');
  });
});
