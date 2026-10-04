import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Briefing } from './Briefing';

afterEach(() => vi.unstubAllGlobals());

describe('Briefing', () => {
  it('is hidden when /briefing.mp3 is missing', async () => {
    const f = vi.fn().mockResolvedValue({ ok: false, headers: new Headers() });
    vi.stubGlobal('fetch', f);
    const { container } = render(<Briefing />);
    await waitFor(() => expect(f).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the player and transcript when present', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (_url: string, init?: { method?: string }) =>
        init?.method === 'HEAD'
          ? { ok: true, headers: new Headers({ 'content-type': 'audio/mpeg' }) }
          : { ok: true, text: async () => 'Hello planner.' },
      ),
    );
    render(<Briefing />);
    expect(await screen.findByText(/Play planner briefing/)).toBeInTheDocument();
    expect(await screen.findByText('Hello planner.')).toBeInTheDocument();
  });
});
