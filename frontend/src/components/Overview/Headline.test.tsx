import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import overviewFixture from '../../fixtures/overview.json';
import type { Resource } from '../../hooks';
import type { Overview } from '../../types/api';
import { Headline } from './Headline';

const base = overviewFixture.data as unknown as Overview;

function resource(data: Overview): Resource<Overview> {
  return { status: 'success', data, meta: undefined, error: undefined, reload: () => undefined };
}

describe('Headline', () => {
  it('shows V2 copy with fixture values', () => {
    render(<Headline overview={resource(base)} />);
    expect(screen.getByText(/V2 catches/)).toHaveTextContent(
      'V2 catches 24% of future breaking assets at a 5% length budget, vs 18% for count-only.',
    );
    expect(screen.getByText('V2 = C2')).toBeInTheDocument();
    expect(screen.getByText(/95% CI 20%–28%/)).toBeInTheDocument();
  });

  it('shows V1-retained copy when v2_equals_v1 is true', () => {
    render(<Headline overview={resource({ ...base, v2_equals_v1: true, selected_policy_id: 'V1' })} />);
    expect(screen.getByText(/V1 retained — no candidate passed the revision gate/)).toBeInTheDocument();
    expect(screen.getByText(/V1 catches/)).toHaveTextContent('21%');
    expect(screen.queryByText(/V2 catches/)).not.toBeInTheDocument();
  });

  it('shows the empty state when final rows are missing', () => {
    render(<Headline overview={resource({ ...base, series: base.series.filter((r) => r.split !== 'final') })} />);
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
    render(<Headline overview={res} />);
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });
});
