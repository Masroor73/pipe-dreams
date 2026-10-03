import { render, screen, waitFor } from '@testing-library/react';
import { useEffect } from 'react';
import { describe, expect, it } from 'vitest';
import { SyntheticBanner } from '../components/AppShell/SyntheticBanner';
import { isSyntheticMeta, MetaProvider, useReportMeta } from './synthetic';
import type { Meta } from '../types/api';

describe('isSyntheticMeta', () => {
  it('is true when synthetic is true', () => {
    expect(isSyntheticMeta({ synthetic: true, config_hash: 'abc123' })).toBe(true);
  });
  it('is true when config_hash is PLACEHOLDER', () => {
    expect(isSyntheticMeta({ synthetic: false, config_hash: 'PLACEHOLDER' })).toBe(true);
  });
  it('is false when neither applies', () => {
    expect(isSyntheticMeta({ synthetic: false, config_hash: 'abc123' })).toBe(false);
    expect(isSyntheticMeta(undefined)).toBe(false);
  });
});

function Reporter({ meta }: { meta: Meta }) {
  const report = useReportMeta();
  useEffect(() => report('test', meta), [report, meta]);
  return null;
}

describe('SyntheticBanner', () => {
  it('renders when a hook reports synthetic meta', async () => {
    render(
      <MetaProvider>
        <SyntheticBanner />
        <Reporter meta={{ synthetic: true, config_hash: 'x' }} />
      </MetaProvider>,
    );
    expect(await screen.findByRole('status')).toHaveTextContent('SYNTHETIC / PLACEHOLDER DATA — not real results');
  });

  it('does not render for real, non-placeholder meta', async () => {
    render(
      <MetaProvider>
        <SyntheticBanner />
        <Reporter meta={{ synthetic: false, config_hash: 'abc' }} />
      </MetaProvider>,
    );
    await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument());
  });

  it('does not render before anything is reported', () => {
    render(
      <MetaProvider>
        <SyntheticBanner />
      </MetaProvider>,
    );
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});
