import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { MetaProvider } from '../../lib/synthetic';
import { AssetPanel } from './AssetPanel';

function renderPanel(assetId: string, onClose = vi.fn()) {
  render(
    <MetaProvider>
      <MemoryRouter>
        <AssetPanel assetId={assetId} onClose={onClose} />
      </MemoryRouter>
    </MetaProvider>,
  );
  return onClose;
}

const TABLE = { name: 'V1 and V2 plan comparison' };

describe('AssetPanel', () => {
  it('shows V1 and V2 values from the fixture in a comparison table', async () => {
    renderPanel('seg_000001');
    const table = await screen.findByRole('table', TABLE);
    const cells = (label: string) =>
      within(within(table).getByRole('rowheader', { name: label }).closest('tr')!)
        .getAllByRole('cell')
        .map((c) => c.textContent);
    expect(cells('Rank')).toEqual(['5', '31']);
    expect(cells('Priority score')).toEqual(['0.892', '0.495']);
    expect(cells('Likelihood score')[0]).toBe('0.870');
    expect(cells('Recommended action')).toEqual(['INSPECT', 'MONITOR']);
    expect(cells('Revision reason')[1]).toBe('older breaks down-weighted');
    expect(screen.getByText(/↓ 26/)).toBeInTheDocument();
    expect(screen.getByText(/Neither is a failure probability/)).toBeInTheDocument();
    expect(screen.getByRole('dialog', { name: 'Asset seg_000001' })).toBeInTheDocument();
  });

  it('labels the consequence tier chip with a tooltip', async () => {
    renderPanel('seg_000001');
    await screen.findByRole('table', TABLE);
    const chip = screen.getByText(/^Consequence tier T\d/);
    expect(chip).toBeInTheDocument();
    expect(chip.closest('[title]')).toHaveAttribute('title', expect.stringContaining('pipe diameter'));
  });

  it('shows the not-found message for an unknown id', async () => {
    renderPanel('nope_123');
    expect(await screen.findByText("No asset with id 'nope_123' in plan v2.")).toBeInTheDocument();
  });

  it('closes on Escape, the X button and the scrim', async () => {
    const onClose = renderPanel('seg_000001');
    await screen.findByRole('table', TABLE);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Close asset panel' }));
    expect(onClose).toHaveBeenCalledTimes(2);
    fireEvent.click(screen.getByTestId('asset-scrim'));
    expect(onClose).toHaveBeenCalledTimes(3);
  });
});
