import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { MetaProvider } from '../lib/synthetic';
import geojson from '../fixtures/assets_geojson_v2.json';
import MapPage from './MapPage';

vi.mock('../components/Communities/CommunityMap', () => ({
  CommunityMap: ({
    points,
    onSelectAsset,
  }: {
    points: { features: { properties: { asset_id: string } }[] };
    onSelectAsset: (id: string) => void;
  }) => (
    <div data-testid="dots" data-count={points.features.length}>
      <button type="button" onClick={() => onSelectAsset(points.features[0]!.properties.asset_id)}>
        dot
      </button>
    </div>
  ),
}));

function Where() {
  const l = useLocation();
  return <output data-testid="loc">{l.search}</output>;
}

function renderMap(path = '/map') {
  render(
    <MetaProvider>
      <MemoryRouter initialEntries={[path]}>
        <MapPage />
        <Where />
      </MemoryRouter>
    </MetaProvider>,
  );
}

const selectedCount = geojson.data.features.filter((f) => f.properties.selected).length;

describe('MapPage (dots from /api/assets)', () => {
  it('builds one dot per selected asset plus legend', async () => {
    renderMap();
    const dots = await screen.findByTestId('dots');
    expect(dots.dataset.count).toBe(String(selectedCount));
    expect(screen.getByText(`${selectedCount} selected segments · plan V2`)).toBeInTheDocument();
    expect(screen.getByText(/≠ failure probability/)).toBeInTheDocument();
  });

  it('sets ?asset= when a dot is clicked', async () => {
    renderMap('/map?plan=v2');
    fireEvent.click(await screen.findByRole('button', { name: 'dot' }));
    const search = screen.getByTestId('loc').textContent!;
    expect(search).toMatch(/asset=/);
    expect(search).toContain('plan=v2');
  });

  it('sets ?plan=v1 from the toggle and preserves ?asset=', async () => {
    renderMap('/map?asset=seg_000001');
    await screen.findByTestId('dots');
    fireEvent.click(screen.getByRole('button', { name: 'V1' }));
    const search = screen.getByTestId('loc').textContent!;
    expect(search).toContain('plan=v1');
    expect(search).toContain('asset=seg_000001');
  });
});
