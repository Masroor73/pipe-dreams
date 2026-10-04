import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../lib/api';
import { MetaProvider } from '../lib/synthetic';
import CommunitiesPage from './CommunitiesPage';

const meta = { synthetic: false, config_hash: 'x' };
const community = (id: string, name: string) => ({
  community_id: id,
  community_name: name,
  pipe_length_km: 10,
  historical_break_count: 20,
  historical_breaks_per_km: 2,
  population: null,
  equity_index: null,
  equity_geography_status: 'NOT_ASSESSED' as const,
  data_quality_flags: [],
});

const mocks = vi.hoisted(() => ({
  getCommunities: vi.fn(),
  getCommunitiesGeoJson: vi.fn(),
  getAssets: vi.fn(),
  getAssetsGeoJson: vi.fn(),
}));

vi.mock('../lib/api', async (orig) => {
  const actual = await orig<typeof import('../lib/api')>();
  return { ...actual, api: { ...mocks } };
});

vi.mock('../components/Communities/CommunityMap', () => ({
  CommunityMap: () => <div data-testid="community-map" />,
}));

function Where() {
  const l = useLocation();
  return <output data-testid="loc">{l.search}</output>;
}

function renderPage(path = '/communities') {
  render(
    <MetaProvider>
      <MemoryRouter initialEntries={[path]}>
        <CommunitiesPage />
        <Where />
      </MemoryRouter>
    </MetaProvider>,
  );
}

beforeEach(() => {
  Object.values(mocks).forEach((m) => m.mockReset());
  mocks.getCommunities.mockResolvedValue({
    meta,
    data: { cutoff_year: 2022, items: [community('BLN', 'Beltline'), community('SNK', 'Sunnyside')] },
  });
  mocks.getCommunitiesGeoJson.mockResolvedValue({ meta, data: { type: 'FeatureCollection', features: [] } });
  mocks.getAssets.mockResolvedValue({
    meta,
    data: {
      plan: 'v2',
      total: 1,
      limit: 500,
      offset: 0,
      items: [
        {
          asset_id: 'seg_1',
          rank: 123,
          selected: true,
          length_m: 250,
          priority_score: 1,
          consequence_tier: 'HIGH',
          evidence_confidence: 'HIGH',
          recommended_action: 'INSPECT',
          latitude: 51,
          longitude: -114,
        },
      ],
    },
  });
  mocks.getAssetsGeoJson.mockResolvedValue({ meta, data: { type: 'FeatureCollection', features: [] } });
});

describe('CommunitiesPage', () => {
  it('shows the framing text and communities in API order', async () => {
    renderPage();
    await screen.findByText('Beltline');
    expect(screen.getByText(/Which communities should we protect first/)).toBeInTheDocument();
    expect(screen.getByText(/not social vulnerability/)).toBeInTheDocument();
    const names = screen.getAllByRole('button').map((b) => b.textContent ?? '');
    expect(names[0]).toContain('Beltline');
    expect(names[1]).toContain('Sunnyside');
  });

  it('selecting a community sets ?community= and fetches pipes with community_id', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /Beltline/ }));
    expect(screen.getByTestId('loc').textContent).toContain('community=BLN');
    await screen.findByText('#123 citywide');
    expect(mocks.getAssets).toHaveBeenCalledWith(expect.objectContaining({ community_id: 'BLN', sort: 'rank' }));
    expect(mocks.getAssetsGeoJson).toHaveBeenCalledWith(expect.objectContaining({ community_id: 'BLN' }));
    expect(screen.getByText('250 m')).toBeInTheDocument();
    expect(screen.getByText('INSPECT')).toBeInTheDocument();
  });

  it('restores the selection from the URL and maps the toggle to selected_only', async () => {
    renderPage('/communities?community=BLN');
    await screen.findByText('#123 citywide');
    expect(mocks.getAssets).toHaveBeenLastCalledWith(
      expect.objectContaining({ community_id: 'BLN', selected_only: false }),
    );
    fireEvent.click(screen.getByLabelText('Selected for inspection only'));
    await waitFor(() =>
      expect(mocks.getAssets).toHaveBeenLastCalledWith(
        expect.objectContaining({ community_id: 'BLN', selected_only: true }),
      ),
    );
    expect(screen.getByTestId('loc').textContent).toContain('inspect=true');
  });

  it('clear selection returns to the citywide list', async () => {
    renderPage('/communities?community=BLN&inspect=true');
    await screen.findByText('#123 citywide');
    fireEvent.click(screen.getByRole('button', { name: 'Clear selection' }));
    expect(screen.getByTestId('loc').textContent).not.toContain('community=');
    expect(await screen.findByRole('button', { name: /Sunnyside/ })).toBeInTheDocument();
  });

  it('shows a friendly not-found state for an unknown community', async () => {
    renderPage('/communities?community=NOPE');
    expect(await screen.findByText('Community not found.')).toBeInTheDocument();
    expect(mocks.getAssets).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Back to citywide view' }));
    expect(screen.getByTestId('loc').textContent).not.toContain('community=');
  });

  it('shows an error state when communities fail to load', async () => {
    mocks.getCommunities.mockRejectedValue(new ApiError(500, 'http_error', 'boom'));
    renderPage();
    expect(await screen.findByText('boom')).toBeInTheDocument();
  });
});
