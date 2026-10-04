import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import overviewFixture from '../../fixtures/overview.json';
import type { Resource } from '../../hooks';
import type { Overview } from '../../types/api';
import { Headline } from './Headline';

const base = overviewFixture.data as unknown as Overview;

function resource(data: Overview): Resource<Overview> {
  return { status: 'success', data, meta: undefined, error: undefined, reload: () => undefined };
}

function renderHeadline(res: Resource<Overview>) {
  return render(
    <MemoryRouter>
      <Headline overview={res} />
    </MemoryRouter>,
  );
}

describe('Headline', () => {
  it('shows V2 copy with fixture values', () => {
    renderHeadline(resource(base));
    expect(screen.getAllByText(/Share of future breaking assets caught/)).toHaveLength(1);
    expect(screen.getByText('24%')).toBeInTheDocument();
    expect(screen.getByText('18%')).toBeInTheDocument();
    expect(screen.queryByText(/V2 catches/)).not.toBeInTheDocument();
    expect(screen.getByText('V2 = C2')).toBeInTheDocument();
    expect(screen.getByText(/95% CI 20%–28%/)).toBeInTheDocument();
  });

  it('puts the selected candidate and the gate decision in the focal block', () => {
    const { container } = renderHeadline(resource(base));
    const focal = container.querySelector('[data-focal="headline"]') as HTMLElement;
    expect(focal).not.toBeNull();
    expect(within(focal).getByText('V2 = C2')).toBeInTheDocument();
    expect(focal).toHaveTextContent(/Selected by the revision gate/);
    expect(focal).toHaveTextContent(/C2: Full history,/);
    expect(focal).toHaveTextContent(/recency, per-asset/);
    expect(within(focal).getByRole('button', { name: 'hl10' })).toBeInTheDocument();
  });

  it('shows V1-retained copy when v2_equals_v1 is true', () => {
    const { container } = renderHeadline(resource({ ...base, v2_equals_v1: true, selected_policy_id: 'V1' }));
    expect(container).toHaveTextContent(/No candidate passed the revision gate/);
    expect(screen.getByText('21%')).toBeInTheDocument();
    expect(screen.queryByText(/V1 catches/)).not.toBeInTheDocument();
    expect(screen.queryByText(/V2 catches/)).not.toBeInTheDocument();
  });

  it('shows the empty state when final rows are missing', () => {
    renderHeadline(resource({ ...base, series: base.series.filter((r) => r.split !== 'final') }));
    expect(screen.getByText('Final-test results not available yet')).toBeInTheDocument();
  });

  it('shows an error with retry', () => {
    const res: Resource<Overview> = {
      status: 'error',
      data: undefined,
      meta: undefined,
      error: new Error('down') as never,
      reload: () => undefined,
    };
    renderHeadline(res);
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('when V1 is retained, lists each candidate gate result from the log (refused to change)', async () => {
    renderHeadline(resource({ ...base, v2_equals_v1: true, selected_policy_id: 'V1' }));
    const list = await screen.findByRole('list', { name: 'Why each candidate was rejected' });
    expect(within(list).getAllByRole('listitem')).toHaveLength(4);
    expect(list.textContent).toMatch(/C1\s*won \d\/3 origins/);
  });
});
