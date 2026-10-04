import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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
      within(within(table).getByRole('rowheader', { name: new RegExp(`^${label}`) }).closest('tr')!)
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

  it('wraps the consequence tier label in a glossary term', async () => {
    renderPanel('seg_000001');
    await screen.findByRole('table', TABLE);
    expect(screen.getByRole('button', { name: 'Consequence tier' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Priority score' })).toBeInTheDocument();
  });

  it('is a non-modal dialog labelled by its heading', async () => {
    renderPanel('seg_000001');
    await screen.findByRole('table', TABLE);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'false');
    expect(dialog).toHaveAttribute('aria-labelledby', screen.getByRole('heading', { level: 2 }).id);
  });

  it('shows the not-found message for an unknown id', async () => {
    renderPanel('nope_123');
    expect(await screen.findByText("No asset with id 'nope_123' in plan v2.")).toBeInTheDocument();
  });

  it('has no dimming scrim', async () => {
    renderPanel('seg_000001');
    await screen.findByRole('table', TABLE);
    expect(screen.queryByTestId('asset-scrim')).not.toBeInTheDocument();
  });

  it('closes on Escape, the X button and an outside click', async () => {
    const onClose = renderPanel('seg_000001');
    await screen.findByRole('table', TABLE);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Close asset panel' }));
    expect(onClose).toHaveBeenCalledTimes(2);
    fireEvent.pointerDown(document.body);
    fireEvent.click(document.body);
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(3));
  });

  it('does not close on a click inside the panel or on an asset trigger', async () => {
    const onClose = renderPanel('seg_000001');
    await screen.findByRole('table', TABLE);
    fireEvent.click(screen.getByRole('table', TABLE));
    const trigger = document.createElement('a');
    trigger.setAttribute('data-asset-trigger', '');
    document.body.appendChild(trigger);
    fireEvent.click(trigger);
    await new Promise((r) => setTimeout(r, 120));
    expect(onClose).not.toHaveBeenCalled();
    trigger.remove();
  });
});
