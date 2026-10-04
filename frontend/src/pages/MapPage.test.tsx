import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { MetaProvider } from '../lib/synthetic';
import geojsonV2 from '../fixtures/assets_geojson_v2.json';
import MapPage from './MapPage';

vi.mock('react-map-gl/maplibre', () => ({
  default: () => null,
  Source: () => null,
  Layer: () => null,
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

const selectedCount = geojsonV2.data.features.filter((f) => f.properties.selected).length;

describe('MapPage (SVG fallback, no WebGL in jsdom)', () => {
  it('renders one path per selected feature plus legend and offline note', async () => {
    renderMap();
    await screen.findByText('Basemap: none (offline)');
    expect(document.querySelectorAll('svg path[data-asset-id]')).toHaveLength(selectedCount);
    expect(screen.getByText(`${selectedCount} selected segments · plan V2`)).toBeInTheDocument();
    expect(screen.getByText('LOW_VERIFY (verify before acting)')).toBeInTheDocument();
    expect(screen.getByText(/≠ failure probability/)).toBeInTheDocument();
  });

  it('sets ?asset= when a line is clicked', async () => {
    renderMap('/map?plan=v2');
    await screen.findByText('Basemap: none (offline)');
    const path = document.querySelector('svg path[data-asset-id]') as SVGPathElement;
    fireEvent.click(path);
    const search = screen.getByTestId('loc').textContent!;
    expect(search).toContain(`asset=${path.dataset.assetId}`);
    expect(search).toContain('plan=v2');
  });

  it('sets ?plan=v1 from the toggle and preserves ?asset=', async () => {
    renderMap('/map?asset=seg_000001');
    await screen.findByText('Basemap: none (offline)');
    fireEvent.click(screen.getByRole('button', { name: 'V1' }));
    const search = screen.getByTestId('loc').textContent!;
    expect(search).toContain('plan=v1');
    expect(search).toContain('asset=seg_000001');
  });

  it('draws the open asset even when it is outside the plan’s selected segments', async () => {
    renderMap('/map?asset=seg_000001');
    await screen.findByText('Basemap: none (offline)');
    expect(await screen.findByText(`${selectedCount} selected segments · plan V2`)).toBeInTheDocument();
    await vi.waitFor(() => expect(document.querySelector('svg path[data-asset-id="seg_000001"]')).not.toBeNull());
    expect(document.querySelectorAll('svg path[data-asset-id]')).toHaveLength(selectedCount + 1);
  });
});
