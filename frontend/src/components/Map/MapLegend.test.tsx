import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { COMMUNITY_COLOR, CONFIDENCE_COLORS, CONFIDENCE_ORDER, MUTED_COLOR, OPEN_PIPE_COLOR } from '../../config/map';
import { MapLegend } from './MapLegend';

function colours(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll('[data-color]')).map((e) => e.getAttribute('data-color')!);
}

describe('MapLegend', () => {
  it('renders every confidence category with the shared colour constants and plain-language meanings', () => {
    const { container } = render(
      <MemoryRouter>
        <MapLegend plan="v1" count={12} />
      </MemoryRouter>,
    );
    expect(colours(container)).toEqual(CONFIDENCE_ORDER.map((c) => CONFIDENCE_COLORS[c]));
    expect(screen.getByText('strong evidence', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('some gaps', { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/weak evidence . verify before acting/)).toBeInTheDocument();
    expect(screen.getByText(/plan V1\), coloured by/)).toBeInTheDocument();
    expect(screen.getByText('12 selected segments · plan V1')).toBeInTheDocument();
    expect(screen.queryByText(/not selected for inspection/)).toBeNull();
    expect(screen.queryByText(/open in the detail panel/)).toBeNull();
  });

  it('adds grey, open-pipe and community entries only when relevant', () => {
    const { container } = render(
      <MemoryRouter>
        <MapLegend plan="v2" showMuted showOpen showCommunity />
      </MemoryRouter>,
    );
    expect(colours(container).slice(3)).toEqual([MUTED_COLOR, OPEN_PIPE_COLOR, COMMUNITY_COLOR]);
    expect(screen.getByText('In community, not selected for inspection')).toBeInTheDocument();
    expect(screen.getByText('Pipe open in the detail panel')).toBeInTheDocument();
    expect(screen.getByText('Selected community')).toBeInTheDocument();
  });
});
