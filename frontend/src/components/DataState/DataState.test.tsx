import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DataState } from './DataState';

describe('DataState', () => {
  it('shows a loading state', () => {
    render(<DataState status="loading" loadingLabel="Loading overview">content</DataState>);
    expect(screen.getByRole('status')).toHaveTextContent('Loading overview');
    expect(screen.queryByText('content')).not.toBeInTheDocument();
  });

  it('shows the empty message when empty', () => {
    render(
      <DataState status="success" empty emptyMessage="No escalations.">
        content
      </DataState>,
    );
    expect(screen.getByText('No escalations.')).toBeInTheDocument();
    expect(screen.queryByText('content')).not.toBeInTheDocument();
  });

  it('shows the error message and retries', async () => {
    const onRetry = vi.fn();
    render(
      <DataState status="error" errorMessage="Boom" onRetry={onRetry}>
        content
      </DataState>,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Boom');
    await userEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('renders children on success', () => {
    render(<DataState status="success">content</DataState>);
    expect(screen.getByText('content')).toBeInTheDocument();
  });
});
