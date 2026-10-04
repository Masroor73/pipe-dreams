import type { ReactNode } from 'react';
import { ArrowClockwise, Tray, WarningCircle } from '@phosphor-icons/react';
import type { ResourceStatus } from '../../hooks/useApiResource';
import styles from './DataState.module.css';

export interface DataStateProps {
  status: ResourceStatus;
  /** Message shown on error (usually `error.message`). */
  errorMessage?: string;
  onRetry?: () => void;
  /** When status is success but there is nothing to show. */
  empty?: boolean;
  emptyMessage?: string;
  loadingLabel?: string;
  /** Minimum height while loading/empty/error so layout does not jump. */
  minHeight?: number;
  children?: ReactNode;
}

export function DataState({
  status,
  errorMessage,
  onRetry,
  empty = false,
  emptyMessage = 'Nothing to show yet.',
  loadingLabel = 'Loading',
  minHeight = 160,
  children,
}: DataStateProps) {
  if (status === 'loading') {
    return (
      <div className={styles.box} style={{ minHeight }} role="status" aria-live="polite" aria-busy="true">
        <div className={styles.skeleton} aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <span className={styles.label}>{loadingLabel}…</span>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className={`${styles.box} ${styles.error}`} style={{ minHeight }} role="alert">
        <WarningCircle size={28} weight="duotone" aria-hidden="true" />
        <p className={styles.message}>{errorMessage ?? 'Something went wrong loading this data.'}</p>
        {onRetry && (
          <button type="button" className={styles.retry} onClick={onRetry}>
            <ArrowClockwise size={18} aria-hidden="true" />
            Retry
          </button>
        )}
      </div>
    );
  }

  if (empty) {
    return (
      <div className={styles.box} style={{ minHeight }} role="status">
        <Tray size={28} weight="duotone" aria-hidden="true" />
        <p className={styles.message}>{emptyMessage}</p>
      </div>
    );
  }

  return <>{children}</>;
}
