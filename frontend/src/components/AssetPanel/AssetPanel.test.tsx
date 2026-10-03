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

describe('AssetPanel', () => {
  it('shows V1 and V2 values from the fixture', async () => {
    renderPanel('seg_000001');
    const v1 = await screen.findByRole('region', { name: 'V1 plan' });
    const v2 = screen.getByRole('region', { name: 'V2 plan' });
    expect(within(v1).getByText('5')).toBeInTheDocument();
    expect(within(v1).getByText('0.892')).toBeInTheDocument();
    expect(within(v1).getByText('0.870')).toBeInTheDocument();
    expect(within(v1).getByText('INSPECT')).toBeInTheDocument();
    expect(within(v2).getByText('31')).toBeInTheDocument();
    expect(within(v2).getByText('0.495')).toBeInTheDocument();
    expect(within(v2).getByText('MONITOR')).toBeInTheDocument();
    expect(within(v2).getByText('older breaks down-weighted')).toBeInTheDocument();
    expect(screen.getByText(/↓ 26/)).toBeInTheDocument();
    expect(screen.getByText(/Neither is a failure probability/)).toBeInTheDocument();
    expect(screen.getByRole('dialog', { name: 'Asset seg_000001' })).toBeInTheDocument();
  });

  it('shows the not-found message for an unknown id', async () => {
    renderPanel('nope_123');
    expect(await screen.findByText("No asset with id 'nope_123' in plan v2.")).toBeInTheDocument();
  });

  it('closes on Escape, the X button and the scrim', async () => {
    const onClose = renderPanel('seg_000001');
    await screen.findByRole('region', { name: 'V1 plan' });
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Close asset panel' }));
    expect(onClose).toHaveBeenCalledTimes(2);
    fireEvent.click(screen.getByTestId('asset-scrim'));
    expect(onClose).toHaveBeenCalledTimes(3);
  });
});
